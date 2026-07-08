# Advance ai LLM

This is a Django-based LLM application for pharmaceutical sales conversation analysis. Here's what the project does:

Core Purpose
The system analyzes conversations between pharmaceutical sales representatives (REPs) and healthcare professionals (HCPs) to classify and evaluate sales dialogue effectiveness.

Key Features
Conversation Classification:

Classifies REP statements into categories: Opening, Questioning, Presenting, Closing & Outcome
Uses AI (Azure OpenAI GPT-4) to analyze conversation segments
Evaluates statement quality and assigns performance levels
Technical Architecture:

Backend: Django 5.0 with Django REST Framework
Database: PostgreSQL for storing transcriptions and classifications
Vector Database: Weaviate for semantic search and data storage
Task Queue: Celery with Redis for async processing
AI Integration: Azure OpenAI, LangChain for LLM orchestration
Deployment: Docker Compose with multi-service setup
Main Models:

Transcription: Stores conversation text and segments
StatementClassification: Categorized statements from conversations
FinalStatementWithLevel: Evaluated statements with performance scores
Prompt templates for classification and evaluation criteria
API Endpoints:

Upload and process conversation transcriptions
Classify statements into categories
Evaluate statement performance levels
Retrieve highest-scoring statements by category
Store data in vector database
The system appears designed for pharmaceutical companies to analyze and improve their sales representatives' conversation effectiveness with healthcare professionals.

Feedback submitted



how do you call ClassificationView

Based on the URL configuration, here's how to call the ClassificationView:

HTTP Endpoint
POST /api/classification/
Request Body
The endpoint expects a JSON payload with:

json
{
    "transcript_id": 123
}
Example Usage
bash
curl -X POST http://localhost:8000/api/classification/ \
  -H "Content-Type: application/json" \
  -d '{"transcript_id": 123}'
What It Does
Retrieves the Transcription object by ID
Processes each segment of the transcription
Classifies REP statements into categories (Opening, Questioning, Presenting, Closing & Outcome)
Uses Azure OpenAI GPT-4 for classification
Creates StatementClassification objects for each classified statement
Prerequisites
The transcription must exist in the database
The transcription should have segments already created
Azure OpenAI credentials must be configured
The view processes the transcription asynchronously and returns a success message when classification is complete.

Based on the URL configuration, here's how to call the ClassificationView:

HTTP Endpoint
POST /api/classification/
Request Body
The endpoint expects a JSON payload with:

json
{
    "transcript_id": 123
}
Example Usage
bash
curl -X POST http://localhost:8000/api/classification/ \
  -H "Content-Type: application/json" \
  -d '{"transcript_id": 123}'
What It Does
Retrieves the Transcription object by ID
Processes each segment of the transcription
Classifies REP statements into categories (Opening, Questioning, Presenting, Closing & Outcome)
Uses Azure OpenAI GPT-4 for classification
Creates StatementClassification objects for each classified statement
Prerequisites
The transcription must exist in the database
The transcription should have segments already created
Azure OpenAI credentials must be configured
The view processes the transcription asynchronously and returns a success message when classification is complete.

Feedback submitted



Upload and process conversation transcriptions

Model provider unreachable
Feedback submitted



what api endpoint API Endpoints:

Upload and process conversation transcriptions

Based on the URL configuration, there are multiple endpoints for uploading and processing conversation transcriptions:

1. Upload Transcription Only
POST /api/transcription/
Request Body:

json
{
    "text": "Full conversation transcript text here..."
}
Response:

json
{
    "transcript_id": 123,
    "number_of_segments": 5
}
2. Upload & Process Asynchronously (Recommended)
POST /api/process/
Request Body:

json
{
    "text": "Full conversation transcript text here..."
}
Response:

json
{
    "transcript_id": 123,
    "number_of_segments": 5
}
Uses Celery for async background processing
Returns immediately with transcript ID
3. Upload & Process Synchronously
POST /api/sync-process/
Request Body:

json
{
    "text": "Full conversation transcript text here..."
}
Response:

Full processing results including classifications and levels
Waits for complete processing before returning
Example Usage
bash
# Upload and process asynchronously
curl -X POST http://localhost:8000/api/process/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Your full conversation transcript here..."}'
The /api/process/ endpoint is typically the best choice as it handles the full workflow (segmentation, classification, and leveling) asynchronously without blocking the request.

Feedback submitted



what does process doThe /api/process/ endpoint is designed to handle the entire workflow of processing a conversation transcription asynchronously. Here's what it does step-by-step:
1. Receives the Full Transcript
The endpoint accepts a JSON payload containing the full conversation transcript text.
2. Creates a Transcription Object
A new Transcription object is created in the database to store the original transcript and its metadata.
3. Segments the Transcript
The full transcript is segmented into smaller parts (e.g., sentences or speaker turns) for easier analysis.
4. Classifies Each Segment
Each segment is processed using Azure OpenAI GPT-4 to classify REP statements into predefined categories (Opening, Questioning, Presenting, Closing & Outcome).
   5. Evaluates Statement Quality
   6. Each classified statement is further evaluated to assign a performance level (e.g., Excellent, Good, Needs Improvement).
7. Stores Results
8. The classified statements and their performance levels are stored in the database, linked to the original Transcription.
9. Returns Response
10. The endpoint returns a JSON response containing the transcript ID and the number of segments created, allowing the client to track the processing status.
The actual processing is handled asynchronously using Celery, so the client receives an immediate response while the heavy lifting of classification and evaluation happens in the background.
11. This design allows for efficient handling of potentially long-running tasks without blocking the client's request, making it suitable for processing large transcripts.
12. Overall, the /api/process/ endpoint streamlines the workflow of analyzing pharmaceutical sales conversations, providing valuable insights into REP performance and conversation effectiveness.
    13. Feedback submitted

/api/classification/ endpoint is designed to classify the segments of a conversation transcription into specific categories. Here's what it does step-by-step:
1. Receives Transcript ID
2. The endpoint accepts a JSON payload containing the ID of an existing Transcription object that has already been created and segmented
3. Retrieves the Transcription Object
4. The system retrieves the Transcription object from the database using the provided ID
5. Processes Each Segment
6. Each segment of the transcription is processed individually to analyze its content
7. Classifies REP Statements
8. The system uses Azure OpenAI GPT-4 to classify each segment into one of the
9. predefined categories: Opening, Questioning, Presenting, Closing & Outcome
10. Creates StatementClassification Objects
11. For each classified segment, a new StatementClassification object is created in the database to store the classification results
12. Returns Response
13. The endpoint returns a JSON response indicating that the classification process has been initiated successfullyvec
14. The actual classification is handled asynchronously, allowing the client to receive an immediate response while the classification process runs in the background
15. This design allows for efficient handling of potentially long-running classification tasks without blocking the client's request, making it suitable for processing large transcripts
16. Overall, the/api/classification/ endpoint provides a way to categorize the segments of a conversation transcription, which can then be used for further analysis and evaluation of REP performance in pharmaceutical sales conversations.
ç
transcription curl command example:bash
curl -X POST http://localhost:8000/api/process/ \
  -H "Content-Type: application/json" \
  -d '{"text": "Your full conversation transcript here..."}'

curl -X POST http://localhost:8000/api/transcription/ \
    -H "Content-Type: application/json" \
    -d '{"text": "Your full conversation transcript here..."}'



/api/transcription/ endpoint is designed to handle the uploading of conversation transcriptions. Here's what it does step-by-step:
1. Receives Transcript Text
2. The endpoint accepts a JSON payload containing the full conversation transcript text
3. Creates a Transcription Object
4. A new Transcription object is created in the database to store the original transcript and its metadata
5. Returns Response
6. The endpoint returns a JSON response containing the ID of the created Transcription object and the number of segments created (if segmentation is performed at this stage)
7. This endpoint is typically used for uploading the raw transcript text, which can then be processed further using the /api/process/ or/api/classification/ endpoints
   8. Overall, the /api/transcription/ endpoint provides a way to upload conversation transcriptions into the system, allowing for subsequent processing and analysis of REP performance in pharmaceutical sales conversations.
7. number of segments created (if segmentation is performed at this stage)

/api/vectorDatabase/ endpoint is designed to handle the management of vector databases for storing and retrieving vector representations of conversation segments. Here's what it does step-by-step:
1. Receives Vector Data
The endpoint accepts a JSON payload containing vector data, which may include the vector representations of conversation segments
2. Stores Vector Data
3. The system stores the received vector data in a vector database, which is optimized for efficient storage and retrieval of high-dimensional vectors
4. Retrieves Vector Data
5. The endpoint may also support retrieving vector data based on specific criteria, such as segment ID or similarity search
   6. Returns Response          
   7. The endpoint returns a JSON response indicating the success of the storage or retrieval operation, along with any relevant data (e.g., stored vector IDs or retrieved vectors)
   8. This endpoint is crucial for enabling advanced functionalities such as similarity search, clustering, and other vector-based analyses of conversation segments, which can provide deeper insights into REP performance in pharmaceutical sales conversations.
   9. Overall, the /api/vectorDatabase/ endpoint provides a way to manage vector representations of conversation segments, facilitating advanced analysis and insights into REP performance in pharmaceutical sales conversations.
   10. Feedback submitted

/api/rating/ endpoint is designed to handle the evaluation and rating of classified conversation segments. Here's what it does step-by-step:
1. Receives Rating Data
2. The endpoint accepts a JSON payload containing the ID of a classified segment and the corresponding rating data, which may include performance levels (e.g., Excellent, Good, Needs Improvement) and any additional feedback
3. Stores Rating Data
4. The system stores the received rating data in the database, linking it to the corresponding StatementClassification object
5. Returns Response
6. The endpoint returns a JSON response indicating the success of the rating operation, along with any relevant data (e.g., updated classification results or aggregated performance metrics)
7. This endpoint is essential for enabling the evaluation of classified conversation segments, allowing for the assessment of REP performance based on the classifications and the assigned performance levels
   8. Overall, the /api/rating/ endpoint provides a way to evaluate and rate classified conversation segments, facilitating the assessment of REP performance in pharmaceutical sales conversations and providing valuable feedback for improvement.        
      9. Feedback submitted

/api/results/ endpoint is designed to handle the retrieval of processed results for a given transcription. Here's what it does step-by-step:
1. Receives Transcription ID
The endpoint accepts a JSON payload containing the ID of an existing Transcription object for which the processed results are to be retrieved
2. Retrieves Processed Results
The system retrieves the processed results from the database, which may include classified segments, performance ratings, and any additional insights derived from the analysis of the conversation transcription
   3. Returns Response
   The endpoint returns a JSON response containing the retrieved results, which may include the classified segments, their              
   4. performance ratings, and any relevant insights or metrics related to REP performance in pharmaceutical sales conversations
   5. This endpoint is crucial for providing access to the processed results of conversation transcriptions, allowing clients to view and analyze the outcomes of the classification and evaluation processes
   6. Overall, the /api/results/ endpoint provides a way to retrieve the processed results for a given transcription, facilitating the analysis of REP performance in pharmaceutical sales conversations and enabling clients to gain valuable insights from the processed data.
      7. Feedback submitted     
8. Overall, the API endpoints are designed to facilitate the workflow of uploading, processing, classifying, evaluating, and retrieving results




The /api/process/ endpoint performs the complete transcription analysis workflow:

Workflow Steps
1. Receive Transcription

Accepts conversation text via POST request
Validates and saves to Transcription model

2. Segment the Text

Splits text into overlapping segments (6000 characters with 100 character overlap)
Ensures context is preserved across segment boundaries

3. Async Classification (Celery Task)

Triggers classify_segments.delay(transcription_id)
Processes each segment through Azure OpenAI GPT-4
Classifies REP statements into categories:
OPENING
QUESTIONING
PRESENTING
CLOSING_OUTCOME
Saves classifications to StatementClassification model
4. Async Leveling (Celery Task)

Automatically triggers level_statements.delay(transcription_id) after classification
Evaluates each classified statement against performance criteria
Assigns proficiency levels (scores) to statements
Saves final results to FinalStatementWithLevel model with:
Level score
Confidence score
Reason for level assignment
Response
Returns immediately with:

json
{
    "transcript_id": 123,
    "number_of_segments": 5
}

Celery tasks run in the background, allowing for efficient processing of potentially long-running classification and leveling operations without blocking the client's request. This design enables the system to handle large transcripts while providing timely feedback to the client.
to run the celery worker, use the following command in the terminal:bash
celery -A your_project_name worker --loglevel=info

Make sure to replace your_project_name with the actual name of your Django project. This command will start the Celery worker, which will listen for tasks and execute them as they are triggered by the API endpoints.

# Start the worker

python -m celery -A advanceAi worker --loglevel=info
    
redis-server is required to run the celery worker, you can start the redis server using the following command in the terminal:bash
redis-server    

brew services start redis


transcribe:
curl -X POST http://localhost:8000/api/transcription/ \
  -H "Content-Type: application/json" \
  -d @request.json

classify:
curl -X POST http://localhost:8000/api/classification/ \
  -H "Content-Type: application/json" \
  -d '{"transcript_id": 24}'

rating:
curl -X POST http://localhost:8000/api/rating/ \
  -H "Content-Type: application/json" \
  -d '{"transcript_id": 24}'

vectordb:
curl -X POST http://localhost:8000/api/vectorDb/ \
  -H "Content-Type: application/json" \
  -d '{
    "collection_name": "pharma_calls",
    "statements": "MSLHello Dr Lewis, can you see me, ok? DrHello, yes I can. MSLCan I just check who else we have in the meeting please? DRYes, of course, does everyone want to introduce themselves? JDrHi, I am Julie one of the junior doctors working alongside Dr Lewis at the moment. MSLGreat to meet you Julie, can I ask what stage you are at in your training? JDrSure, I am an F2 so still pretty early on. MSLWell it is great to meet you, thanks for joining the meeting. NSHi, I am Sally the Lung Specialist Nurse. MSLBrilliant, lovely to meet you Sally."
  }'

curl "http://172.21.0.2:8000/api/vector-data/?collection_name=pharma_calls&q=progression+free+survival"


from analysis.models import StatementClassificationTypePrompt

# Clear existing records
StatementClassificationTypePrompt.objects.all().delete()

# OPENING
StatementClassificationTypePrompt.objects.create(
    category='OPENING',
    definition="Statements made by the REP at the start of the interaction to establish rapport, introduce themselves and their company, set the agenda, confirm the purpose of the meeting, and build a positive relationship with the HCP before presenting clinical data.",
    examples="'Hello Dr Lewis, can you see me ok?', 'Let me introduce myself, I am Laurence from Pharmapro and I am here in response to a medical request you made through my colleague Louise.', 'My aim is that by the end of the presentation I will have provided you with the information you need to support your treatment decisions for your patients. I am keen to answer any questions you may have so do please ask questions as we go through the data.', 'Great to meet you Julie, can I ask what stage you are at in your training?', 'Brilliant, lovely to meet you Sally. Thanks for introducing yourselves, are we expecting anyone else?'",
    invalid_examples="'The phase 3 study showed progression free survival of 6.3 months' — this is a presenting statement not an opening. 'Can I ask what discussions you have had to date with the other consultants?' — this is a questioning statement not an opening. 'I will send out the webinar information' — this is a closing statement not an opening.",
    active=True
)

# QUESTIONING
StatementClassificationTypePrompt.objects.create(
    category='QUESTIONING',
    definition="Statements made by the REP to gather information, assess the HCP's current knowledge, understand clinical needs, explore treatment experiences, or engage the HCP in dialogue. Includes open and closed questions directed at HCPs to uncover needs and tailor the interaction.",
    examples="'Can I ask what discussions you have had to date with the other consultants about it?', 'In terms of the testing element, what information are you looking for specifically?', 'Can I ask what you remember from the presentations you observed?', 'What presentation stood out for you?', 'When you have introduced a new diagnostic test previously, what process did you follow?', 'Is there anything particular any of you would like me to focus on?', 'What additional information or support do you need from me?'",
    invalid_examples="'The results are as follows: Objective response rate 45% vs 21%' — this is a presenting statement not a question. 'Hello Dr Lewis, can you see me?' — this is an opening statement not a question. 'I will send out the webinar information' — this is a closing statement not a question.",
    active=True
)

# PRESENTING
StatementClassificationTypePrompt.objects.create(
    category='PRESENTING',
    definition="Statements made by the REP to deliver clinical data, study results, product information, dosing details, safety profiles, or scientific evidence to the HCP. The REP is actively sharing information to educate and support the HCP's treatment decisions.",
    examples="'The phase 3 study was a randomized, double-blind, placebo-controlled, multinational, and multicenter study to evaluate the efficacy of Avant in combination with Docetaxel as second line therapy in patients with advanced or locally advanced NSCLC.', 'The results are as follows: Objective response rate 45% vs 21%, progression free survival 6.3 months vs 2.1 months and overall survival of 12.1 months vs 9.6 months.', 'Antibody drug conjugates tend to be well tolerated because they deliver the cytotoxic payload into the tumour cell meaning that very little goes into the healthy tissue.', 'The dose is weight dependent and is an infusion, the treatment schedule is Avant plus Docetaxel every 3 weeks.', 'The current data published in the New England Journal of Medicine by Professor Sykes in 2018 suggests up to 65% of advanced or locally advanced non-small cell tumours may have some expression of ELC.'",
    invalid_examples="'What stands out for you in that data?' — this is a questioning statement not a presenting statement. 'Hello Dr Lewis, can you see me?' — this is an opening statement not a presenting statement. 'I will send out the webinar information' — this is a closing statement not a presenting statement.",
    active=True
)

# CLOSING_OUTCOME
StatementClassificationTypePrompt.objects.create(
    category='CLOSING_OUTCOME',
    definition="Statements made by the REP at the end of the interaction to summarise next steps, confirm commitments, arrange follow-up actions, and bring the meeting to a productive conclusion. Paired with HCP responses that indicate level of commitment, agreement, or planned action.",
    examples="'I will send out the webinar information and get Dr Lewis set up on the clinical paper portal. I know you have plans to speak to your pathologist and the wider team, please do let me know if you need any support with that.', 'Would you be interested in signing up to our Clinical Paper Portal which would give you access to all the clinical studies for Avant?', 'Would it be ok to reach out to you after the webinar to discuss in more depth?', 'Great, so in terms of next steps, how do you plan to take this forward as a team?'",
    invalid_examples="'The phase 3 study showed progression free survival of 6.3 months' — this is a presenting statement not a closing statement. 'Hello Dr Lewis, can you see me?' — this is an opening statement not a closing statement. 'Can I ask what discussions you have had with the other consultants?' — this is a questioning statement not a closing statement.",
    active=True
)

# Verify
for obj in StatementClassificationTypePrompt.objects.all():
    print(obj.id, obj.category, obj.active)
    print(repr(obj.definition[:80]))
    print("---")




