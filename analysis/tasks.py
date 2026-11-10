from __future__ import absolute_import, unicode_literals

from celery import shared_task
from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput
from analysis.llm import get_llm_model, make_agent

from .models import Transcription, StatementLevelPrompt, FinalStatementWithLevel
from .serializers import TranscriptionSerializer
from .utils import create_overlapping_segments
from .outputParser import EvaluationResult
from .langfuse_client import create_trace
from .classification import classify_transcription
from .levelling import level_category
from .sentiment import analyze_sentiment


# Include the necessary modules and functions such as
# get_statements_data, get_important_note_and_parser,
# classify_segments function, statement classification objects creation, etc.
@shared_task
def save_transcription(transcription_data):
    print("Saving transcription data")
    segment_length = 6000  # Adjust as needed
    overlap = 100  # Adjust as needed
    print(type(transcription_data))
    serializer = TranscriptionSerializer(data=transcription_data)
    if serializer.is_valid():
        instance = serializer.save()
        instance.segments = create_overlapping_segments(transcription_data['text'], segment_length, overlap)
        instance.save()
        classify_segments.delay(instance.id)
        return instance.id
    else:
        return serializer.errors

@shared_task
def classify_segments(transcription_id):
    print("Classifying segments")
    trace = create_trace(
        name="classification_celery",
        session_id=str(transcription_id),
        metadata={"transcript_id": transcription_id, "task": "classify_segments"}
    )
    transcription = Transcription.objects.get(id=transcription_id)
    total_segments = classify_transcription(transcription, trace)
    trace.end(output={"status": "completed", "total_segments": total_segments})

    # After classification, the next task in the sequence is initiated:
    level_statements.delay(transcription.id)

@shared_task
def level_statements(transcription_id):
    print("level_statements")
    
    # Create Langfuse trace for levelling
    trace = create_trace(
        name="levelling_celery",
        session_id=str(transcription_id),
        metadata={"transcript_id": transcription_id, "task": "level_statements"}
    )
    
    # Use structured pydantic_ai output to level statements and save the results.
    transcription = Transcription.objects.get(id=transcription_id)

    sentences = transcription.statementclassification_set.all()
    for category in ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING_OUTCOME']:
        # Create span for category processing
        category_span = trace.span(name=f"category_{category}")
        statements = list(sentences.filter(category=category).filter(levelDone=False).values('id', 'statement'))
        classification_statements = sentences.filter(category=category).filter(levelDone=False)

        statement_level_obj = StatementLevelPrompt.objects.filter(active=True).filter(category=category).first()
        if len(statements) == 0 or not statement_level_obj:
            category_span.end(output={"status": "skipped", "reason": "no statements or no prompt"})
            continue
        unscored = level_category(category, transcription, statement_level_obj, parent_span=category_span)
        
        # End category span
        category_span.end(output={"status": "completed", "statements_processed": len(statements) - len(unscored),
                                  "unscored": unscored})
    
    # End trace
    trace.end(output={"status": "completed"})
    analyze_sentiment_task.delay(transcription_id)


@shared_task
def analyze_sentiment_task(transcription_id):
    analyze_sentiment(transcription_id)


# Invoke this from the APIView as before
