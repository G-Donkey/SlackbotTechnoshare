"""
MLflow tracing integration for LLM observability.
Provides span-based tracing for retrieval, LLM calls, quality gates, and Slack posting.
"""
import logging
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextlib import contextmanager

import mlflow

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MLflowTracer:
    """Handles MLflow tracing for LLM observability."""
    
    def __init__(self):
        self.enabled = settings.MLFLOW_ENABLE_TRACING
        if self.enabled:
            try:
                mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
                logger.info("MLflow tracing enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize MLflow tracing: {e}")
                self.enabled = False
        else:
            logger.info("MLflow tracing disabled")
    
    @contextmanager
    def span(
        self,
        name: str,
        span_type: str = "UNKNOWN",
        attributes: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None
    ):
        """
        Create a traced span for an operation.
        
        Args:
            name: Name of the span (e.g., "analysis.run", "retrieval.fetch")
            span_type: Type of span (e.g., "LLM", "RETRIEVER", "CHAIN", "TOOL")
            attributes: Additional metadata for the span
            inputs: Input data to the operation
        """
        if not self.enabled:
            yield None
            return
        
        try:
            with mlflow.start_span(name=name, span_type=span_type) as span:
                if attributes:
                    span.set_attributes(attributes)
                if inputs:
                    span.set_inputs(inputs)
                
                start_time = time.time()
                yield span
                elapsed = time.time() - start_time
                span.set_attribute("latency_ms", int(elapsed * 1000))
        except Exception as e:
            logger.warning(f"Tracing span failed for {name}: {e}")
            # Don't yield None on error, just let the exception propagate after logging
            raise
    
    def trace_llm_call(
        self,
        model: str,
        prompt: str,
        response: Any,
        tool_calls: Optional[list] = None,
        sources: Optional[list] = None,
        tokens: Optional[Dict[str, int]] = None
    ):
        """Log details of an LLM call within the current span."""
        if not self.enabled:
            return
        
        try:
            attributes = {
                "model": model,
                "prompt_length": len(prompt),
            }
            
            if tool_calls:
                attributes["tool_calls"] = ",".join(tool_calls)
                attributes["tool_call_count"] = len(tool_calls)
            
            if sources:
                attributes["sources"] = ",".join(sources)
                attributes["source_count"] = len(sources)
            
            if tokens:
                attributes.update(tokens)
            
            # Get current active span and set attributes
            try:
                current_span = mlflow.get_current_active_span()
                if current_span:
                    current_span.set_attributes(attributes)
            except AttributeError:
                # MLflow version may not have this method, skip silently
                pass
            
        except Exception as e:
            logger.warning(f"Failed to trace LLM call: {e}")
    
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
        
        try:
            attributes = {
                "url": url,
                "adapter": adapter_name,
                "coverage": coverage,
                "snippet_count": snippet_count,
            }
            # Get current active span and set attributes
            try:
                current_span = mlflow.get_current_active_span()
                if current_span:
                    current_span.set_attributes(attributes)
            except AttributeError:
                # MLflow version may not have this method, skip silently
                pass
        except Exception as e:
            logger.warning(f"Failed to trace retrieval: {e}")
    
    def trace_quality_gates(
        self,
        failures: list,
        total_gates: int
    ):
        """Log quality gate results."""
        if not self.enabled:
            return
        
        try:
            attributes = {
                "gate_failures": len(failures),
                "gate_total": total_gates,
                "gate_pass_rate": (total_gates - len(failures)) / total_gates if total_gates > 0 else 1.0,
            }
            if failures:
                attributes["failed_gates"] = ",".join(failures)
            
            # Get current active span and set attributes
            try:
                current_span = mlflow.get_current_active_span()
                if current_span:
                    current_span.set_attributes(attributes)
            except AttributeError:
                # MLflow version may not have this method, skip silently
                pass
        except Exception as e:
            logger.warning(f"Failed to trace quality gates: {e}")


def traced_operation(name: str, span_type: str = "CHAIN"):
    """
    Decorator to automatically trace a function as a span.
    
    Usage:
        @traced_operation("retrieval.fetch", span_type="RETRIEVER")
        def fetch_evidence(url):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with tracer.span(name=name, span_type=span_type):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Global tracer instance
tracer = MLflowTracer()
