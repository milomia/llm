import re

from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse
from django.db.models import Max
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from analysis.aiService.weaviateDb import storeData
from analysis.serializers import TranscriptionSerializer
from analysis.models import Transcription, StatementClassification, StatementLevelPrompt, FinalStatementWithLevel
from analysis.utils import create_overlapping_segments, get_statements_data, get_important_note_and_parser
from analysis.langfuse_client import create_trace

from pydantic_ai import Agent
from pydantic_ai.models.ollama import OllamaModel
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_ai.output import NativeOutput

from .outputParser import EvaluationResult
from .synctask import sync_classify_segments
from .tasks import save_transcription, classify_segments

load_dotenv()


def extract_msl_statements(transcript):
    """
    Splits transcript by speaker label and returns only MSL turns,
    one per line, preserving original text.
    """
    # Split on speaker labels — handles MSL, Dr, DR, JDr, NS, ALL
    parts = re.split(r'(MSL|DR|Dr|JDr|NS|ALL)', transcript)

    msl_lines = []
    for i, part in enumerate(parts):
        if part == 'MSL' and i + 1 < len(parts):
            text = parts[i + 1].strip()
            if text:
                msl_lines.append(f"MSL {text}")

    return "\n".join(msl_lines)

# set_debug(True)

class ClassificationView(APIView):


    def post(self, request):
        transcript_id = request.data['transcript_id']
        print(transcript_id)
        
        # Create Langfuse trace for classification
        trace = create_trace(
            name="classification",
            session_id=str(transcript_id),
            metadata={"transcript_id": transcript_id}
        )
        
        transcript = Transcription.objects.get(id=transcript_id)

        total_segments = len(transcript.segments)

        for index, segment in enumerate(transcript.segments):

            # Create span for segment processing
            segment_span = trace.span(
                name=f"segment_{index + 1}",
                metadata={"segment_index": index + 1, "total_segments": total_segments}
            )

            # Pre-process: strip HCP lines, keep only MSL turns
            msl_segment = extract_msl_statements(segment)

            # INITIAL_PROCESSING
            # Get all the statement category types
            statement_type_considered, different_statement_definition = get_statements_data(index + 1, total_segments)
            important_note, agent = get_important_note_and_parser(statement_type_considered, index + 1, total_segments)

            # Build the prompt for pydantic_ai
            user_prompt = (
                    "Respond with ONLY a JSON object, no explanation, no markdown, no preamble. "
                    "Return ONLY valid JSON. Do not include explanations, markdown, or extra text. "
                    "READ THE " + str(index + 1) + " PART OF THE TRANSCRIPT (WHOLE TRANSCRIPT HAS TOTAL " + str(
                total_segments)
                    + " PARTS, with overlaps of 200 words in each part).\n"
                    + " CRITICAL: Only classify statements made by the REP (labelled MSL). "
                      " Never include HCP, DR, NS, or JDr statements in any category."
                    + " CRITICAL: Copy each statement EXACTLY as it appears in the transcript. " 
                      " Do NOT paraphrase, summarise, truncate, or add ellipsis (...). "
                      " The statement field must contain the complete original text word for word. "
                      "The conversation is between a representative (REP) and one or more healthcare professionals (HCPs).\n"
                      "Read the transcript part line by line:\n<transcript>\n{transcript}\n</transcript>\n\n"
                      "Objective: Review and classify dialogues from interactions between pharmaceutical sales representatives (REPs) and healthcare professionals (HCPs). "
                      "Each dialogue may belong to MORE THAN ONE OR NONE of the following categories (based on its content, intention and definition of the category):\n"
                    + ", ".join(statement_type_considered) + "\n"
                     "This requires discerning the REP's strategic approach towards initiating the conversation, "
                     "engaging in inquiry, presenting information, and steering towards a productive conclusion.\n\n"
                     "Detailed Definition for Classification:\n"
                     "<definitions>\n{different_statement_definition}\n</definitions>\n\n"
                     "Important Notes:\n"
                     "<notes>\n{important_note}\n</notes>\n\n"
                     "Maintain the original transcript form for authenticity, "
                     "focusing on the accuracy and relevance of each classification.\n\n"
                     "Assignment Execution: Thoroughly proceed through the transcript, "
                     "identifying and classifying each REP dialogue according to the category definitions, examples, and invalid examples. "
                     "Take care of the guidelines and notes provided. Utilize a nuanced approach to determine the strategic intent "
                     "and outcome of each dialogue within the structured interaction framework.\n\n"
            )

            # Create span for AI agent call
            agent_span = segment_span.span(name="agent_classification")
            
            result = agent.run_sync(user_prompt.format(
                transcript=msl_segment or segment,
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
                    "segment_length": len(msl_segment or segment)
                }
            )

            category_map = {
                'OPENING': getattr(response, 'opening_statements', []),
                'QUESTIONING': getattr(response, 'questioning_statements', []),
                'PRESENTING': getattr(response, 'presenting_statements', []),
                'CLOSING_OUTCOME': getattr(response, 'closing_outcome_sentences', []),
            }

            for category, statements in category_map.items():
                print("Creating objects for:", category)
                for statement in statements:
                    classification_obj = StatementClassification(
                        category=category,
                        transcription=transcript,
                        statement=str(statement),
                        segment_number=index + 1
                    )
                    classification_obj.save()
                print("Finished creating Classification objects for:", category)
            
            # End segment span
            segment_span.end()

        # End trace
        trace.update(output={"status": "completed", "total_segments": total_segments})
        
        return Response({"message": "action is finished"}, status=status.HTTP_201_CREATED)

class TranscriptionView(APIView):

    def get(self, request):
        transcripts = Transcription.objects.filter(docker_feteched=False)
        return Response({"pending_transcript": [transcript.id for transcript in transcripts]}, status=status.HTTP_200_OK)

    def post(self, request):
        # Desired segment length and overlap
        segment_length = 4000  # Adjusted due to example length; use 1200 for your full text
        overlap = 100
        trans_obj = request.data
        # Create overlapping segments
        print(trans_obj)
        trans_obj['segments'] = create_overlapping_segments(trans_obj['text'], segment_length, overlap)

        serializer = TranscriptionSerializer(data=trans_obj)

        if serializer.is_valid():
            instance = serializer.save()
            instance.segments = create_overlapping_segments(trans_obj['text'], segment_length, overlap)
            instance.save()
            return Response({"transcript_id": instance.id, "number_of_segments": len(instance.segments)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def transcription_status_update(request, transcript_id):
    obj = Transcription.objects.filter(id=transcript_id).first()
    obj.docker_feteched = True
    obj.save()
    return JsonResponse({"message": "done"}, safe=False)

class VectorDataView(APIView):

    def get(self, request):
        pass

    def post(self, request):
        statements = request.data['statements']
        collection_name = request.data['collection_name']
        
        # Create Langfuse trace for vector database operations
        trace = create_trace(
            name="vector_db_store",
            metadata={
                "collection_name": collection_name,
                "num_statements": len(statements)
            }
        )
        
        # Create span for storage operation
        storage_span = trace.span(name="store_data")
        
        storeData(collection_name, statements)
        
        storage_span.end(output={"status": "stored", "collection": collection_name})
        trace.update(output={"status": "completed"})
        
        return Response(
            {"message": "data has been stored in {collection_name}".format(collection_name=collection_name)},
            status=status.HTTP_201_CREATED
        )

class LevellingDataView(APIView):

    def post(self, request):
        transcript_id = request.data['transcript_id']
        print(transcript_id)
        
        # Create Langfuse trace for levelling
        trace = create_trace(
            name="levelling",
            session_id=str(transcript_id),
            metadata={"transcript_id": transcript_id}
        )
        
        transcript = Transcription.objects.get(id=transcript_id)
        sentences = transcript.statementclassification_set.all()

        for category in ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING_OUTCOME']:
            # Create span for category processing
            category_span = trace.span(name=f"category_{category}")
            
            statements = list(sentences.filter(category=category).filter(levelDone=False).values('id', 'statement'))
            classification_statements = sentences.filter(category=category).filter(levelDone=False)

            if not statements:
                print(f"No statements for {category}, skipping")
                category_span.end(output={"status": "skipped", "reason": "no statements"})
                continue

            statement_level_obj = StatementLevelPrompt.objects.filter(active=True).filter(category=category).first()
            if not statement_level_obj:
                print(f"No StatementLevelPrompt found for {category}, skipping")
                category_span.end(output={"status": "skipped", "reason": "no prompt"})
                continue

            # Use pydantic_ai Agent with OllamaModel for structured output
            model = OllamaModel(
                'llama3',
                provider=OllamaProvider(base_url='http://localhost:11434/v1')
            )
            agent = Agent(model, output_type=NativeOutput(EvaluationResult))

            # Build the prompt for pydantic_ai
            user_prompt = (
                category + " statements: \n{statements}\n\n"
                           "Objective: !!!{objective}!!!\n\n"
                           "Evaluation Criteria:\n ###{evaluation_criteria}###\n\n"
                           "Score assignment criteria:\n ###{score_assignment_criteria}###\n\n"
                           "Instruction:\n ###{instruction}###\n\n"
                           "Examples:\n ###{examples}###\n\n"
                           "notes:\n ###{notes}###\n\n"
                           "CRITICAL: For EVERY statement you MUST provide:\n"
                           "- level: integer 1-4 based on score assignment criteria\n"
                           "- confidence_score: integer 0-100 representing how certain you are about YOUR level assignment. "
                           "This is NOT the quality score — it is YOUR confidence in the level you assigned. "
                           "A level 1 statement can still have confidence_score of 90 if you are certain it is level 1.\n"
                           "- reason: max 1 line explaining the level assignment\n\n"
                           "Return data matching this shape exactly:\n"
                           "{{\"statements\":[{{\"id\":1,\"level\":1,\"confidence_score\":90,\"reason\":\"short reason\"}}]}}\n"
            )

            # Create span for AI agent call
            agent_span = category_span.span(name="agent_levelling")
            
            result = agent.run_sync(user_prompt.format(
                statements=statements,
                objective=statement_level_obj.objective,
                evaluation_criteria=statement_level_obj.evaluation_criteria,
                score_assignment_criteria=statement_level_obj.score_assignment_criteria,
                instruction=statement_level_obj.instruction,
                examples=statement_level_obj.examples,
                notes=statement_level_obj.notes
            ))
            response = result.output
            print(response)
            
            # Log agent call details
            agent_span.end(
                output=str(response),
                metadata={
                    "category": category,
                    "num_statements": len(statements)
                }
            )

            print("RAW RESPONSE:")
            for s in response.statements:
                print(f"  id={s.id} level={s.level} confidence={s.confidence_score} reason={s.reason[:50]}")

            for scored_statement in response.statements:
                try:
                    statement_obj = StatementClassification.objects.get(id=scored_statement.id)
                except StatementClassification.DoesNotExist:
                    continue
                final_statement = FinalStatementWithLevel(
                    transcription=statement_obj.transcription,
                    category=category,
                    statement=statement_obj.statement,
                    level=scored_statement.level,
                    confidence_score=scored_statement.confidence_score,
                    reason_for_level=scored_statement.reason
                )
                final_statement.save()
                print(final_statement)

            classification_statements.update(levelDone=True)
            
            # End category span
            category_span.end(output={"status": "completed", "statements_processed": len(statements)})

        # End trace
        trace.update(output={"status": "completed"})
        
        return Response(
            {"message": "done"},
            status=status.HTTP_200_OK
        )
    
@csrf_exempt
def highest_level_statements(request, transcript_id):
    categories = ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING', 'OUTCOME']
    results = []

    for category in categories:
        # Find the highest level statement in each category
        highest_level = FinalStatementWithLevel.objects.filter(transcription__id=transcript_id, category=category).aggregate(Max('level'))['level__max']

        if highest_level is not None:
            statement = FinalStatementWithLevel.objects.filter(transcription__id=transcript_id, category=category, level=highest_level).first()
            results.append({
                'statement': statement.statement,
                'level': statement.level,
                'category': statement.category,
                'reason_for_level': statement.reason_for_level,
                'confidence_score': statement.confidence_score
            })

    return JsonResponse(results, safe=False)

def highest_level_statements_docker_results(request, transcript_id):
    return JsonResponse(getDockerOutput(transcript_id), safe=False)


class FullProcessView(APIView):
    def post(self, request):
        segment_length = 6000  # Adjust as needed
        overlap = 100  # Adjust as needed
        print(type(request.data))
        serializer = TranscriptionSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            instance.segments = create_overlapping_segments(request.data['text'], segment_length, overlap)
            instance.save()
            classify_segments.delay(instance.id)
            return Response({"transcript_id": instance.id, "number_of_segments": len(instance.segments)}, status=status.HTTP_202_ACCEPTED)
        else:
            return JsonResponse(serializer.errors, safe=False, status=status.HTTP_400_BAD_REQUEST)

def getDockerOutput(transcript_id):
    categories = ['OPENING', 'QUESTIONING', 'PRESENTING', 'CLOSING', 'OUTCOME']
    category_map = {
        "OPENING": "Opening",
        "QUESTIONING": "Questioning",
        "PRESENTING": "Presenting",
        "CLOSING": "Closing",
        "OUTCOME": "Outcome",
    }
    results = []
    consolidated_score = []

    for category in categories:
        # Find the highest level statement in each category
        highest_level = \
        FinalStatementWithLevel.objects.filter(transcription__id=transcript_id, category=category).aggregate(
            Max('level'))['level__max']
        if highest_level is not None:
            statement = FinalStatementWithLevel.objects.filter(transcription__id=transcript_id, category=category,
                                                               level=highest_level).first()
            consolidated_score.append({
                "category": category_map[statement.category],
                "score": statement.level
            })

            all_statements = FinalStatementWithLevel.objects.filter(transcription__id=transcript_id, category=category).all()
            if category == 'CLOSING' or category == 'OUTCOME':
                sentences = [
                    {
                        # FIXME: change the values to actual after CTA
                        "call_to_action": ["No CTA"],
                        "call_to_action_confidence": "0",
                        "criteria": str(sentence.level),
                        "category": category_map[sentence.category],
                        "criteria_confidence_score": sentence.confidence_score,
                        "sentence": sentence.statement,
                        "speaker": "REP"
                    }
                    for sentence in all_statements
                ]
            else:
                sentences = [
                    {
                        "criteria": str(sentence.level),
                        "criteria_confidence_score": sentence.confidence_score,
                        "sentence": sentence.statement,
                        "speaker": "REP"
                    }
                    for sentence in all_statements
                ]
            transcript_chunk = " ".join([sentence['sentence'] for sentence in sentences])
            if category == 'CLOSING':
                results.append({
                    "category": "Closing & Outcome",
                    "category_confidence_score": 1,
                    "consolidated_close_score": statement.level,
                    "sentences": sentences,
                    "transcript_chunks": transcript_chunk
                })
            elif category == 'OUTCOME':
                closing_results = results[-1]
                closing_results['consolidated_outcome_score'] = statement.level
                closing_outcome_statements = []
                for closing_statement in closing_results['sentences']:
                    # for closing and outcome in pairs
                    closing_outcome_statements.append(closing_statement)
                    closing_outcome_statements.append(sentences[0])
                    sentences = sentences[1:]

                closing_results['sentences'] = closing_outcome_statements
                # print(closing_results)
                # continue
            else:
                results.append({
                    "category": category_map[statement.category],
                    "category_confidence_score": 1,
                    "sentences": sentences,
                    "transcript_chunks": transcript_chunk
                })

    responseDict = {
        "consolidate_scores": consolidated_score,
        "transcript": results,
        "status": "Success",
        "code": "200",
        "error_msg": "None",
        "merged_speakers": [
            {"extra_speakers": {}},
            {"original_speaker": "2"},
            {"deleted": False},
            {"merged": False}
        ],
        "speaker_total_time": {
            "HCP_total_time": 50.32,
            "REP_total_time": 261.49
        },
        "consolidated_call_to_action_scores": [
            {
                "category": "Prescribe",
                "score": "0"
            },
            {
                "category": "Patient Id",
                "score": "0"
            },
            {
                "category": "MSL",
                "score": "0"
            },
            {
                "category": "Advocacy",
                "score": "0"
            },
            {
                "category": "Guidelines",
                "score": "0"
            },
            {
                "category": "Next Meeting",
                "score": "0"
            },
            {
                "category": "Send Info",
                "score": "0"
            },
            {
                "category": "No CTA",
                "score": "0"
            }
        ],
    }
    return responseDict

class FullSyncProcessView(APIView):
    def post(self, request):
        segment_length = 6000  # Adjust as needed
        overlap = 100  # Adjust as needed
        print(type(request.data))
        serializer = TranscriptionSerializer(data=request.data)
        if serializer.is_valid():
            instance = serializer.save()
            instance.segments = create_overlapping_segments(request.data['text'], segment_length, overlap)
            instance.save()
            sync_classify_segments(instance.id)
            return Response(getDockerOutput(instance.id), status=status.HTTP_200_OK)
        else:
            return JsonResponse(serializer.errors, safe=False, status=status.HTTP_400_BAD_REQUEST)
