"""Endpoint tests driven by data/request.json (a real transcript upload body).

No LLM, Weaviate, Celery or Langfuse is contacted: the agents are replaced by a fake that answers
each pipeline stage from the prompt it is given, so the tests are fast and deterministic.
"""
import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APITestCase

from analysis.langfuse_client import Observation
from analysis.models import (
    FinalStatementWithLevel, StatementClassification, StatementClassificationTypePrompt,
    StatementLevelPrompt, Transcription,
)
from analysis.outputParser import (
    EvaluationResult, SentimentResult, StatementLevelModel, StatementParser, StatementSentimentModel,
)

REQUEST_BODY = json.loads((Path(settings.BASE_DIR) / "data" / "request.json").read_text())
TEXT = REQUEST_BODY["text"]

CATEGORIES = ["OPENING", "QUESTIONING", "PRESENTING", "CLOSING_OUTCOME"]

# What the fake classifier "finds" in the transcript: real REP lines from request.json.
OPENING = "Hello Dr Lewis, can you see me, ok?"
QUESTION_1 = "Can I just check who else we have in the meeting please?"
QUESTION_2 = "Did any of you get the opportunity to attend the virtual ASCO meeting last month?"
PRESENTING = "You can order it direct from the company."
CLOSING = {
    "closing_statement": "Would it be ok to reach out to you after the webinar to discuss in more depth?",
    "outcome_statement": "Yes, that would be fine.",
}
CLASSIFIED = StatementParser(
    opening_statements=[OPENING],
    questioning_statements=[QUESTION_1, QUESTION_2],
    presenting_statements=[PRESENTING],
    closing_outcome_sentences=[CLOSING],
)
EXPECTED_ROWS = {
    ("OPENING", OPENING), ("QUESTIONING", QUESTION_1), ("QUESTIONING", QUESTION_2),
    ("PRESENTING", PRESENTING), ("CLOSING_OUTCOME", str(CLOSING)),
}


class EndpointTestCase(APITestCase):
    """Seeds the prompt tables and swaps every external dependency for a local fake."""

    def setUp(self):
        for category in CATEGORIES:
            StatementClassificationTypePrompt.objects.create(
                category=category, definition=f"definition of {category}", examples="e", invalid_examples="i")
            StatementLevelPrompt.objects.create(
                category=category, objective="o", evaluation_criteria="e", score_assignment_criteria="s",
                instruction="i", examples="x", notes="n")

        self.prompts = []  # (output model, prompt) for every agent call
        for target in ("analysis.utils.make_agent", "analysis.levelling.make_agent", "analysis.sentiment.make_agent"):
            self.enterContext(patch(target, side_effect=self.fake_agent))
        self.enterContext(patch("analysis.utils.get_similar_examples", return_value=([], [])))
        self.enterContext(patch("analysis.utils.get_llm_model"))
        self.enterContext(patch("analysis.views.create_trace", return_value=Observation()))

    def fake_agent(self, output_type):
        def run_sync(prompt):
            self.prompts.append((output_type, prompt))
            # Levelling and sentiment prompts list their statements as {'id': <pk>, 'statement': ...}
            ids = [int(i) for i in re.findall(r"'id': (\d+)", prompt)]
            if output_type is EvaluationResult:
                output = EvaluationResult(statements=[
                    StatementLevelModel(id=i, level=3, confidence_score=80, reason="clear") for i in ids])
            elif output_type is SentimentResult:
                output = SentimentResult(statements=[
                    StatementSentimentModel(id=i, sentiment="positive", confidence_score=70, reason="agrees")
                    for i in ids])
            else:
                output = CLASSIFIED
            return MagicMock(output=output)

        agent = MagicMock()
        agent.run_sync.side_effect = run_sync
        return agent

    def upload(self):
        response = self.client.post(reverse("transcript"), REQUEST_BODY, format="json")
        self.assertEqual(response.status_code, 201)
        return response.json()["transcript_id"]

    def rows(self, transcript_id):
        return set(StatementClassification.objects.filter(transcription_id=transcript_id)
                   .values_list("category", "statement"))


class RequestFileTests(EndpointTestCase):
    def test_request_file_is_a_valid_upload_body(self):
        self.assertEqual(list(REQUEST_BODY), ["text"])
        self.assertGreater(len(TEXT.split()), 2000)
        for statement in (OPENING, QUESTION_1, QUESTION_2, PRESENTING, *CLOSING.values()):
            self.assertIn(statement, TEXT)


class TranscriptionEndpointTests(EndpointTestCase):
    def test_upload_json_saves_text_and_segments(self):
        response = self.client.post(reverse("transcript"), REQUEST_BODY, format="json")

        self.assertEqual(response.status_code, 201)
        transcript = Transcription.objects.get(id=response.json()["transcript_id"])
        self.assertEqual(transcript.text, TEXT)
        self.assertEqual(response.json()["number_of_segments"], len(transcript.segments))
        self.assertEqual(" ".join(transcript.segments).split(), TEXT.split())  # one segment: nothing lost

    def test_upload_file_saves_the_same_text(self):
        upload = SimpleUploadedFile("call.txt", TEXT.encode("utf-8"), content_type="text/plain")
        response = self.client.post(reverse("transcript"), {"file": upload}, format="multipart")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(Transcription.objects.get(id=response.json()["transcript_id"]).text, TEXT)

    def test_upload_without_text_or_file_is_rejected(self):
        response = self.client.post(reverse("transcript"), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json())
        self.assertEqual(Transcription.objects.count(), 0)

    def test_upload_of_non_utf8_file_is_rejected(self):
        upload = SimpleUploadedFile("call.txt", b"\xff\xfe\x00bad", content_type="text/plain")
        response = self.client.post(reverse("transcript"), {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.json())

    def test_pending_list_drops_a_transcript_once_marked_fetched(self):
        transcript_id = self.upload()
        self.assertEqual(self.client.get(reverse("transcript")).json(), {"pending_transcript": [transcript_id]})

        response = self.client.get(reverse("transcript_details", args=[transcript_id]))

        self.assertEqual(response.json(), {"message": "done"})
        self.assertEqual(self.client.get(reverse("transcript")).json(), {"pending_transcript": []})

    def test_marking_an_unknown_transcript_fetched_returns_404(self):
        self.assertEqual(self.client.get(reverse("transcript_details", args=[999999])).status_code, 404)


class ClassificationEndpointTests(EndpointTestCase):
    def test_classifies_the_uploaded_transcript(self):
        transcript_id = self.upload()

        response = self.client.post(reverse("classification"), {"transcript_id": transcript_id}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.rows(transcript_id), EXPECTED_ROWS)
        output_type, prompt = self.prompts[0]
        self.assertIs(output_type, StatementParser)  # single segment: all four categories in play
        self.assertIn(f"<transcript>\n{Transcription.objects.get(id=transcript_id).segments[0]}\n</transcript>", prompt)
        for category in CATEGORIES:
            self.assertIn(f"definition of {category}", prompt)

    def test_rerunning_replaces_results_instead_of_duplicating(self):
        transcript_id = self.upload()
        for _ in range(2):
            self.client.post(reverse("classification"), {"transcript_id": transcript_id}, format="json")
        self.assertEqual(StatementClassification.objects.filter(transcription_id=transcript_id).count(),
                         len(EXPECTED_ROWS))

    def test_unknown_transcript_returns_404(self):
        response = self.client.post(reverse("classification"), {"transcript_id": 999999}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.prompts, [])


class RatingEndpointTests(EndpointTestCase):
    def test_levels_every_classified_statement(self):
        transcript_id = self.upload()
        self.client.post(reverse("classification"), {"transcript_id": transcript_id}, format="json")

        response = self.client.post(reverse("rating"), {"transcript_id": transcript_id}, format="json")

        self.assertEqual(response.status_code, 200)
        levelled = FinalStatementWithLevel.objects.filter(transcription_id=transcript_id)
        self.assertEqual(set(levelled.values_list("category", "statement")), EXPECTED_ROWS)
        self.assertEqual(set(levelled.values_list("level", "confidence_score")), {(3, "80")})
        self.assertFalse(StatementClassification.objects.filter(transcription_id=transcript_id, levelDone=False).exists())

    def test_rerunning_does_not_level_statements_twice(self):
        transcript_id = self.upload()
        self.client.post(reverse("classification"), {"transcript_id": transcript_id}, format="json")
        for _ in range(2):
            self.client.post(reverse("rating"), {"transcript_id": transcript_id}, format="json")
        self.assertEqual(FinalStatementWithLevel.objects.filter(transcription_id=transcript_id).count(),
                         len(EXPECTED_ROWS))

    def test_unknown_transcript_returns_404(self):
        response = self.client.post(reverse("rating"), {"transcript_id": 999999}, format="json")
        self.assertEqual(response.status_code, 404)


class SentimentEndpointTests(EndpointTestCase):
    def test_run_then_fetch_returns_a_label_for_every_statement(self):
        transcript_id = self.upload()
        self.client.post(reverse("classification"), {"transcript_id": transcript_id}, format="json")

        response = self.client.post(reverse("sentiment"), {"transcript_id": transcript_id}, format="json")

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["transcript_id"], transcript_id)
        self.assertEqual(body["summary"], {"positive": len(EXPECTED_ROWS)})
        self.assertEqual({(s["category"], s["statement"]) for s in body["statements"]}, EXPECTED_ROWS)
        self.assertEqual({(s["hcp_sentiment"], s["confidence_score"], s["reason"]) for s in body["statements"]},
                         {("positive", 70, "agrees")})
        self.assertEqual(self.client.get(reverse("sentiment_results", args=[transcript_id])).json(), body)

    def test_results_before_any_run_have_no_labels(self):
        transcript_id = self.upload()
        body = self.client.get(reverse("sentiment_results", args=[transcript_id])).json()
        self.assertEqual(body, {"transcript_id": transcript_id, "summary": {}, "statements": []})

    def test_unknown_transcript_returns_404(self):
        self.assertEqual(
            self.client.post(reverse("sentiment"), {"transcript_id": 999999}, format="json").status_code, 404)
        self.assertEqual(self.client.get(reverse("sentiment_results", args=[999999])).status_code, 404)


class ResultsEndpointTests(EndpointTestCase):
    def setUp(self):
        super().setUp()
        self.transcript = Transcription.objects.create(text=TEXT, segments=[TEXT])
        for category, statement, level in [
            ("OPENING", OPENING, 2),
            ("QUESTIONING", QUESTION_1, 2), ("QUESTIONING", QUESTION_2, 4),
            ("PRESENTING", PRESENTING, 3),
        ]:
            FinalStatementWithLevel.objects.create(
                transcription=self.transcript, category=category, statement=statement,
                level=level, confidence_score=90, reason_for_level="because")

    def test_results_returns_the_highest_level_statement_per_category(self):
        response = self.client.get(reverse("highest_level_statements", args=[self.transcript.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [(r["category"], r["statement"], r["level"]) for r in response.json()],
            [("OPENING", OPENING, 2), ("QUESTIONING", QUESTION_2, 4), ("PRESENTING", PRESENTING, 3)])
        self.assertEqual(response.json()[0]["reason_for_level"], "because")

    def test_results_for_a_transcript_with_no_levels_is_empty(self):
        other = Transcription.objects.create(text="x", segments=["x"])
        self.assertEqual(self.client.get(reverse("highest_level_statements", args=[other.id])).json(), [])

    def test_docker_results_groups_statements_and_scores_by_category(self):
        body = self.client.get(reverse("highest_level_statements_docker", args=[self.transcript.id])).json()

        self.assertEqual(body["status"], "Success")
        self.assertEqual(body["consolidate_scores"], [
            {"category": "Opening", "score": 2},
            {"category": "Questioning", "score": 4},
            {"category": "Presenting", "score": 3},
        ])
        questioning = next(c for c in body["transcript"] if c["category"] == "Questioning")
        self.assertEqual([s["sentence"] for s in questioning["sentences"]], [QUESTION_1, QUESTION_2])
        self.assertEqual([s["criteria"] for s in questioning["sentences"]], ["2", "4"])
        self.assertEqual(questioning["transcript_chunks"], f"{QUESTION_1} {QUESTION_2}")

    def add_closing(self, statement=str(CLOSING), level=3):
        FinalStatementWithLevel.objects.create(
            transcription=self.transcript, category="CLOSING_OUTCOME", statement=statement,
            level=level, confidence_score=90, reason_for_level="because")

    def test_results_include_closing_statements(self):
        self.add_closing()
        response = self.client.get(reverse("highest_level_statements", args=[self.transcript.id]))
        self.assertEqual([(r["category"], r["statement"], r["level"]) for r in response.json()][-1],
                         ("CLOSING_OUTCOME", str(CLOSING), 3))

    def test_docker_results_pair_each_closing_statement_with_its_outcome(self):
        self.add_closing()
        self.add_closing(statement="not a dict, just text", level=2)
        body = self.client.get(reverse("highest_level_statements_docker", args=[self.transcript.id])).json()

        self.assertEqual(body["consolidate_scores"][-1], {"category": "Closing & Outcome", "score": 3})
        closing = body["transcript"][-1]
        self.assertEqual((closing["category"], closing["consolidated_close_score"], closing["consolidated_outcome_score"]),
                         ("Closing & Outcome", 3, 3))
        self.assertEqual(
            [(s["category"], s["speaker"], s["sentence"], s["criteria"]) for s in closing["sentences"]],
            [("Closing", "REP", CLOSING["closing_statement"], "3"),
             ("Outcome", "HCP", CLOSING["outcome_statement"], "3"),
             ("Closing", "REP", "not a dict, just text", "2")])
        self.assertEqual(closing["sentences"][0]["call_to_action"], ["No CTA"])


class FullProcessEndpointTests(EndpointTestCase):
    def test_async_process_saves_the_transcript_and_queues_classification(self):
        with patch("analysis.views.classify_segments") as classify_segments:
            response = self.client.post(reverse("full_process_single_api"), REQUEST_BODY, format="json")

        self.assertEqual(response.status_code, 202)
        transcript = Transcription.objects.get(id=response.json()["transcript_id"])
        self.assertEqual(transcript.text, TEXT)
        self.assertEqual(response.json()["number_of_segments"], len(transcript.segments))
        classify_segments.delay.assert_called_once_with(transcript.id)
        self.assertEqual(self.prompts, [])  # nothing runs inside the request

    def test_async_process_without_text_is_rejected(self):
        with patch("analysis.views.classify_segments") as classify_segments:
            response = self.client.post(reverse("full_process_single_api"), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("text", response.json())
        classify_segments.delay.assert_not_called()

    def test_sync_process_runs_all_three_stages_and_returns_the_result(self):
        response = self.client.post(reverse("full_sync_process_single_api"), REQUEST_BODY, format="json")

        self.assertEqual(response.status_code, 200)
        transcript = Transcription.objects.get()
        self.assertEqual(self.rows(transcript.id), EXPECTED_ROWS)
        rows = StatementClassification.objects.filter(transcription=transcript)
        self.assertFalse(rows.filter(levelDone=False).exists())
        self.assertEqual(set(rows.values_list("hcp_sentiment", flat=True)), {"positive"})
        self.assertEqual([stage for stage, _ in self.prompts],
                         [StatementParser] + [EvaluationResult] * 4 + [SentimentResult])

        body = response.json()
        self.assertEqual(body["status"], "Success")
        scores = {score["category"]: score["score"] for score in body["consolidate_scores"]}
        self.assertEqual(scores, {"Opening": 3, "Questioning": 3, "Presenting": 3, "Closing & Outcome": 3})
        closing = next(c for c in body["transcript"] if c["category"] == "Closing & Outcome")
        self.assertEqual([s["sentence"] for s in closing["sentences"]], list(CLOSING.values()))
        questioning = next(c for c in body["transcript"] if c["category"] == "Questioning")
        self.assertEqual({s["sentence"] for s in questioning["sentences"]}, {QUESTION_1, QUESTION_2})

    def test_sync_process_without_text_is_rejected(self):
        response = self.client.post(reverse("full_sync_process_single_api"), {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Transcription.objects.count(), 0)


class VectorDbEndpointTests(EndpointTestCase):
    def test_stores_statements_in_the_named_collection(self):
        statements = [OPENING, QUESTION_1]
        with patch("analysis.views.storeData") as store_data:
            response = self.client.post(
                reverse("vectorDb"),
                {"collection_name": "OPENING_CORRECT_EXAMPLE", "statements": statements}, format="json")

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json(), {"message": "data has been stored in OPENING_CORRECT_EXAMPLE"})
        store_data.assert_called_once_with("OPENING_CORRECT_EXAMPLE", statements)
