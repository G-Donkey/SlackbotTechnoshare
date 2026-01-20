"""
Langfuse tracing integration for LLM observability.
Provides span-based tracing for retrieval, LLM calls, quality gates, and Slack posting.
"""
import logging
import os
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager

from langfuse import Langfuse, observe

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Initialize Langfuse client
_langfuse_client: Optional[Langfuse] = None


def _get_langfuse() -> Optional[Langfuse]:
    """Get or create Langfuse client singleton."""
    global _langfuse_client
    
    if not settings.LANGFUSE_ENABLED:
        return None
    
    if _langfuse_client is None:
        try:
            # Set environment variables for Langfuse SDK
            os.environ["LANGFUSE_HOST"] = settings.LANGFUSE_HOST
            if settings.LANGFUSE_PUBLIC_KEY:
                os.environ["LANGFUSE_PUBLIC_KEY"] = settings.LANGFUSE_PUBLIC_KEY
            if settings.LANGFUSE_SECRET_KEY:
                os.environ["LANGFUSE_SECRET_KEY"] = settings.LANGFUSE_SECRET_KEY
            
            _langfuse_client = Langfuse()
            logger.info(f"Langfuse tracing enabled: {settings.LANGFUSE_HOST}")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse: {e}")
            return None
    
    return _langfuse_client


class LangfuseTracer:
    """Handles Langfuse tracing for LLM observability.
    
    Note: In Langfuse v3, tracing is primarily done via:
    - @observe decorator for automatic function tracing
    - langfuse.openai wrapper for automatic OpenAI call tracing
    - Manual trace/span creation via the Langfuse client
    
    The span() method here is a simple pass-through for compatibility
    with existing code. Real tracing happens at the tracker level.
    """
    
    def __init__(self):
        self.enabled = settings.LANGFUSE_ENABLED
        self.client = _get_langfuse()
        if self.client:
            logger.info("Langfuse tracing initialized")
        elif self.enabled:
            logger.warning("Langfuse enabled but client failed to initialize")
            self.enabled = False
        else:
            logger.info("Langfuse tracing disabled")
    
    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = "DEFAULT",
        attributes: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None
    ):
        """
        Create a traced span for an operation.
        
        In Langfuse v3, spans are created via the tracker's trace.
        This is a compatibility shim that yields context for the operation.
        """
        if not self.enabled or not self.client:
            yield None
            return
        
        # Simple pass-through - actual tracing is done at tracker level
        start_time = time.time()
        try:
            yield {"name": name, "type": span_type, "attributes": attributes, "inputs": inputs}
        finally:
            elapsed = time.time() - start_time
            logger.debug(f"Span {name} completed in {elapsed:.3f}s")
    
    def trace_llm_call(
        self,
        model: str,
        prompt: str,
        response: Any,
        tool_calls: Optional[list] = None,
        sources: Optional[list] = None,
        tokens: Optional[Dict[str, int]] = None
    ):
        """Log details of an LLM call.
        
        Note: With langfuse.openai wrapper, LLM calls are auto-traced.
        This method is for manual logging if needed.
        """
        if not self.enabled:
            return
        
        logger.debug(f"LLM call: model={model}, prompt_len={len(prompt)}")
    
    def trace_retrieval(
        self,
        url: str,
        adapter_name: str,
        coverage: str,
        snippet_count: int
    ):
        """Log details of a retrieval operation."""
        if not self.enabled:
            return
        
        logger.debug(f"Retrieval: url={url}, adapter={adapter_name}, coverage={coverage}")
    
    def trace_quality_gates(
        self,
        failures: list,
        total_gates: int
    ):
        """Log quality gate results."""
        if not self.enabled:
            return
        
        pass_rate = (total_gates - len(failures)) / total_gates if total_gates > 0 else 1.0
        logger.debug(f"Quality gates: {len(failures)}/{total_gates} failed, pass_rate={pass_rate:.2f}")
    
    def flush(self):
        """Flush any pending traces to Langfuse."""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                logger.warning(f"Failed to flush Langfuse: {e}")


def traced_operation(name: str, span_type: str = "DEFAULT"):
    """
    Decorator to automatically trace a function as a span.
    Uses Langfuse @observe decorator under the hood.
    
    Usage:
        @traced_operation("retrieval.fetch", span_type="RETRIEVER")
        def fetch_evidence(url):
            ...
    """
    def decorator(func: Callable):
        if not settings.LANGFUSE_ENABLED:
            return func
        
        # Apply Langfuse observe decorator
        return observe(name=name)(func)
    return decorator


# Global tracer instance
tracer = LangfuseTracer()
