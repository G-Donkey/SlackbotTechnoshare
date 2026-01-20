"""
MLflow tracking integration for TechnoShare Commentator.
Provides job-level tracking with nested runs for different stages.
"""
import logging
import json
import time
from typing import Optional, Dict, Any, List
from contextlib import contextmanager
from pathlib import Path

import mlflow
from mlflow.entities import RunStatus

from ..config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class MLflowTracker:
    """Handles MLflow tracking for the pipeline."""
    
    def __init__(self):
        self.enabled = settings.MLFLOW_ENABLE_TRACKING
        if self.enabled:
            try:
                mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
                mlflow.set_experiment(settings.MLFLOW_EXPERIMENT_NAME)
                
                # Enable autologging for OpenAI to capture LLM traces
                try:
                    mlflow.openai.autolog()
                    logger.info("MLflow OpenAI autologging enabled")
                except Exception as e:
                    logger.warning(f"Failed to enable OpenAI autologging: {e}")
                
                logger.info(f"MLflow tracking enabled: {settings.MLFLOW_TRACKING_URI}")
            except Exception as e:
                logger.warning(f"Failed to initialize MLflow tracking: {e}")
                self.enabled = False
        else:
            logger.info("MLflow tracking disabled")
    
    def _sanitize_tags(self, tags: Dict[str, Any]) -> Dict[str, str]:
        """Ensure all tag values are strings (MLflow requirement)."""
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
        Start a new MLflow run for a job.
        Yields the run_id for nested runs.
        """
        if not self.enabled:
            yield None
            return
        
        run_tags = {
            "job_id": job_id,
            "channel_id": channel_id,
            "message_ts": message_ts,
            "component": "pipeline",
        }
        if target_url:
            run_tags["target_url"] = target_url
        if tags:
            run_tags.update(tags)
        
        # MLflow requires all tag values to be strings
        run_tags = self._sanitize_tags(run_tags)
        
        run = mlflow.start_run(run_name=f"job_{job_id}", tags=run_tags)
        run_id = run.info.run_id
        
        try:
            yield run_id
            mlflow.set_tag("status", "success")
            mlflow.end_run(status=RunStatus.to_string(RunStatus.FINISHED))
        except Exception as e:
            logger.exception("Run failed")
            mlflow.set_tag("status", "failed")
            mlflow.set_tag("error", str(e))
            mlflow.end_run(status=RunStatus.to_string(RunStatus.FAILED))
            raise
    
    @contextmanager
    def start_nested_run(
        self,
        run_name: str,
        parent_run_id: Optional[str] = None,
        tags: Optional[Dict[str, Any]] = None
    ):
        """Start a nested run for a specific stage or component.
        
        Note: The parent run should already be active when calling this.
        """
        if not self.enabled:
            yield None
            return
        
        # Parent run is already active, just start nested run directly
        sanitized_tags = self._sanitize_tags(tags) if tags else {}
        with mlflow.start_run(run_name=run_name, nested=True, tags=sanitized_tags) as nested_run:
            start_time = time.time()
            try:
                yield nested_run.info.run_id
                elapsed = time.time() - start_time
                mlflow.log_metric("latency_seconds", elapsed)
            except Exception as e:
                elapsed = time.time() - start_time
                mlflow.log_metric("latency_seconds", elapsed)
                mlflow.set_tag("error", str(e))
                raise
    
    def log_params(self, params: Dict[str, Any], run_id: Optional[str] = None):
        """Log parameters to MLflow."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just log directly
            mlflow.log_params(params)
        except Exception as e:
            logger.warning(f"Failed to log params: {e}")
    
    def log_metrics(self, metrics: Dict[str, float], run_id: Optional[str] = None, step: Optional[int] = None):
        """Log metrics to MLflow."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just log directly
            mlflow.log_metrics(metrics, step=step)
        except Exception as e:
            logger.warning(f"Failed to log metrics: {e}")
    
    def log_artifact(self, artifact_path: str, run_id: Optional[str] = None):
        """Log an artifact file to MLflow."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just log directly
            mlflow.log_artifact(artifact_path)
        except Exception as e:
            logger.warning(f"Failed to log artifact: {e}")
    
    def log_dict_artifact(self, data: Dict[str, Any], filename: str, run_id: Optional[str] = None):
        """Log a dictionary as a JSON artifact."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just log directly
            mlflow.log_dict(data, filename)
        except Exception as e:
            logger.warning(f"Failed to log dict artifact: {e}")
    
    def log_text_artifact(self, text: str, filename: str, run_id: Optional[str] = None):
        """Log text content as an artifact."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just log directly
            mlflow.log_text(text, filename)
        except Exception as e:
            logger.warning(f"Failed to log text artifact: {e}")
    
    def set_tags(self, tags: Dict[str, Any], run_id: Optional[str] = None):
        """Set tags on the current or specified run."""
        if not self.enabled:
            return
        
        try:
            # Don't re-enter run if already active, just set directly
            mlflow.set_tags(self._sanitize_tags(tags))
        except Exception as e:
            logger.warning(f"Failed to set tags: {e}")


# Global tracker instance
tracker = MLflowTracker()
