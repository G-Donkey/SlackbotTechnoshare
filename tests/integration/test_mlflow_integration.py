"""Integration tests for MLflow functionality.

These tests verify the full MLflow integration with real MLflow server.
Run these tests only when MLflow server is available.
"""
import pytest
import time
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

# Skip all tests in this module if MLflow server is not available
pytest.skip("Integration tests require running MLflow server", allow_module_level=True)


class TestMLflowIntegration:
    """Integration tests with real MLflow server."""
    
    @pytest.fixture(autouse=True)
    def setup_mlflow_env(self):
        """Set up test environment with MLflow enabled."""
        with patch.dict('os.environ', {
            'MLFLOW_TRACKING_URI': 'http://localhost:5000',
            'MLFLOW_EXPERIMENT_NAME': 'test_integration',
            'MLFLOW_ENABLE_TRACKING': 'true',
            'MLFLOW_ENABLE_TRACING': 'true'
        }):
            yield
    
    def test_full_pipeline_tracking(self):
        """Test full pipeline run with tracking."""
        import mlflow
        from technoshare_commentator.mlops.tracking import tracker
        
        # Start a test run
        with tracker.start_job_run(
            job_id="integration_test_1",
            channel_id="C123TEST",
            message_ts="1234567890.123",
            target_url="https://example.com/test"
        ) as run_id:
            assert run_id is not None
            
            # Log some test data
            tracker.log_params({
                "model": "test-model",
                "temperature": 0.7
            }, run_id=run_id)
            
            tracker.log_metrics({
                "latency_seconds": 1.5,
                "token_count": 100
            }, run_id=run_id)
            
            tracker.log_dict_artifact({
                "test": "data",
                "nested": {"key": "value"}
            }, "test_artifact.json", run_id=run_id)
        
        # Verify run exists in MLflow
        client = mlflow.tracking.MlflowClient()
        run = client.get_run(run_id)
        
        assert run.data.params["model"] == "test-model"
        assert float(run.data.metrics["latency_seconds"]) == 1.5
        assert run.data.tags["job_id"] == "integration_test_1"
    
    def test_nested_runs_tracking(self):
        """Test nested run creation and tracking."""
        import mlflow
        from technoshare_commentator.mlops.tracking import tracker
        
        with tracker.start_job_run("test_nested", "C123", "123") as parent_run_id:
            # Create nested run
            with tracker.start_nested_run(
                "test_stage",
                parent_run_id=parent_run_id,
                tags={"stage": "test"}
            ) as nested_run_id:
                assert nested_run_id is not None
                
                tracker.log_metrics({
                    "stage_latency": 0.5
                }, run_id=nested_run_id)
        
        # Verify nested structure
        client = mlflow.tracking.MlflowClient()
        nested_run = client.get_run(nested_run_id)
        
        assert nested_run.data.tags.get("stage") == "test"
        assert nested_run.data.tags.get("mlflow.parentRunId") == parent_run_id
    
    def test_tracing_integration(self):
        """Test tracing with real MLflow."""
        from technoshare_commentator.mlops.tracing import tracer
        
        with tracer.span(
            "test_operation",
            span_type="LLM",
            attributes={"model": "test-gpt"},
            inputs={"prompt": "test prompt"}
        ) as span:
            # Simulate some work
            time.sleep(0.1)
            
            # Trace LLM call
            tracer.trace_llm_call(
                model="test-gpt",
                prompt="test prompt",
                response="test response",
                tool_calls=["search"],
                sources=["https://example.com"]
            )
        
        # Span should have been created (manual verification in UI)
    
    def test_artifact_logging(self):
        """Test artifact logging with various types."""
        import mlflow
        from technoshare_commentator.mlops.tracking import tracker
        
        with tracker.start_job_run("test_artifacts", "C123", "123") as run_id:
            # Log dict artifact
            tracker.log_dict_artifact({
                "test": "data",
                "number": 42
            }, "test.json", run_id=run_id)
            
            # Log text artifact
            tracker.log_text_artifact(
                "This is test text content",
                "test.txt",
                run_id=run_id
            )
        
        # Verify artifacts exist
        client = mlflow.tracking.MlflowClient()
        artifacts = client.list_artifacts(run_id)
        artifact_paths = [a.path for a in artifacts]
        
        assert "test.json" in artifact_paths
        assert "test.txt" in artifact_paths
    
    def test_graceful_degradation(self):
        """Test that system works when MLflow is unavailable."""
        with patch.dict('os.environ', {
            'MLFLOW_TRACKING_URI': 'http://localhost:9999',  # Wrong port
            'MLFLOW_ENABLE_TRACKING': 'true'
        }):
            from technoshare_commentator.mlops.tracking import MLflowTracker
            
            # Should disable itself
            tracker = MLflowTracker()
            
            # These should not raise errors
            with tracker.start_job_run("test", "C123", "123") as run_id:
                tracker.log_params({"test": "value"}, run_id=run_id)
                tracker.log_metrics({"test": 1.0}, run_id=run_id)


class TestEvaluationIntegration:
    """Integration tests for evaluation suite."""
    
    def test_evaluation_runner_with_dataset(self):
        """Test running evaluation on a small dataset."""
        from technoshare_commentator.mlops.evaluation.dataset import EvalDataset, EvalExample
        from technoshare_commentator.mlops.evaluation.scorers import run_hard_checks
        from technoshare_commentator.llm.schema import AnalysisResult
        
        # Create test dataset
        dataset = EvalDataset(name="test", version="1.0")
        dataset.add_example(EvalExample(
            id="test_1",
            url="https://example.com",
            slack_text="Test URL: https://example.com",
            tags=["test"]
        ))
        
        # Create test result
        result = AnalysisResult(
            tldr=["Test TLDR sentence one.", "With three sentences total.", "All is good here."],
            summary="This is a comprehensive test summary paragraph with sufficient length. It covers multiple aspects of the content being analyzed. The technology presents interesting possibilities. Performance metrics show improvements over baseline. Overall a valuable addition to our toolkit.",
            projects=["**Test** — project one", "**Theme** — project two", "**Other** — project three"],
            similar_tech=["**Tech 1** — first tech."]
        )
        
        # Run scorers
        scores = run_hard_checks(result)
        
        assert scores.overall_pass_rate() == 1.0
        assert len(scores.scores) >= 5
