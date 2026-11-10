import json
import re
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.management import call_command
from django.test import SimpleTestCase, TestCase

from analysis.evaluation import (
    CATEGORIES, match_statements, run_case, same_statement, score_classification, score_levels, summarise,
    verbatim_share,
)
from analysis.models import (
    FinalStatementWithLevel, StatementClassification, StatementClassificationTypePrompt, StatementLevelPrompt,
    Transcription,
)
from analysis.outputParser import EvaluationResult, StatementLevelModel, StatementParser

TEXT = ("MSLHello Dr Lewis, thanks for your time. DrNo problem. MSLHow do you treat moderate asthma today? "
        "DrInhaled steroids. MSLOur trial showed a 30 percent reduction in exacerbations. DrInteresting. "
        "MSLCould we meet again next month? DrYes, that works.")
CLOSING = {"closing_statement": "Could we meet again next month?", "outcome_statement": "Yes, that works."}
CASE = {
    "id": "case-1",
    "text": TEXT,
    "statements": {
        "OPENING": ["Hello Dr Lewis, thanks for your time."],
        "QUESTIONING": ["How do you treat moderate asthma today?"],
        "PRESENTING": ["Our trial showed a 30 percent reduction in exacerbations."],
        "CLOSING_OUTCOME": [str(CLOSING)],
    },
    "levels": [
        {"category": "OPENING", "statement": "Hello Dr Lewis, thanks for your time.", "level": 2},
        {"category": "QUESTIONING", "statement": "How do you treat moderate asthma today?", "level": 3},
        {"category": "PRESENTING", "statement": "Our trial showed a 30 percent reduction in exacerbations.", "level": 4},
    ],
}


class ScoringTests(SimpleTestCase):
    def test_same_statement_tolerates_labels_punctuation_and_small_edits(self):
        self.assertTrue(same_statement("MSLHello Dr Lewis, thanks for your time.", "hello dr lewis thanks for your time"))
        self.assertTrue(same_statement("How do you treat moderate asthma today?", "How do you treat moderate asthma?"))
        self.assertFalse(same_statement("How do you treat moderate asthma today?", "Could we meet again next month?"))
        self.assertFalse(same_statement("Yes", "Yes, I would like to hear much more about the trial data please"))
        self.assertFalse(same_statement("", "anything"))

    def test_each_predicted_statement_matches_at_most_one_reference(self):
        matched, missed, extra = match_statements(["a question here", "a question here"], ["a question here", "other"])
        self.assertEqual((len(matched), missed, extra), (1, ["a question here"], ["other"]))

    def test_classification_counts_found_missed_and_extra_per_category(self):
        predicted = {
            "OPENING": ["MSLHello Dr Lewis, thanks for your time."],
            "QUESTIONING": [],
            "PRESENTING": ["Our trial showed a 30 percent reduction in exacerbations.", "An invented claim."],
            "CLOSING_OUTCOME": [str({"closing_statement": "Could we meet again next month?", "outcome_statement": ""})],
        }
        scores = score_classification(CASE["statements"], predicted)
        self.assertEqual({c: (s["tp"], s["fp"], s["fn"]) for c, s in scores.items()},
                         {"OPENING": (1, 0, 0), "QUESTIONING": (0, 0, 1), "PRESENTING": (1, 1, 0),
                          "CLOSING_OUTCOME": (1, 0, 0)})
        self.assertEqual(scores["QUESTIONING"]["missed"], ["How do you treat moderate asthma today?"])
        self.assertEqual(scores["PRESENTING"]["extra"], ["An invented claim."])

    def test_verbatim_share_flags_statements_not_in_the_transcript(self):
        predicted = {"OPENING": ["Hello Dr Lewis, thanks for your time."], "PRESENTING": ["An invented claim."],
                     "CLOSING_OUTCOME": [str(CLOSING)]}
        self.assertEqual(verbatim_share(predicted, TEXT), (3, 4))

    def test_levels_report_exact_within_one_and_unscored(self):
        self.assertEqual(score_levels([(2, 2), (3, 4), (4, 1), (1, None)]),
                         {"statements": 4, "scored": 3, "exact": 1, "within_one": 2, "abs_error": 4})

    def test_summary_adds_cases_up_and_counts_failures(self):
        ok = {"classification": {"seconds": 1.0, "verbatim": 3, "predicted": 4,
                                 "categories": {c: {"tp": 1, "fp": 1, "fn": 0} for c in CATEGORIES}},
              "levelling": {"seconds": 2.0, "categories": {
                  "OPENING": {"statements": 2, "scored": 2, "exact": 1, "within_one": 2, "abs_error": 1}}}}
        failed = {"classification": {"error": "TimeoutError: x", "seconds": 5.0}}
        summary = summarise([ok, ok, failed])
        self.assertEqual((summary["cases"], summary["classification_errors"], summary["seconds"]), (3, 1, 11.0))
        self.assertEqual(summary["classification"]["ALL"],
                         {"tp": 8, "fp": 8, "fn": 0, "precision": 0.5, "recall": 1.0, "f1": 2 / 3})
        self.assertEqual(summary["levelling"]["ALL"]["exact"], 2)
        self.assertEqual((summary["verbatim"], summary["predicted"]), (6, 8))

    def test_shipped_reference_file_is_well_formed(self):
        reference = json.loads((Path(settings.BASE_DIR) / "eval" / "reference.json").read_text())
        self.assertGreater(len(reference["cases"]), 0)
        for case in reference["cases"]:
            self.assertEqual(set(case["statements"]), set(CATEGORIES))
            self.assertTrue(case["text"])
            for item in case["levels"]:
                self.assertIn(item["level"], (1, 2, 3, 4))
                self.assertIn(item["statement"], case["statements"][item["category"]])


class RunCaseTests(TestCase):
    def setUp(self):
        for category in CATEGORIES:
            StatementClassificationTypePrompt.objects.create(
                category=category, definition="d", examples="e", invalid_examples="i")
            StatementLevelPrompt.objects.create(
                category=category, objective="o", evaluation_criteria="e", score_assignment_criteria="s",
                instruction="i", examples="x", notes="n")
        self.classified = StatementParser(
            opening_statements=CASE["statements"]["OPENING"],
            questioning_statements=["Something the HCP said instead."],
            presenting_statements=CASE["statements"]["PRESENTING"],
            closing_outcome_sentences=[CLOSING],
        )
        for target in ("analysis.utils.make_agent", "analysis.levelling.make_agent"):
            self.enterContext(patch(target, side_effect=self.fake_agent))
        self.enterContext(patch("analysis.utils.get_similar_examples", return_value=([], [])))
        self.enterContext(patch("analysis.utils.get_llm_model"))

    def fake_agent(self, output_type):
        def run_sync(prompt):
            if output_type is EvaluationResult:  # every statement gets level 3
                ids = [int(i) for i in re.findall(r"'id': (\d+)", prompt)]
                return MagicMock(output=EvaluationResult(statements=[
                    StatementLevelModel(id=i, level=3, confidence_score=80, reason="r") for i in ids]))
            return MagicMock(output=self.classified)

        agent = MagicMock()
        agent.run_sync.side_effect = run_sync
        return agent

    def test_scores_both_stages_and_leaves_the_database_untouched(self):
        result = run_case(CASE)

        categories = result["classification"]["categories"]
        self.assertEqual({c: (s["tp"], s["fp"], s["fn"]) for c, s in categories.items()},
                         {"OPENING": (1, 0, 0), "QUESTIONING": (0, 1, 1), "PRESENTING": (1, 0, 0),
                          "CLOSING_OUTCOME": (1, 0, 0)})
        self.assertEqual((result["classification"]["verbatim"], result["classification"]["predicted"]), (4, 5))
        levels = result["levelling"]["categories"]
        self.assertEqual({c: (s["scored"], s["exact"], s["within_one"]) for c, s in levels.items()},
                         {"OPENING": (1, 0, 1), "QUESTIONING": (1, 1, 1), "PRESENTING": (1, 0, 1)})
        for model in (Transcription, StatementClassification, FinalStatementWithLevel):
            self.assertEqual(model.objects.count(), 0)

    def test_a_model_failure_is_recorded_instead_of_raised(self):
        with patch("analysis.evaluation.classify_transcription", side_effect=TimeoutError("model hung")):
            result = run_case(CASE, stages=["classification"])
        self.assertEqual(result["classification"]["error"], "TimeoutError: model hung")
        self.assertEqual(Transcription.objects.count(), 0)

    def test_command_prints_a_summary_and_writes_a_report(self):
        with tempfile.TemporaryDirectory() as folder:
            reference = Path(folder) / "reference.json"
            reference.write_text(json.dumps({"cases": [CASE, {**CASE, "id": "case-2", "reviewed": True}]}))
            out = StringIO()
            with patch("analysis.management.commands.run_eval.get_llm_model") as model:
                model.return_value.model_name = "fake:1b"
                call_command("run_eval", reference=str(reference), output=folder, limit=2, stdout=out)

            report = json.loads(next(Path(folder).glob("*-fake_1b.json")).read_text())
        self.assertIn("Cases: 2 (1 human-reviewed)", out.getvalue())
        self.assertIn("Classification", out.getvalue())
        self.assertEqual((report["model"], len(report["cases"])), ("fake:1b", 2))
        self.assertEqual(report["summary"]["classification"]["ALL"]["tp"], 6)
        self.assertEqual(report["summary"]["levelling"]["ALL"]["scored"], 6)
