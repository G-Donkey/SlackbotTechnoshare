"""
Langfuse tracking integration for TechnoShare Commentator.
Provides job-level tracking with nested spans for different stages.
"""
import logging
import json
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from pathlib import Path

from langfuse import Langfuse

from ..config import get_settings
from .tracing import _get_langfuse

logger = logging.getLogger(__name__)
settings = get_settings()


class LangfuseTracker:
    """Handles Langfuse tracking for the pipeline."""
    
    def __init__(self):
        self.enabled = settings.LANGFUSE_ENABLED
        self.client = _get_langfuse()
        self._current_trace = None
        
        if self.client:
            logger.info(f"Langfuse tracking enabled: {settings.LANGFUSE_HOST}")
        elif self.enabled:
            logger.warning("Langfuse enabled but client failed to initialize")
            self.enabled = False
        else:
            logger.info("Langfuse tracking disabled")
    
    def _sanitize_tags(self, tags: Dict[str, Any]) -> Dict[str, str]:
        """Ensure all tag values are strings."""
        return {k: str(v) for k, v in tags.items() if v is not None}
    
    @contextmanager
    def start_job_run(
        self,
        job_id: str,
        channel_id: str,
        message_ts: str,
        target_url: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """
        Start a new Langfuse trace for a job.
        Yields the trace_id for nested spans.
        """
        if not self.enabled or not self.client:
            yield None
            return
        
        metadata = {
            "job_id": job_id,
            "channel_id": channel_id,
            "message_ts": message_ts,
            "component": "pipeline",
        }
        if target_url:
            metadata["target_url"] = target_url
        if tags:
            metadata.update(self._sanitize_tags(tags))
        
        try:
            # In Langfuse v3, we use spans - create a root span for this job
            # The trace is automatically created when we create the first span
            span = self.client.start_span(
                name=f"job_{job_id}",
                metadata=metadata,
            )
            self._current_trace = span
            trace_id = span.id if span else None
            
            try:
                yield trace_id
                # Update span with success status
                if span:
                    span.end()
            except Exception as e:
                logger.exception("Job run failed")
                if span:
                    span.end()
                raise
            finally:
                self._current_trace = None
                # Flush to ensure trace is sent
                if self.client:
                    self.client.flush()
        except Exception as e:
            logger.warning(f"Failed to start job trace: {e}")
            yield None
    
    @contextmanager
    def start_nested_run(
        self,
        run_name: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """Start a nested span for a specific stage or component."""
        if not self.enabled or not self.client:
            yield None
            return
        
        sanitized_tags = self._sanitize_tags(tags) if tags else {}
        
        try:
            # Create a nested span under the current trace
            span = self.client.start_span(
                name=run_name,
                metadata=sanitized_tags,
            )
            start_time = time.time()
            
            try:
                yield span.id if span else None
                elapsed = time.time() - start_time
                if span:
                    # Update metadata before ending (end() doesn't take parameters in v3)
                    span.update(metadata={**sanitized_tags, "latency_seconds": elapsed})
                    span.end()
            except Exception as e:
                elapsed = time.time() - start_time
                if span:
                    span.update(metadata={**sanitized_tags, "latency_seconds": elapsed, "error": str(e)})
                    span.end()
                raise
        except Exception as e:
            logger.warning(f"Failed to start nested span: {e}")
            yield None
    
    def log_params(self, params: Dict[str, Any], run_id: Optional[str] = None):
        """Log parameters to the current trace."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            # Update trace metadata with params
            self._current_trace.update(input=params)
        except Exception as e:
            logger.warning(f"Failed to log params: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], run_id: Optional[str] = None, step: Optional[int] = None):
        """Log metrics to the current trace."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            # Add metrics to trace metadata
            self._current_trace.update(metadata={"metrics": metrics})
        except Exception as e:
            logger.warning(f"Failed to log metrics: {e}")
    
    def log_artifact(self, artifact_path: str, run_id: Optional[str] = None):
        """Log an artifact file reference."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            # Log artifact path as metadata (Langfuse doesn't store files)
            self._current_trace.update(metadata={"artifact_path": artifact_path})
        except Exception as e:
            logger.warning(f"Failed to log artifact: {e}")
    
    def log_dict_artifact(self, data: Dict[str, Any], filename: str, run_id: Optional[str] = None):
        """Log a dictionary as trace output/metadata."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            # Log as output for better visibility in Langfuse UI
            self._current_trace.update(output=data)
        except Exception as e:
            logger.warning(f"Failed to log dict artifact: {e}")
    
    def log_text_artifact(self, text: str, filename: str, run_id: Optional[str] = None):
        """Log text content as metadata."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            self._current_trace.update(metadata={filename: text})
        except Exception as e:
            logger.warning(f"Failed to log text artifact: {e}")
    
    def set_tags(self, tags: Dict[str, Any], run_id: Optional[str] = None):
        """Set tags on the current trace."""
        if not self.enabled or not self._current_trace:
            return
        
        try:
            self._current_trace.update(metadata=self._sanitize_tags(tags))
        except Exception as e:
            logger.warning(f"Failed to set tags: {e}")


# Global tracker instance
tracker = LangfuseTracker()
