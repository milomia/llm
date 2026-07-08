# Langfuse Integration Guide

This application now includes Langfuse tracing for monitoring and debugging AI operations.

## Setup

### 1. Install Dependencies

The Langfuse Python SDK is already included in `requirements.txt`:
```
langfuse==2.53.1
```

### 2. Configure Environment Variables

Add the following to your `.env` file:

```bash
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

Get your API keys from [Langfuse Cloud](https://cloud.langfuse.com) or your self-hosted instance under Settings > API Keys.

### 3. Available Regions

- **EU (default)**: `https://cloud.langfuse.com`
- **US**: `https://us.cloud.langfuse.com`
- **Japan**: `https://jp.cloud.langfuse.com`
- **HIPAA**: `https://hipaa.cloud.langfuse.com`

## What is Traced

### API Views

- **ClassificationView** (`/classification/`)
  - Trace: `classification`
  - Spans: Each segment processing, AI agent calls
  - Metadata: transcript_id, segment indices, statement types

- **VectorDataView** (`/vectorDb/`)
  - Trace: `vector_db_store`
  - Spans: Storage operations
  - Metadata: collection_name, number of statements

- **LevellingDataView** (`/rating/`)
  - Trace: `levelling`
  - Spans: Each category processing, AI agent calls
  - Metadata: transcript_id, category, statement counts

### Celery Tasks

- **classify_segments**
  - Trace: `classification_celery`
  - Spans: Segment processing, AI agent calls
  - Metadata: transcript_id, task name

- **level_statements**
  - Trace: `levelling_celery`
  - Spans: Category processing, AI agent calls
  - Metadata: transcript_id, task name

### AI Agent Calls

All pydantic_ai agent calls are traced with:
- Input prompts
- Output responses
- Metadata (statement types, segment lengths, categories)

## Viewing Traces1. Go to your Langfuse dashboard
2. Navigate to the "Traces" section
3. Filter by trace name or session_id (transcript_id)
4. View detailed spans and timing information

## Best Practices

- **Session IDs**: All traces use `transcript_id` as session_id for easy correlation
- **Metadata**: Relevant context is attached to each trace (transcript_id, categories, etc.)
- **Span Naming**: Spans follow a hierarchical naming convention (e.g., `segment_1`, `agent_classification`)
- **Error Handling**: Failed operations will be visible in Langfuse with error details

## Client Usage

The Langfuse client is initialized in `analysis/langfuse_client.py`:

```python
from analysis.langfuse_client import create_trace

# Create a trace
trace = create_trace(
    name="my_operation",
    session_id="session_123",
    metadata={"key": "value"}
)

# Create a span
span = trace.span(name="sub_operation")

# End span with output
span.end(output={"status": "success"})

# Update trace
trace.update(output={"status": "completed"})
```

## Troubleshooting

### Authentication Failed
- Verify your LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY are correct
- Check that LANGFUSE_BASE_URL matches your region

### No Traces Appearing
- Ensure environment variables are loaded before Django starts
- Check that the Langfuse client is being called in your code paths
- Verify network connectivity to Langfuse servers

### Missing Spans
- Ensure spans are properly ended with `.end()`
- Check for exceptions that might prevent span completion
