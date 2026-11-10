from __future__ import absolute_import, unicode_literals

from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput
from analysis.llm import get_llm_model, make_agent

from .models import Transcription, StatementLevelPrompt, FinalStatementWithLevel
from .serializers import TranscriptionSerializer
from .utils import create_overlapping_segments
from .outputParser import EvaluationResult
from .classification import classify_transcription
from .levelling import level_category
from .sentiment import analyze_sentiment


# Include the necessary modules and functions such as
# get_statements_data, get_important_note_and_parser,
# classify_segments function, statement classification objects creation, etc.

def sync_save_transcription(transcription_data):
    segment_length = 6000  # Adjust as needed
    overlap = 100  # Adjust as needed
    print(type(transcription_data))
    serializer = TranscriptionSerializer(data=transcription_data)
    if serializer.is_valid():
        instance = serializer.save()
        instance.segments = create_overlapping_segments(transcription_data['text'], segment_length, overlap)
        instance.save()
        sync_classify_segments(instance.id)
        return instance.id
    else:
        return serializer.errors

def sync_classify_segments(transcription_id):
    transcription = Transcription.objects.get(id=transcription_id)
    classify_transcription(transcription)
    # After classification, the next stage in the sequence is run:
    sync_level_statements(transcription.id)


def sync_level_statements(transcription_id):
    # Use structured pydantic_ai output to level statements and save the results.
    transcript = Transcription.objects.get(id=transcription_id)

    sentences = transcript.statementclassification_set.all()
    for category in ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING_OUTCOME']:
        statements = list(sentences.filter(category=category).filter(levelDone=False).values('id', 'statement'))
        classification_statements = sentences.filter(category=category).filter(levelDone=False)

        statement_level_obj = StatementLevelPrompt.objects.filter(active=True).filter(category=category).first()
        if len(statements) == 0 or not statement_level_obj:
            continue
        level_category(category, transcript, statement_level_obj)

    # Sentiment is supplementary: don't fail the whole pipeline if it errors (re-run via /sentiment/)
    try:
        analyze_sentiment(transcription_id)
    except Exception as exc:
        print(f"Sentiment analysis failed for transcript {transcription_id}: {exc}")



# Invoke this from the APIView as before
