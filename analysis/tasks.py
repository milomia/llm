from __future__ import absolute_import, unicode_literals

from celery import shared_task
from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput
from analysis.llm import get_llm_model, make_agent

from .models import Transcription, StatementClassification, StatementLevelPrompt, FinalStatementWithLevel
from .serializers import TranscriptionSerializer
from .utils import create_overlapping_segments, get_statements_data, get_important_note_and_parser, clear_previous_results
from .outputParser import EvaluationResult
from .langfuse_client import create_trace
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
    
    # Create Langfuse trace for classification
    trace = create_trace(
        name="classification_celery",
        session_id=str(transcription_id),
        metadata={"transcript_id": transcription_id, "task": "classify_segments"}
    )
    
    # Same logic as we have built in the API code earlier
    transcription = Transcription.objects.get(id=transcription_id)
    clear_previous_results(transcription)
    total_segments = len(transcription.segments)

    for index, segment in enumerate(transcription.segments):
        # Create span for segment processing
        segment_span = trace.span(
            name=f"segment_{index + 1}",
            metadata={"segment_index": index + 1, "total_segments": total_segments}
        )
        
        # Here goes the detail classification logic that you build
        # Obtaining statement type, creating a prompt, running classification_chain, etc.

        # INITIAL_PROCESSING
        # Get all the statement category types
        statement_type_considered, different_statement_definition = get_statements_data(index + 1, total_segments, segment)
        important_note, agent = get_important_note_and_parser(statement_type_considered, index + 1, total_segments)

        user_prompt = (
                "Respond with ONLY a JSON object, no explanation, no markdown, no preamble. "
                "Return ONLY valid JSON. Do not include explanations, markdown, or extra text. "
                "READ THE " + str(index + 1) + " PART OF THE TRANSCRIPT (WHOLE TRANSCRIPT HAS TOTAL " + str(
            total_segments)
                + " PARTS, with overlaps of 200 words in each part).\n"
                + " CRITICAL: Copy each statement EXACTLY as it appears in the transcript. "
                  "Do NOT paraphrase, summarise, truncate, or add ellipsis (...). "
                  "The conversation is between a representative (REP) and one or more healthcare professionals (HCPs). "
                  "\nRead the transcript part line by line:\n<transcript>\n{transcript}\n</transcript>\n\n"
                  "Objective: Review and classify dialogues from interactions between pharmaceutical sales representatives (REPs) and healthcare professionals (HCPs)."
                  " Each dialogue may belong to MORE THAN ONE OR NONE of the following categories( based on its content, intention and definition of the category):\n"
                + ", ".join(statement_type_considered) + "\n"
                                                         " This requires discerning the REP's strategic approach towards initiating the conversation,"
                                                         " engaging in inquiry, presenting information, and steering towards a productive conclusion."
                                                         "\n\nDetailed Definition for Classification::\n"
                                                         "\n{different_statement_definition}\n\n"
                                                         "Important Notes:\n"
                                                         "###{important_note}\n\n"
                                                         "Maintain the original transcript form for authenticity, "
                                                         "focusing on the accuracy and relevance of each classification.###\n\n"
                                                         "Assignment Execution: ### Thoroughly proceed through the transcripts,"
                                                         " identifying and classifying each of REP dialogues according to the category's definition, category's examples and category's invalid examples."
                                                         "Also take care of the guidelines and notes provided. Utilize a nuanced approach to determine the strategic intent "
                                                         "and outcome of the dialogue within the structured interaction framework.###"
        )

        # Create span for AI agent call
        agent_span = segment_span.span(name="agent_classification")
        
        result = agent.run_sync(user_prompt.format(
            transcript=segment,
            different_statement_definition=different_statement_definition,
            important_note=important_note
        ))
        response = result.output
        print(response)
        
        # Log agent call details
        agent_span.end(
            output=str(response),
            metadata={
                "statement_types": statement_type_considered,
                "segment_length": len(segment)
            }
        )

        category_map = {
            'OPENING': getattr(response, 'opening_statements', []),
            'QUESTIONING': getattr(response, 'questioning_statements', []),
            'PRESENTING': getattr(response, 'presenting_statements', []),
            'CLOSING_OUTCOME': getattr(response, 'closing_outcome_sentences', []),
        }

        for category, statements in category_map.items():
            print("Creating objects for : ", category)
            for statement in statements:
                classifcation_obj = StatementClassification(
                    category=category,
                    transcription=transcription,
                    statement=str(statement),
                    segment_number=index + 1
                )
                classifcation_obj.save()
            print("Finished creating the Classification objects for the statement type: ", category)
        
        # End segment span
        segment_span.end()
    
    # End trace
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
