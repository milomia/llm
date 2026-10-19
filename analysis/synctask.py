from __future__ import absolute_import, unicode_literals

from pydantic_ai import Agent
from pydantic_ai.output import NativeOutput
from analysis.llm import get_llm_model, make_agent

from .models import Transcription, StatementClassification, StatementLevelPrompt, FinalStatementWithLevel
from .serializers import TranscriptionSerializer
from .utils import create_overlapping_segments, get_statements_data, get_important_note_and_parser, clear_previous_results
from .outputParser import EvaluationResult
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
    # Same logic as we have built in the API code earlier
    transcription = Transcription.objects.get(id=transcription_id)
    clear_previous_results(transcription)
    total_segments = len(transcription.segments)

    for index, segment in enumerate(transcription.segments):
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

        result = agent.run_sync(user_prompt.format(
            transcript=segment,
            different_statement_definition=different_statement_definition,
            important_note=important_note
        ))
        response = result.output
        print(response)

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
        # After classification, the next task in the sequence is initiated:
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
