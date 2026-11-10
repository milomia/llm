"""Score the pipeline against a reference set (eval/reference.json).

Classification is scored per category as precision / recall / F1 over statements, plus how many
predicted statements are verbatim quotes of the transcript. Levelling is scored on the reference
statements themselves (so a classification miss does not also count as a levelling miss) as exact
and within-one-level agreement. Run it with `python manage.py run_eval`.
"""
import re
import time
from difflib import SequenceMatcher

from django.db import transaction

from analysis.classification import classify_transcription
from analysis.levelling import level_category
from analysis.models import FinalStatementWithLevel, StatementClassification, StatementLevelPrompt, Transcription
from analysis.utils import create_overlapping_segments, split_closing_outcome

CATEGORIES = ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING_OUTCOME']
STAGES = ['classification', 'levelling']

# Same segmentation as the /process/ and /sync-process/ pipelines.
SEGMENT_LENGTH = 6000
SEGMENT_OVERLAP = 100

# Two statements are the same if their text is this similar, or if one contains the other and is at
# least half its length (the model and the reference often cut a turn at slightly different points).
MATCH_RATIO = 0.8
CONTAINMENT_MIN_SHARE = 0.5


def normalise(text):
    """Lower-case, drop a leading speaker label and collapse everything but letters and digits."""
    text = re.sub(r'^\s*(MSL|REP)\s*:?\s*', '', str(text))
    return re.sub(r'[\W_]+', ' ', text.lower()).strip()


def same_statement(a, b):
    a, b = normalise(a), normalise(b)
    if not a or not b:
        return False
    if a == b:
        return True
    shorter, longer = sorted((a, b), key=len)
    if shorter in longer and len(shorter) >= CONTAINMENT_MIN_SHARE * len(longer):
        return True
    return SequenceMatcher(None, a, b).ratio() >= MATCH_RATIO


def match_statements(reference, predicted):
    """One-to-one match of predicted statements to reference statements.
    Returns (matched pairs, missed reference statements, extra predicted statements)."""
    remaining = list(predicted)
    matched, missed = [], []
    for ref in reference:
        hit = next((p for p in remaining if same_statement(ref, p)), None)
        if hit is None:
            missed.append(ref)
        else:
            remaining.remove(hit)
            matched.append((ref, hit))
    return matched, missed, remaining


def closing_text(statement):
    """The REP's closing line of a CLOSING_OUTCOME statement, which is what gets compared."""
    return split_closing_outcome(str(statement))[0]


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision and recall else (0.0 if tp + fp + fn else None)
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}


def score_classification(reference, predicted):
    """reference / predicted: {category: [statement, ...]}. Returns per-category counts and the
    statements that were missed or extra."""
    result = {}
    for category in CATEGORIES:
        ref, pred = reference.get(category, []), predicted.get(category, [])
        if category == 'CLOSING_OUTCOME':
            ref, pred = [closing_text(s) for s in ref], [closing_text(s) for s in pred]
        matched, missed, extra = match_statements(ref, pred)
        result[category] = {"tp": len(matched), "fp": len(extra), "fn": len(missed), "missed": missed, "extra": extra}
    return result


def verbatim_share(predicted, text):
    """(verbatim, total): how many predicted statements appear word for word in the transcript."""
    haystack = normalise(text)
    parts = []
    for category, statements in predicted.items():
        for statement in statements:
            if category == 'CLOSING_OUTCOME':
                parts.extend(part for part in split_closing_outcome(str(statement)) if part)
            else:
                parts.append(statement)
    return sum(normalise(part) in haystack for part in parts), len(parts)


def score_levels(pairs):
    """pairs: [(reference level, predicted level or None)]."""
    scored = [(ref, pred) for ref, pred in pairs if pred is not None]
    return {
        "statements": len(pairs),
        "scored": len(scored),
        "exact": sum(ref == pred for ref, pred in scored),
        "within_one": sum(abs(ref - pred) <= 1 for ref, pred in scored),
        "abs_error": sum(abs(ref - pred) for ref, pred in scored),
    }


def run_case(case, stages=STAGES):
    """Run the real pipeline stages on one reference case and score them. Everything is written
    inside a transaction that is rolled back, so the database is left untouched."""
    result = {"id": case["id"], "words": len(case["text"].split())}
    with transaction.atomic():
        transcription = Transcription.objects.create(
            text=case["text"],
            segments=create_overlapping_segments(case["text"], SEGMENT_LENGTH, SEGMENT_OVERLAP),
        )
        if 'classification' in stages:
            result["classification"] = _run_classification(case, transcription)
        if 'levelling' in stages and case.get("levels"):
            result["levelling"] = _run_levelling(case, transcription)
        transaction.set_rollback(True)
    return result


def _run_classification(case, transcription):
    started = time.monotonic()
    try:
        classify_transcription(transcription)
    except Exception as exc:  # a model failure is a result to report, not a reason to stop the eval
        return {"error": f"{type(exc).__name__}: {exc}"[:300], "seconds": round(time.monotonic() - started, 1)}
    predicted = {category: [] for category in CATEGORIES}
    for row in StatementClassification.objects.filter(transcription=transcription).order_by('id'):
        predicted[row.category].append(row.statement)
    verbatim, total = verbatim_share(predicted, case["text"])
    return {
        "seconds": round(time.monotonic() - started, 1),
        "categories": score_classification(case["statements"], predicted),
        "verbatim": verbatim,
        "predicted": total,
    }


def _run_levelling(case, transcription):
    # Level the reference statements, not whatever classification just produced.
    StatementClassification.objects.filter(transcription=transcription).delete()
    FinalStatementWithLevel.objects.filter(transcription=transcription).delete()
    StatementClassification.objects.bulk_create([
        StatementClassification(transcription=transcription, category=item["category"],
                                statement=item["statement"], segment_number=1)
        for item in case["levels"]
    ])
    started = time.monotonic()
    try:
        for category in CATEGORIES:
            prompt = StatementLevelPrompt.objects.filter(active=True, category=category).first()
            if prompt:
                level_category(category, transcription, prompt)
    except Exception as exc:
        return {"error": f"{type(exc).__name__}: {exc}"[:300], "seconds": round(time.monotonic() - started, 1)}
    predicted = {
        (row.category, row.statement): row.level
        for row in FinalStatementWithLevel.objects.filter(transcription=transcription)
    }
    by_category = {}
    for item in case["levels"]:
        by_category.setdefault(item["category"], []).append(
            (item["level"], predicted.get((item["category"], item["statement"]))))
    return {
        "seconds": round(time.monotonic() - started, 1),
        "categories": {category: score_levels(pairs) for category, pairs in by_category.items()},
    }


def summarise(case_results):
    """Add the per-case results up into one summary per stage."""
    classification = {category: {"tp": 0, "fp": 0, "fn": 0} for category in CATEGORIES}
    levelling = {}
    summary = {"cases": len(case_results), "classification_errors": 0, "levelling_errors": 0,
               "verbatim": 0, "predicted": 0, "seconds": 0.0}
    for case in case_results:
        for stage in STAGES:
            outcome = case.get(stage)
            if not outcome:
                continue
            summary["seconds"] += outcome["seconds"]
            if "error" in outcome:
                summary[f"{stage}_errors"] += 1
        outcome = case.get("classification")
        if outcome and "error" not in outcome:
            summary["verbatim"] += outcome["verbatim"]
            summary["predicted"] += outcome["predicted"]
            for category, counts in outcome["categories"].items():
                for key in ("tp", "fp", "fn"):
                    classification[category][key] += counts[key]
        outcome = case.get("levelling")
        if outcome and "error" not in outcome:
            for category, counts in outcome["categories"].items():
                total = levelling.setdefault(category, dict.fromkeys(counts, 0))
                for key, value in counts.items():
                    total[key] += value

    summary["classification"] = {category: prf(**counts) for category, counts in classification.items()}
    summary["classification"]["ALL"] = prf(*(sum(c[key] for c in classification.values()) for key in ("tp", "fp", "fn")))
    if levelling:
        levelling["ALL"] = {key: sum(c[key] for c in levelling.values()) for key in next(iter(levelling.values()))}
    summary["levelling"] = levelling
    summary["seconds"] = round(summary["seconds"], 1)
    return summary
