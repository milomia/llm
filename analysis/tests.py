from unittest.mock import patch, MagicMock

from django.test import TestCase

from analysis.models import Transcription, StatementClassification
from analysis.outputParser import SentimentResult, StatementSentimentModel
from analysis.sentiment import analyze_sentiment, get_sentiment_results


class SentimentTests(TestCase):
    def setUp(self):
        self.t = Transcription.objects.create(text="x", segments=["REP: hi. HCP: great, tell me more."])
        self.a = StatementClassification.objects.create(
            transcription=self.t, category="OPENING", statement="hi", segment_number=1)
        self.b = StatementClassification.objects.create(
            transcription=self.t, category="PRESENTING", statement="drug X", segment_number=1)

    @patch("analysis.sentiment.make_agent")
    def test_saves_sentiment_and_ignores_unknown_ids(self, make_agent):
        make_agent.return_value.run_sync.return_value = MagicMock(output=SentimentResult(statements=[
            StatementSentimentModel(id=self.a.id, sentiment="positive", confidence_score=90, reason="keen"),
            StatementSentimentModel(id=99999, sentiment="negative", confidence_score=10, reason="bogus"),
        ]))
        analyze_sentiment(self.t.id)

        self.a.refresh_from_db()
        self.b.refresh_from_db()
        self.assertEqual((self.a.hcp_sentiment, self.a.sentimentDone), ("positive", True))
        self.assertFalse(self.b.sentimentDone)

        result = get_sentiment_results(self.t.id)
        self.assertEqual(result["summary"], {"positive": 1})
        self.assertEqual(len(result["statements"]), 2)

    @patch("analysis.sentiment.make_agent")
    def test_retries_only_statements_the_model_skipped(self, make_agent):
        first = MagicMock(output=SentimentResult(statements=[
            StatementSentimentModel(id=self.a.id, sentiment="positive", confidence_score=90, reason="keen")]))
        second = MagicMock(output=SentimentResult(statements=[
            StatementSentimentModel(id=self.b.id, sentiment="neutral", confidence_score=70, reason="ok")]))
        make_agent.return_value.run_sync.side_effect = [first, second]
        analyze_sentiment(self.t.id)

        self.assertEqual(make_agent.return_value.run_sync.call_count, 2)
        retry_prompt = make_agent.return_value.run_sync.call_args_list[1].args[0]
        self.assertIn("drug X", retry_prompt)
        self.assertNotIn("'statement': 'hi'", retry_prompt)
        self.assertEqual(StatementClassification.objects.filter(transcription=self.t, sentimentDone=True).count(), 2)

    @patch("analysis.sentiment.make_agent")
    def test_skips_already_done(self, agent_cls):
        StatementClassification.objects.filter(transcription=self.t).update(sentimentDone=True)
        analyze_sentiment(self.t.id)
        agent_cls.assert_not_called()


class ClearPreviousResultsTests(TestCase):
    def test_replaces_only_this_transcripts_results(self):
        from analysis.models import FinalStatementWithLevel
        from analysis.utils import clear_previous_results
        t1 = Transcription.objects.create(text="x", segments=["a"])
        t2 = Transcription.objects.create(text="y", segments=["b"])
        for t in (t1, t2):
            StatementClassification.objects.create(transcription=t, category="OPENING", statement="hi", segment_number=1)
            FinalStatementWithLevel.objects.create(transcription=t, category="OPENING", statement="hi",
                                                   level=1, confidence_score=50, reason_for_level="r")
        clear_previous_results(t1)

        self.assertEqual(StatementClassification.objects.filter(transcription=t1).count(), 0)
        self.assertEqual(FinalStatementWithLevel.objects.filter(transcription=t1).count(), 0)
        self.assertEqual(StatementClassification.objects.filter(transcription=t2).count(), 1)
        self.assertEqual(FinalStatementWithLevel.objects.filter(transcription=t2).count(), 1)


class LevellingTests(TestCase):
    def setUp(self):
        from analysis.models import StatementLevelPrompt
        self.t = Transcription.objects.create(text="x", segments=["seg"])
        self.a = StatementClassification.objects.create(
            transcription=self.t, category="OPENING", statement="hi", segment_number=1)
        self.b = StatementClassification.objects.create(
            transcription=self.t, category="OPENING", statement="hello there", segment_number=1)
        self.prompt = StatementLevelPrompt.objects.create(
            category="OPENING", objective="o", evaluation_criteria="e", score_assignment_criteria="s",
            instruction="i", examples="x", notes="n", active=True)

    def _result(self, *ids):
        from analysis.outputParser import EvaluationResult, StatementLevelModel
        return MagicMock(output=EvaluationResult(statements=[
            StatementLevelModel(id=i, level=2, confidence_score=80, reason="r") for i in ids]))

    @patch("analysis.levelling.make_agent")
    def test_retries_skipped_statements_and_marks_only_scored_done(self, make_agent):
        from analysis.levelling import level_category
        from analysis.models import FinalStatementWithLevel
        make_agent.return_value.run_sync.side_effect = [self._result(self.a.id), self._result(self.b.id)]
        self.assertEqual(level_category("OPENING", self.t, self.prompt), [])
        self.assertEqual(FinalStatementWithLevel.objects.filter(transcription=self.t).count(), 2)
        self.assertEqual(StatementClassification.objects.filter(levelDone=True).count(), 2)

    @patch("analysis.levelling.make_agent")
    def test_unscored_statements_stay_pending(self, make_agent):
        from analysis.levelling import level_category
        from analysis.models import FinalStatementWithLevel
        make_agent.return_value.run_sync.return_value = self._result(self.a.id)
        self.assertEqual(level_category("OPENING", self.t, self.prompt), [self.b.id])
        self.assertEqual(FinalStatementWithLevel.objects.filter(transcription=self.t).count(), 1)
        self.b.refresh_from_db()
        self.assertFalse(self.b.levelDone)


class ClassificationTests(TestCase):
    @patch("analysis.classification.get_important_note_and_parser")
    @patch("analysis.classification.get_statements_data")
    def test_replaces_old_rows_and_saves_statements_per_segment(self, get_statements_data, get_parser):
        from analysis.classification import classify_transcription
        from analysis.outputParser import StatementParser, StatementParserWithoutOpening
        t = Transcription.objects.create(text="x", segments=["first part {braces}", "second part"])
        StatementClassification.objects.create(transcription=t, category="OPENING", statement="stale", segment_number=1)
        get_statements_data.side_effect = [
            (["OPENING", "QUESTIONING", "PRESENTING", "CLOSING_OUTCOME"], "defs-1"),
            (["QUESTIONING", "PRESENTING", "CLOSING_OUTCOME"], "defs-2"),
        ]
        closing = {"closing_statement": "bye", "outcome_statement": "ok"}
        agent = MagicMock()
        agent.run_sync.side_effect = [
            MagicMock(output=StatementParser(
                opening_statements=["hello"], questioning_statements=["how?"],
                presenting_statements=[], closing_outcome_sentences=[])),
            MagicMock(output=StatementParserWithoutOpening(
                questioning_statements=[], presenting_statements=["data"], closing_outcome_sentences=[closing])),
        ]
        get_parser.return_value = ("note", agent)

        self.assertEqual(classify_transcription(t), 2)

        rows = set(StatementClassification.objects.filter(transcription=t)
                   .values_list("category", "statement", "segment_number"))
        self.assertEqual(rows, {("OPENING", "hello", 1), ("QUESTIONING", "how?", 1),
                                ("PRESENTING", "data", 2), ("CLOSING_OUTCOME", str(closing), 2)})
        first_prompt = agent.run_sync.call_args_list[0].args[0]
        self.assertIn("READ THE 1 PART OF THE TRANSCRIPT (WHOLE TRANSCRIPT HAS TOTAL 2 PARTS", first_prompt)
        self.assertIn("<transcript>\nfirst part {braces}\n</transcript>", first_prompt)
        self.assertIn("OPENING, QUESTIONING, PRESENTING, CLOSING_OUTCOME\n", first_prompt)
        self.assertIn("defs-1", first_prompt)
        self.assertIn("###note", first_prompt)


class ModelSettingsTests(TestCase):
    def test_no_response_cap_unless_configured(self):
        from analysis.llm import get_model_settings
        with patch.dict("os.environ", {"LLM_PROVIDER": "ollama"}, clear=False) as env:
            env.pop("LLM_MAX_TOKENS", None)
            self.assertEqual(get_model_settings(), {"temperature": 0, "seed": 42})

    def test_response_cap_is_sent_in_the_form_each_provider_honours(self):
        from analysis.llm import get_model_settings
        with patch.dict("os.environ", {"LLM_PROVIDER": "ollama", "LLM_MAX_TOKENS": "500", "LLM_SEED": "42"}):
            self.assertEqual(get_model_settings(), {"temperature": 0, "seed": 42, "extra_body": {"max_tokens": 500}})
        with patch.dict("os.environ", {"LLM_PROVIDER": "bedrock", "LLM_MAX_TOKENS": "500"}):
            self.assertEqual(get_model_settings(), {"temperature": 0, "max_tokens": 500})
