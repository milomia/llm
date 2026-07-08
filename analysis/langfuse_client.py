"""
Langfuse client initialization and utilities for tracing.
"""
from langfuse import get_client
from dotenv import load_dotenv

load_dotenv()


def get_langfuse_client():
    """
    Get or create the Langfuse client singleton.
    
    The client automatically uses environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_BASE_URL (optional, defaults to https://cloud.langfuse.com)
    
    Returns:
        Langfuse: The Langfuse client instance
    """
    return get_client()


def create_trace(name, **kwargs):
    """
    Create a new Langfuse trace.
    
    Args:
        name (str): Name of the trace
        **kwargs: Additional trace metadata (session_id, user_id, etc.)
    
    Returns:
        LangfuseTrace: The created trace object
    """
    langfuse = get_langfuse_client()
    return langfuse.trace(name=name, **kwargs)


def get_or_create_trace(trace_id, name, **kwargs):
    """
    Get an existing trace or create a new one.
    
    Args:
        trace_id (str): ID of the trace to retrieve or create
        name (str): Name of the trace
        **kwargs: Additional trace metadata
    
    Returns:
        LangfuseTrace: The trace object
    """
    langfuse = get_langfuse_client()
    return langfuse.trace(id=trace_id, name=name, **kwargs)
