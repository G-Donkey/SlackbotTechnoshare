"""Tests for MLflow tracking functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from technoshare_commentator.mlops.tracking import MLflowTracker
from technoshare_commentator.config import Settings


@pytest.fixture
def mock_settings():
    """Mock settings with MLflow enabled."""
    with patch('technoshare_commentator.mlops.tracking.settings') as mock:
        mock.MLFLOW_ENABLE_TRACKING = True
        mock.MLFLOW_TRACKING_URI = "http://localhost:5000"
        mock.MLFLOW_EXPERIMENT_NAME = "test_experiment"
        yield mock


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with MLflow disabled."""
    with patch('technoshare_commentator.mlops.tracking.settings') as mock:
        mock.MLFLOW_ENABLE_TRACKING = False
        yield mock


class TestMLflowTrackerEnabled:
    """Tests for MLflowTracker when enabled."""
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_tracker_initialization_enabled(self, mock_mlflow, mock_settings):
        """Test tracker initializes correctly when enabled."""
        tracker = MLflowTracker()
        
        assert tracker.enabled is True
        mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")
        mock_mlflow.set_experiment.assert_called_once_with("test_experiment")
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_start_job_run_success(self, mock_mlflow, mock_settings):
        """Test starting a job run logs correct metadata."""
        tracker = MLflowTracker()
        
        # Mock run
        mock_run = Mock()
        mock_run.info.run_id = "test_run_123"
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = mock_run
        
        with tracker.start_job_run(
            job_id="job_123",
            channel_id="C123",
            message_ts="1234567890.123",
            target_url="https://example.com"
        ) as run_id:
            assert run_id == "test_run_123"
        
        # Verify run was started with correct tags
        call_kwargs = mock_mlflow.start_run.call_args[1]
        assert call_kwargs['run_name'] == "job_job_123"
        assert 'tags' in call_kwargs
        tags = call_kwargs['tags']
        assert tags['job_id'] == "job_123"
        assert tags['channel_id'] == "C123"
        assert tags['target_url'] == "https://example.com"
        
        # Verify run was ended
        mock_mlflow.end_run.assert_called_once()
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_start_job_run_with_exception(self, mock_mlflow, mock_settings):
        """Test job run handles exceptions correctly."""
        tracker = MLflowTracker()
        
        mock_run = Mock()
        mock_run.info.run_id = "test_run_123"
        mock_mlflow.start_run.return_value = mock_run
        mock_mlflow.active_run.return_value = mock_run
        
        with pytest.raises(ValueError):
            with tracker.start_job_run("job_123", "C123", "123"):
                raise ValueError("Test error")
        
        # Verify error was tagged
        mock_mlflow.set_tag.assert_any_call("status", "failed")
        assert any(
            call[0][0] == "error" for call in mock_mlflow.set_tag.call_args_list
        )
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_start_nested_run(self, mock_mlflow, mock_settings):
        """Test nested runs are created correctly."""
        tracker = MLflowTracker()
        
        mock_nested = Mock()
        mock_nested.info.run_id = "nested_run_123"
        mock_mlflow.start_run.return_value.__enter__.return_value = mock_nested
        
        with tracker.start_nested_run(
            run_name="test_stage",
            parent_run_id="parent_123",
            tags={"stage": "test"}
        ) as nested_id:
            assert nested_id == "nested_run_123"
        
        # Verify nested run was created
        assert mock_mlflow.start_run.call_count >= 1
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_params(self, mock_mlflow, mock_settings):
        """Test logging parameters."""
        tracker = MLflowTracker()
        
        params = {"model": "gpt-4o", "temperature": 0.7}
        tracker.log_params(params)
        
        mock_mlflow.log_params.assert_called_once_with(params)
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_metrics(self, mock_mlflow, mock_settings):
        """Test logging metrics."""
        tracker = MLflowTracker()
        
        metrics = {"latency": 1.5, "tokens": 1000}
        tracker.log_metrics(metrics)
        
        mock_mlflow.log_metrics.assert_called_once_with(metrics, step=None)
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_dict_artifact(self, mock_mlflow, mock_settings):
        """Test logging dictionary as artifact."""
        tracker = MLflowTracker()
        
        data = {"key": "value", "nested": {"a": 1}}
        tracker.log_dict_artifact(data, "test.json")
        
        mock_mlflow.log_dict.assert_called_once_with(data, "test.json")
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_text_artifact(self, mock_mlflow, mock_settings):
        """Test logging text as artifact."""
        tracker = MLflowTracker()
        
        text = "Test content"
        tracker.log_text_artifact(text, "test.txt")
        
        mock_mlflow.log_text.assert_called_once_with(text, "test.txt")


class TestMLflowTrackerDisabled:
    """Tests for MLflowTracker when disabled."""
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_tracker_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test tracker is disabled correctly."""
        tracker = MLflowTracker()
        
        assert tracker.enabled is False
        mock_mlflow.set_tracking_uri.assert_not_called()
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_start_job_run_noop_when_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test job run is no-op when disabled."""
        tracker = MLflowTracker()
        
        with tracker.start_job_run("job_123", "C123", "123") as run_id:
            assert run_id is None
        
        mock_mlflow.start_run.assert_not_called()
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_params_noop_when_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test logging params is no-op when disabled."""
        tracker = MLflowTracker()
        
        tracker.log_params({"test": "value"})
        
        mock_mlflow.log_params.assert_not_called()
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_metrics_noop_when_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test logging metrics is no-op when disabled."""
        tracker = MLflowTracker()
        
        tracker.log_metrics({"test": 1.0})
        
        mock_mlflow.log_metrics.assert_not_called()


class TestMLflowTrackerGracefulDegradation:
    """Tests for graceful degradation when MLflow fails."""
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_initialization_failure_disables_tracker(self, mock_mlflow):
        """Test tracker disables itself if initialization fails."""
        with patch('technoshare_commentator.mlops.tracking.settings') as mock_settings:
            mock_settings.MLFLOW_ENABLE_TRACKING = True
            mock_mlflow.set_tracking_uri.side_effect = Exception("Connection failed")
            
            tracker = MLflowTracker()
            
            assert tracker.enabled is False
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_params_handles_failure(self, mock_mlflow, mock_settings):
        """Test logging params handles failures gracefully."""
        tracker = MLflowTracker()
        mock_mlflow.log_params.side_effect = Exception("Logging failed")
        
        # Should not raise
        tracker.log_params({"test": "value"})
    
    @patch('technoshare_commentator.mlops.tracking.mlflow')
    def test_log_metrics_handles_failure(self, mock_mlflow, mock_settings):
        """Test logging metrics handles failures gracefully."""
        tracker = MLflowTracker()
        mock_mlflow.log_metrics.side_effect = Exception("Logging failed")
        
        # Should not raise
        tracker.log_metrics({"test": 1.0})
