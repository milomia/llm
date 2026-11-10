"""
Request/response shapes for the OpenAPI docs (drf-spectacular).

These serializers only describe the API; the views don't use them for validation,
so changing them never changes runtime behaviour.
"""
from rest_framework import serializers


class TranscriptTextRequest(serializers.Serializer):
    text = serializers.CharField(help_text="Full transcript text.")


class TranscriptUploadRequest(serializers.Serializer):
    file = serializers.FileField(required=False, help_text="UTF-8 text file containing the transcript.")
    text = serializers.CharField(required=False, help_text="Transcript text, used when no file is uploaded.")


class TranscriptCreatedResponse(serializers.Serializer):
    transcript_id = serializers.IntegerField()
    number_of_segments = serializers.IntegerField()


class PendingTranscriptsResponse(serializers.Serializer):
    pending_transcript = serializers.ListField(
        child=serializers.IntegerField(),
        help_text="IDs of transcripts not yet fetched by the results consumer.",
    )


class TranscriptIdRequest(serializers.Serializer):
    transcript_id = serializers.IntegerField()


class MessageResponse(serializers.Serializer):
    message = serializers.CharField()


class VectorStoreRequest(serializers.Serializer):
    collection_name = serializers.CharField(help_text="Weaviate collection, e.g. OPENING_CORRECT_EXAMPLE.")
    statements = serializers.ListField(child=serializers.CharField(), help_text="Example statements to store.")


# --- Full pipeline result (getDockerOutput) ------------------------------------------

class ConsolidatedScore(serializers.Serializer):
    category = serializers.CharField()
    score = serializers.IntegerField(help_text="Highest level (1-4) reached in this category.")


class ScoredSentence(serializers.Serializer):
    sentence = serializers.CharField()
    speaker = serializers.CharField()
    criteria = serializers.CharField(help_text="Level (1-4) as a string.")
    criteria_confidence_score = serializers.CharField(allow_null=True)
    category = serializers.CharField(required=False, help_text="Closing & outcome sentences only.")
    call_to_action = serializers.ListField(child=serializers.CharField(), required=False)
    call_to_action_confidence = serializers.CharField(required=False)


class CategoryResult(serializers.Serializer):
    category = serializers.CharField()
    category_confidence_score = serializers.IntegerField()
    consolidated_close_score = serializers.IntegerField(required=False)
    consolidated_outcome_score = serializers.IntegerField(required=False)
    sentences = ScoredSentence(many=True)
    transcript_chunks = serializers.CharField()


class CallToActionScore(serializers.Serializer):
    category = serializers.CharField()
    score = serializers.CharField()


class PipelineResultResponse(serializers.Serializer):
    consolidate_scores = ConsolidatedScore(many=True)
    transcript = CategoryResult(many=True)
    status = serializers.CharField()
    code = serializers.CharField()
    error_msg = serializers.CharField()
    merged_speakers = serializers.ListField(child=serializers.DictField())
    speaker_total_time = serializers.DictField(child=serializers.FloatField())
    consolidated_call_to_action_scores = CallToActionScore(many=True)


class SentimentStatement(serializers.Serializer):
    id = serializers.IntegerField()
    category = serializers.CharField()
    segment_number = serializers.IntegerField(allow_null=True)
    statement = serializers.CharField()
    hcp_sentiment = serializers.CharField(allow_null=True, help_text="positive, neutral, negative or no_response; null if not yet analysed.")
    confidence_score = serializers.IntegerField(allow_null=True)
    reason = serializers.CharField(allow_null=True)


class SentimentResultResponse(serializers.Serializer):
    transcript_id = serializers.IntegerField()
    summary = serializers.DictField(child=serializers.IntegerField(), help_text="Count of statements per sentiment label.")
    statements = SentimentStatement(many=True)
