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
docker-compose up -d   # starts PostgreSQL and Weaviate
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

## Required services

The app depends on three external services that must be running:

1. **PostgreSQL** — via Docker (`docker-compose up -d db`) or local; configured at `127.0.0.1:5432`, db `milomia`
2. **Redis** — must be running at `localhost:6379` for Celery
3. **Ollama** — must be running at `http://localhost:11434` with `llama3` pulled (`ollama pull llama3`)

Weaviate (Docker) is only needed for the `/vectorDb/` endpoint.

## Environment variables

Copy `.envold` as a reference. Required vars:
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` — for LLM call tracing (Langfuse)
- `LANGFUSE_BASE_URL` — optional, defaults to `https://cloud.langfuse.com`

WatsonX vars (`WATSONX_APIKEY`, `PROJECT_ID`, `IBM_WATSONX_URL`) are present in `.envold` but the WatsonX integration is entirely commented out.

## Architecture

### Two-stage AI pipeline

Every transcript goes through two sequential LLM stages:

**Stage 1 — Classification** (`ClassificationView`, `classify_segments` task, `sync_classify_segments`):
- Transcript is split into overlapping segments (6000 words, 100-word overlap) via `create_overlapping_segments` in `analysis/utils.py`
- Each segment is sent to a `pydantic_ai` Agent backed by local Ollama (`llama3`)
- The agent classifies each MSL/REP statement into: `OPENING`, `QUESTIONING`, `PRESENTING`, `CLOSING_OUTCOME`
- Results saved as `StatementClassification` records

**Stage 2 — Levelling** (`LevellingDataView`, `level_statements` task, `sync_level_statements`):
- Each category's classified statements are sent to another `pydantic_ai` Agent
- The agent assigns a level (1–4) and confidence score (0–100) per statement
- Results saved as `FinalStatementWithLevel` records

### Segment-aware prompt selection

`get_statements_data()` and `get_important_note_and_parser()` in `analysis/utils.py` dynamically adjust which categories are considered based on where the segment falls in the transcript:
- `OPENING` is excluded from segments past the 30% mark (when `total_parts >= 3`)
- `CLOSING_OUTCOME` is excluded from segments before the 70% mark
- The pydantic output model is swapped accordingly (`StatementParser`, `StatementParserWithoutOpening`, `StatementParserWithoutClosing`, `StatementParserWithoutOpeningAndClosing`)

### Async vs sync execution

There are two parallel implementations of the full pipeline:
- **Async** (`FullProcessView` → `classify_segments` Celery task → `level_statements` Celery task): fires and forgets, returns `202`
- **Sync** (`FullSyncProcessView` → `sync_classify_segments` → `sync_level_statements`): blocks until complete, returns the full result JSON

### Prompt configuration via database

Category definitions, examples, and level rubrics are stored in the database, not hardcoded:
- `StatementClassificationTypePrompt` — per-category classification prompts (definition, examples, invalid examples); queried at classification time
- `StatementLevelPrompt` — per-category levelling prompts (objective, evaluation criteria, scoring rubric); queried at levelling time
- `llmModel` — unused active LLM record (legacy WatsonX config)

The hardcoded constants in `analysis/aiService/constants.py` are the domain definitions used to seed or understand these DB records, not used at runtime directly.

### Key files

| File | Purpose |
|---|---|
| `analysis/views.py` | All API views; contains the main classification and levelling logic |
| `analysis/tasks.py` | Celery async versions of classify + level |
| `analysis/synctask.py` | Synchronous versions of classify + level (no Celery) |
| `analysis/utils.py` | Segment creation, prompt/agent selection logic |
| `analysis/outputParser.py` | Pydantic models for structured LLM output |
| `analysis/aiService/constants.py` | Domain knowledge: level rubrics and category definitions |
| `analysis/langfuse_client.py` | Langfuse tracing client wrapper |
| `milomia/settings.py` | Django + Celery config |
| `milomia/celery.py` | Celery app init |

### Django project layout

- Django project: `milomia/`
- Single app: `analysis/`
- All URLs mounted under the `analysis/` app; root URL config is at `milomia/urls.py`
