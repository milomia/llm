# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the server
```bash
source .venv/bin/activate
python manage.py runserver
```

### Database migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Celery worker (required for async pipeline)
```bash
celery -A milomia worker --loglevel=info
```

### Infrastructure (Docker)
```bash
docker-compose up -d   # starts PostgreSQL, Weaviate and t2v-transformers
docker-compose down
```

### Django shell
```bash
python manage.py shell
```

### Tests
```bash
python manage.py test analysis
```
Tests live in `analysis/tests.py`. Use the Django runner: `pytest.ini` points at a non-existent `core.settings`.

### API docs
With the server running, the OpenAPI schema is at `/api/schema/`, Swagger UI at `/api/docs/`, ReDoc at `/api/redoc/` (drf-spectacular; per-view schemas in `analysis/api_schemas.py`).

## Required services

1. **PostgreSQL** — via Docker (`docker-compose up -d db`) or local; configured at `127.0.0.1:5432`, db `milomia`
2. **Redis** — must be running at `localhost:6379` for Celery
3. **An LLM provider** — either:
   - **Ollama** (default) at `http://localhost:11434` with the model pulled (`ollama pull llama3`), or
   - **AWS Bedrock** (`LLM_PROVIDER=bedrock`), using the standard AWS credential chain
4. **Weaviate** (Docker, `localhost:8999` HTTP / `50051` gRPC) — used by `/vectorDb/` and to inject similar reviewed examples into the classification prompt. Lookups are wrapped in try/except, so classification still runs without it, just without those examples.

## Environment variables

`env.sample` and `.envold` are references. Relevant vars:

- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — LLM call tracing (Langfuse); `LANGFUSE_BASE_URL` defaults to `https://cloud.langfuse.com`
- `LLM_PROVIDER` — `ollama` (default) or `bedrock`
- `OLLAMA_MODEL` (default `llama3`), `OLLAMA_BASE_URL` (default `http://localhost:11434/v1`)
- `BEDROCK_MODEL_ID` (default `us.anthropic.claude-haiku-4-5-20251001-v1:0`), `AWS_REGION` (default `us-east-1`)
- `LLM_SEED` (default `42`, Ollama only — Bedrock has no seed), `LLM_RETRIES` (default `3`, output-validation retries)

WatsonX vars (`WATSONX_APIKEY`, `PROJECT_ID`, `IBM_WATSONX_URL`) in `.envold` and the Azure OpenAI vars in `env.sample` are unused.

## Architecture

### Three-stage AI pipeline

Every transcript goes through three sequential LLM stages. All agents are built with `make_agent()` in `analysis/llm.py`: provider from `get_llm_model()`, temperature 0, fixed seed (Ollama), and `NativeOutput` structured output with validation retries.

**Stage 1 — Classification** (`ClassificationView`, `classify_segments` task, `sync_classify_segments`):
- `clear_previous_results()` (`analysis/utils.py`) first deletes the transcript's earlier results, so re-running replaces rather than duplicates
- Transcript is split into overlapping segments (6000 words, 100-word overlap) via `create_overlapping_segments`
- For each active category, `get_similar_examples()` pulls the nearest reviewed `<CATEGORY>_CORRECT_EXAMPLE` / `<CATEGORY>_INCORRECT_EXAMPLE` entries from Weaviate and adds them to the prompt
- The agent classifies each MSL/REP statement into: `OPENING`, `QUESTIONING`, `PRESENTING`, `CLOSING_OUTCOME`
- Results saved as `StatementClassification` records

**Stage 2 — Levelling** (`LevellingDataView`, `level_statements` task, `sync_level_statements`; shared logic in `level_category()` in `analysis/levelling.py`):
- Each category's unlevelled statements (`levelDone=False`) are sent to the agent with that category's `StatementLevelPrompt`
- The agent assigns a level (1–4) and confidence score (0–100), both required and bounded
- Statements the model skips are re-asked; only scored rows are marked `levelDone`
- Results saved as `FinalStatementWithLevel` records

**Stage 3 — HCP sentiment** (`SentimentView`, `analyze_sentiment_task`, `analyze_sentiment()` in `analysis/sentiment.py`):
- For each REP statement with `sentimentDone=False`, labels the HCP's immediate reaction: `positive`, `neutral`, `negative`, `no_response`, with a confidence and one-line reason
- Stored on `StatementClassification` (`hcp_sentiment`, `hcp_sentiment_confidence`, `hcp_sentiment_reason`); skipped statements are re-asked
- Runs automatically after levelling. In the sync pipeline a sentiment failure is caught and does not fail the run; re-run it via `/sentiment/`

### Segment-aware prompt selection

`get_statements_data()` and `get_important_note_and_parser()` in `analysis/utils.py` dynamically adjust which categories are considered based on where the segment falls in the transcript:
- `OPENING` is excluded from segments past the 30% mark (when `total_parts >= 3`)
- `CLOSING_OUTCOME` is excluded from segments before the 70% mark
- The pydantic output model is swapped accordingly (`StatementParser`, `StatementParserWithoutOpening`, `StatementParserWithoutClosing`, `StatementParserWithoutOpeningAndClosing`)

### Async vs sync execution

There are two parallel implementations of the full pipeline:
- **Async** (`FullProcessView` at `/process/` → `classify_segments` → `level_statements` → `analyze_sentiment_task`, all Celery): fires and forgets, returns `202`
- **Sync** (`FullSyncProcessView` at `/sync-process/` → `sync_classify_segments` → `sync_level_statements`, which also runs sentiment): blocks until complete, returns the full result JSON

### Endpoints (`analysis/urls.py`)

| Path | Purpose |
|---|---|
| `transcription/`, `transcription/<id>/` | Upload/list transcripts, status update |
| `classification/` | Stage 1 only |
| `rating/` | Stage 2 only |
| `sentiment/`, `sentiment/<id>/` | Stage 3 run / results |
| `process/`, `sync-process/` | Full pipeline (async / sync) |
| `results/<id>/`, `docker-results/<id>/` | Highest-level statements per category |
| `vectorDb/` | Read/store reviewed examples in Weaviate |

### Prompt configuration via database

Category definitions, examples, and level rubrics are stored in the database, not hardcoded:
- `StatementClassificationTypePrompt` — per-category classification prompts (definition, examples, invalid examples); queried at classification time
- `StatementLevelPrompt` — per-category levelling prompts (objective, evaluation criteria, scoring rubric); queried at levelling time
- `llmModel` — unused active LLM record (legacy WatsonX config)

The hardcoded constants in `analysis/aiService/constants.py` are the domain definitions used to seed or understand these DB records, not used at runtime directly. The sentiment prompt is the exception: it is hardcoded in `analysis/sentiment.py`.

### Key files

| File | Purpose |
|---|---|
| `analysis/views.py` | All API views |
| `analysis/tasks.py` | Celery async versions of classify, level, sentiment |
| `analysis/synctask.py` | Synchronous versions (no Celery) |
| `analysis/llm.py` | LLM provider selection and `make_agent()` |
| `analysis/levelling.py` | Shared levelling logic |
| `analysis/sentiment.py` | Stage 3 HCP sentiment |
| `analysis/utils.py` | Segment creation, prompt/parser selection, Weaviate example lookup, result clearing |
| `analysis/outputParser.py` | Pydantic models for structured LLM output |
| `analysis/api_schemas.py` | OpenAPI schema definitions |
| `analysis/aiService/weaviateDb.py` | Weaviate client, storage and nearest-neighbour search |
| `analysis/aiService/constants.py` | Domain knowledge: level rubrics and category definitions |
| `analysis/langfuse_client.py` | Langfuse tracing client wrapper |
| `milomia/settings.py` | Django, Celery and drf-spectacular config |
| `milomia/celery.py` | Celery app init |

### Django project layout

- Django project: `milomia/`
- Single app: `analysis/`
- App URLs in `analysis/urls.py`; root URL config (including the `/api/` docs routes) is at `milomia/urls.py`
