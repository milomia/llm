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
