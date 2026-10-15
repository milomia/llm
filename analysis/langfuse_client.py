"""
Langfuse client initialization and utilities for tracing.

Wraps the Langfuse v4 (OpenTelemetry-based) SDK behind the small trace/span API the
views and tasks use: trace.span(...), span.end(output=...), trace.end(output=...).
Tracing is best-effort: if Langfuse is misconfigured or unreachable, every call
becomes a no-op instead of failing the request.
"""
import logging

from dotenv import load_dotenv
from langfuse import LangfuseOtelSpanAttributes, get_client

load_dotenv()

logger = logging.getLogger(__name__)


def get_langfuse_client():
    """
    Get or create the Langfuse client singleton.

    The client automatically uses environment variables:
    - LANGFUSE_PUBLIC_KEY
    - LANGFUSE_SECRET_KEY
    - LANGFUSE_BASE_URL (optional, defaults to https://cloud.langfuse.com)
    """
    return get_client()


class Observation:
    """A trace or span. Methods never raise; on any Langfuse error they log and do nothing."""

    def __init__(self, observation=None, is_root=False):
        self._observation = observation
        self._is_root = is_root

    def span(self, name, metadata=None, input=None):
        if self._observation is None:
            return Observation()
        try:
            child = self._observation.start_observation(name=name, metadata=metadata, input=input)
            return Observation(child)
        except Exception as exc:
            logger.warning("Langfuse span %s failed: %s", name, exc)
            return Observation()

    def update(self, output=None, metadata=None):
        if self._observation is None:
            return
        try:
            self._observation.update(output=output, metadata=metadata)
            if self._is_root and output is not None:
                self._observation._otel_span.set_attribute(
                    LangfuseOtelSpanAttributes.TRACE_OUTPUT, str(output)
                )
        except Exception as exc:
            logger.warning("Langfuse update failed: %s", exc)

    def end(self, output=None, metadata=None):
        """Record output/metadata (if given) and close this span; closing a trace also flushes it."""
        if self._observation is None:
            return
        if output is not None or metadata is not None:
            self.update(output=output, metadata=metadata)
        try:
            self._observation.end()
            if self._is_root:
                get_langfuse_client().flush()
        except Exception as exc:
            logger.warning("Langfuse end failed: %s", exc)


def create_trace(name, session_id=None, user_id=None, metadata=None):
    """
    Create a new Langfuse trace. Call .end(output=...) on it when the work is done.

    Args:
        name (str): Name of the trace
        session_id (str): Optional session to group traces under
        user_id (str): Optional user the trace belongs to
        metadata (dict): Optional trace metadata

    Returns:
        Observation: the trace (a no-op object if Langfuse is unavailable)
    """
    try:
        root = get_langfuse_client().start_observation(name=name, metadata=metadata)
        otel_span = root._otel_span
        otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_NAME, name)
        if session_id is not None:
            otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_SESSION_ID, str(session_id))
        if user_id is not None:
            otel_span.set_attribute(LangfuseOtelSpanAttributes.TRACE_USER_ID, str(user_id))
        return Observation(root, is_root=True)
    except Exception as exc:
        logger.warning("Langfuse trace %s failed: %s", name, exc)
        return Observation()
