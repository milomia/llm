import json
import os
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from analysis.evaluation import STAGES, run_case, summarise
from analysis.llm import get_llm_model


def pct(part, whole):
    return "   -" if not whole else f"{100 * part / whole:3.0f}%"


def ratio(value):
    return "   -" if value is None else f"{100 * value:3.0f}%"


class Command(BaseCommand):
    help = ("Run classification and levelling on the reference transcripts with the configured LLM "
            "and report how closely the output matches. Nothing is saved to the database.")

    def add_arguments(self, parser):
        parser.add_argument("--reference", default=str(Path(settings.BASE_DIR) / "eval" / "reference.json"),
                            help="Reference set to score against (default: eval/reference.json)")
        parser.add_argument("--model", help="Model to use for this run (overrides OLLAMA_MODEL / BEDROCK_MODEL_ID)")
        parser.add_argument("--limit", type=int, help="Only run the first N cases")
        parser.add_argument("--max-tokens", type=int, default=3000,
                            help="Cap on each model response, so a model that loops fails fast instead of "
                                 "hanging (default: 3000, enough for the reference transcripts)")
        parser.add_argument("--stages", default=",".join(STAGES), help=f"Comma-separated, from: {', '.join(STAGES)}")
        parser.add_argument("--output", default=str(Path(settings.BASE_DIR) / "eval" / "reports"),
                            help="Folder for the JSON report (default: eval/reports)")

    def handle(self, *args, **options):
        stages = [stage.strip() for stage in options["stages"].split(",") if stage.strip()]
        unknown = set(stages) - set(STAGES)
        if unknown:
            raise CommandError(f"Unknown stage(s): {', '.join(sorted(unknown))}")

        provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        if options["model"]:
            os.environ["BEDROCK_MODEL_ID" if provider == "bedrock" else "OLLAMA_MODEL"] = options["model"]
        os.environ["LLM_MAX_TOKENS"] = str(options["max_tokens"])
        model = get_llm_model().model_name

        reference = json.loads(Path(options["reference"]).read_text())
        cases = reference["cases"][:options["limit"]]
        reviewed = sum(bool(case.get("reviewed")) for case in cases)
        self.stdout.write(f"Model: {provider} / {model}\n"
                          f"Cases: {len(cases)} ({reviewed} human-reviewed)   Stages: {', '.join(stages)}\n")

        results = []
        for number, case in enumerate(cases, start=1):
            self.stdout.write(f"[{number}/{len(cases)}] {case['id']} ({len(case['text'].split())} words) ...")
            result = run_case(case, stages)
            results.append(result)
            for stage in stages:
                outcome = result.get(stage)
                if outcome:
                    status = outcome.get("error", "ok")
                    self.stdout.write(f"    {stage}: {status} ({outcome['seconds']}s)")

        summary = summarise(results)
        self.print_summary(summary, stages)

        output = Path(options["output"])
        output.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        report = output / f"{stamp}-{model.replace('/', '_').replace(':', '_')}.json"
        report.write_text(json.dumps({
            "provider": provider, "model": model, "run_at": stamp, "stages": stages,
            "reference": options["reference"], "reviewed_cases": reviewed,
            "summary": summary, "cases": results,
        }, indent=2, ensure_ascii=False))
        self.stdout.write(f"\nReport: {report}")

    def print_summary(self, summary, stages):
        write = self.stdout.write
        if "classification" in stages:
            write("\nClassification (statements matched against the reference)")
            write(f"  {'category':<16} {'precision':>9} {'recall':>7} {'F1':>5}   found  missed  extra")
            for category, s in summary["classification"].items():
                write(f"  {category:<16} {ratio(s['precision']):>9} {ratio(s['recall']):>7} {ratio(s['f1']):>5}"
                      f"   {s['tp']:5d}  {s['fn']:6d}  {s['fp']:5d}")
            write(f"  Verbatim quotes: {pct(summary['verbatim'], summary['predicted']).strip()} "
                  f"of {summary['predicted']} predicted statements")
            write(f"  Failed cases: {summary['classification_errors']} of {summary['cases']}")
        if "levelling" in stages and summary["levelling"]:
            write("\nLevelling (reference statements, level 1-4)")
            write(f"  {'category':<16} {'exact':>6} {'within 1':>9} {'avg error':>10}   scored")
            for category, s in summary["levelling"].items():
                average = f"{s['abs_error'] / s['scored']:.2f}" if s["scored"] else "-"
                write(f"  {category:<16} {pct(s['exact'], s['scored']):>6} {pct(s['within_one'], s['scored']):>9}"
                      f" {average:>10}   {s['scored']} of {s['statements']}")
            write(f"  Failed cases: {summary['levelling_errors']} of {summary['cases']}")
        write(f"\nModel time: {summary['seconds']}s")
