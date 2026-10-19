import re

from dotenv import load_dotenv
from django.views.decorators.csrf import csrf_exempt

from django.http import JsonResponse
from django.db.models import Max
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema

from analysis import api_schemas

from analysis.aiService.weaviateDb import storeData
from analysis.serializers import TranscriptionSerializer
from analysis.models import Transcription, StatementClassification, StatementLevelPrompt, FinalStatementWithLevel
from analysis.utils import create_overlapping_segments, get_statements_data, get_important_note_and_parser, \
    clear_previous_results
from analysis.langfuse_client import create_trace

from pydantic_ai import Agent
from analysis.llm import get_llm_model, make_agent
from pydantic_ai.output import NativeOutput

from .outputParser import EvaluationResult
from .synctask import sync_classify_segments
from .tasks import save_transcription, classify_segments
from .levelling import level_category
from .sentiment import analyze_sentiment, get_sentiment_results

load_dotenv()

# DRF validation errors: {"<field>": ["<message>", ...]}
VALIDATION_ERROR = OpenApiResponse(OpenApiTypes.OBJECT, description="Invalid input; maps each field to its error messages.")


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

    @extend_schema(
        summary="Classify a transcript's statements (stage 1)",
        description="Runs every segment of the transcript through the classification agent and saves "
                    "StatementClassification records. Blocks until all segments are done.",
        request=api_schemas.TranscriptIdRequest,
        responses={201: api_schemas.MessageResponse},
        tags=["pipeline"],
    )
    def post(self, request):
        transcript_id = request.data['transcript_id']
        print(transcript_id)

        try:
            transcript = Transcription.objects.get(id=transcript_id)
        except Transcription.DoesNotExist:
            return Response({"error": f"Transcription {transcript_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        clear_previous_results(transcript)

        # Create Langfuse trace for classification
        trace = create_trace(
            name="classification",
            session_id=str(transcript_id),
            metadata={"transcript_id": transcript_id}
        )

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
            statement_type_considered, different_statement_definition = get_statements_data(index + 1, total_segments, msl_segment)
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
        trace.end(output={"status": "completed", "total_segments": total_segments})
        
        return Response({"message": "action is finished"}, status=status.HTTP_201_CREATED)

class TranscriptionView(APIView):

    @extend_schema(
        summary="List pending transcripts",
        description="Transcripts whose results haven't been fetched yet (docker_feteched=False).",
        responses={200: api_schemas.PendingTranscriptsResponse},
        tags=["transcripts"],
    )
    def get(self, request):
        transcripts = Transcription.objects.filter(docker_feteched=False)
        return Response({"pending_transcript": [transcript.id for transcript in transcripts]}, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Upload a transcript",
        description="Send the transcript as a multipart `file` upload, or as `text` (JSON or form). "
                    "The text is split into overlapping segments and saved.",
        request={
            "multipart/form-data": api_schemas.TranscriptUploadRequest,
            "application/json": api_schemas.TranscriptTextRequest,
        },
        responses={201: api_schemas.TranscriptCreatedResponse, 400: VALIDATION_ERROR},
        tags=["transcripts"],
    )
    def post(self, request):
        # Desired segment length and overlap
        segment_length = 4000  # Adjusted due to example length; use 1200 for your full text
        overlap = 100

        # Accept either an uploaded file (multipart "file") or JSON/form "text"
        uploaded = request.FILES.get('file')
        if uploaded:
            try:
                text = uploaded.read().decode('utf-8')
            except UnicodeDecodeError:
                return Response({"file": ["File must be UTF-8 encoded text."]}, status=status.HTTP_400_BAD_REQUEST)
        else:
            text = request.data.get('text')
        if not text:
            return Response({"text": ["Provide a 'text' field or upload a 'file'."]}, status=status.HTTP_400_BAD_REQUEST)

        # Plain dict: request.data is an immutable QueryDict for form/multipart requests
        trans_obj = {'text': text}
        print(trans_obj)
        # Create overlapping segments
        segments = create_overlapping_segments(text, segment_length, overlap)

        serializer = TranscriptionSerializer(data=trans_obj)

        if serializer.is_valid():
            instance = serializer.save()
            instance.segments = segments
            instance.save()
            return Response({"transcript_id": instance.id, "number_of_segments": len(instance.segments)}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

def transcription_status_update(request, transcript_id):
    obj = Transcription.objects.filter(id=transcript_id).first()
    obj.docker_feteched = True
    obj.save()
    return JsonResponse({"message": "done"}, safe=False)

class VectorDataView(APIView):

    @extend_schema(exclude=True)  # not implemented
    def get(self, request):
        pass

    @extend_schema(
        summary="Store example statements in Weaviate",
        description="Adds statements to a Weaviate collection (created if missing). These are the reviewed "
                    "examples retrieved into the classification prompt.",
        request=api_schemas.VectorStoreRequest,
        responses={201: api_schemas.MessageResponse},
        tags=["examples"],
    )
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
        trace.end(output={"status": "completed"})
        
        return Response(
            {"message": "data has been stored in {collection_name}".format(collection_name=collection_name)},
            status=status.HTTP_201_CREATED
        )

class LevellingDataView(APIView):

    @extend_schema(
        summary="Level classified statements (stage 2)",
        description="Assigns a level (1-4) and confidence score to each classified statement and saves "
                    "FinalStatementWithLevel records. Run after classification.",
        request=api_schemas.TranscriptIdRequest,
        responses={200: api_schemas.MessageResponse},
        tags=["pipeline"],
    )
    def post(self, request):
        transcript_id = request.data['transcript_id']
        print(transcript_id)
        
        try:
            transcript = Transcription.objects.get(id=transcript_id)
        except Transcription.DoesNotExist:
            return Response({"error": f"Transcription {transcript_id} not found"}, status=status.HTTP_404_NOT_FOUND)

        # Create Langfuse trace for levelling
        trace = create_trace(
            name="levelling",
            session_id=str(transcript_id),
            metadata={"transcript_id": transcript_id}
        )
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

            unscored = level_category(category, transcript, statement_level_obj, parent_span=category_span)
            
            # End category span
            category_span.end(output={"status": "completed", "statements_processed": len(statements) - len(unscored),
                                      "unscored": unscored})

        # End trace
        trace.end(output={"status": "completed"})
        
        return Response(
            {"message": "done"},
            status=status.HTTP_200_OK
        )
    
class SentimentView(APIView):
    @extend_schema(
        summary="Analyse HCP sentiment (stage 3)",
        description="Labels the HCP's reaction (positive / neutral / negative / no_response) to each classified "
                    "REP statement. Only statements not yet analysed are processed, so it is safe to re-run.",
        request=api_schemas.TranscriptIdRequest,
        responses={200: api_schemas.SentimentResultResponse, 404: OpenApiResponse(description="Unknown transcript")},
        tags=["pipeline"],
    )
    def post(self, request):
        transcript_id = request.data['transcript_id']
        if not Transcription.objects.filter(id=transcript_id).exists():
            return Response({"error": "Transcript not found"}, status=status.HTTP_404_NOT_FOUND)
        analyze_sentiment(transcript_id)
        return Response(get_sentiment_results(transcript_id))


@extend_schema(
    summary="Get HCP sentiment results",
    responses={200: api_schemas.SentimentResultResponse, 404: OpenApiResponse(description="Unknown transcript")},
    tags=["results"],
)
@api_view(['GET'])
def sentiment_results(request, transcript_id):
    if not Transcription.objects.filter(id=transcript_id).exists():
        return Response({"error": "Transcript not found"}, status=status.HTTP_404_NOT_FOUND)
    return Response(get_sentiment_results(transcript_id))


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
    @extend_schema(
        summary="Upload and process a transcript (async)",
        description="Saves the transcript and queues classification then levelling on Celery. "
                    "Returns immediately; poll /api/transcription/ or fetch /api/docker-results/{id}/ later.",
        request=api_schemas.TranscriptTextRequest,
        responses={202: api_schemas.TranscriptCreatedResponse, 400: VALIDATION_ERROR},
        tags=["pipeline"],
    )
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
    @extend_schema(
        summary="Upload and process a transcript (sync)",
        description="Runs classification and levelling in the request and returns the full result. "
                    "Can take minutes for long transcripts.",
        request=api_schemas.TranscriptTextRequest,
        responses={200: api_schemas.PipelineResultResponse, 400: VALIDATION_ERROR},
        tags=["pipeline"],
    )
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
