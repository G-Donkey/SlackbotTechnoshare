"""Unit tests for Langfuse tracking."""

import pytest
from unittest.mock import patch, MagicMock


class TestLangfuseTracker:
    """Tests for LangfuseTracker class."""
    
    @patch('technoshare_commentator.mlops.tracking._get_langfuse')
    @patch('technoshare_commentator.mlops.tracking.get_settings')
    def test_tracker_disabled_when_langfuse_disabled(self, mock_settings, mock_get_langfuse):
        """Tracker should be disabled when LANGFUSE_ENABLED is False."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracking import LangfuseTracker
        tracker = LangfuseTracker()
        
        assert tracker.enabled is False
    
    @patch('technoshare_commentator.mlops.tracking._get_langfuse')
    @patch('technoshare_commentator.mlops.tracking.get_settings')
    def test_start_job_run_yields_none_when_disabled(self, mock_settings, mock_get_langfuse):
        """start_job_run should yield None when disabled."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracking import LangfuseTracker
        tracker = LangfuseTracker()
        
        with tracker.start_job_run("job1", "C123", "123.456") as trace_id:
            assert trace_id is None
    
    @patch('technoshare_commentator.mlops.tracking._get_langfuse')
    @patch('technoshare_commentator.mlops.tracking.get_settings')
    def test_sanitize_tags(self, mock_settings, mock_get_langfuse):
        """Tags should be sanitized to strings."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracking import LangfuseTracker
        tracker = LangfuseTracker()
        
        tags = {"string": "value", "int": 42, "none": None}
        sanitized = tracker._sanitize_tags(tags)
        
        assert sanitized == {"string": "value", "int": "42"}
        assert "none" not in sanitized


class TestLangfuseTrackerIntegration:
    """Integration tests for LangfuseTracker (requires Langfuse)."""
    
    @pytest.mark.integration
    @patch('technoshare_commentator.mlops.tracking._get_langfuse')
    @patch('technoshare_commentator.mlops.tracking.get_settings')
    def test_full_job_tracking(self, mock_settings, mock_get_langfuse):
        """Test complete job tracking workflow with mocked Langfuse."""
        # Setup mocks
        mock_settings.return_value.LANGFUSE_ENABLED = True
        mock_settings.return_value.LANGFUSE_HOST = "http://localhost:3000"
        
        mock_span = MagicMock()
        mock_span.id = "test-span-id"
        mock_nested_span = MagicMock()
        mock_nested_span.id = "test-nested-span-id"
        
        mock_client = MagicMock()
        mock_client.start_span.side_effect = [mock_span, mock_nested_span]
        mock_get_langfuse.return_value = mock_client
        
        from technoshare_commentator.mlops.tracking import LangfuseTracker
        tracker = LangfuseTracker()
        
        with tracker.start_job_run(
            job_id="test-job",
            channel_id="C123",
            message_ts="123.456",
            target_url="https://example.com"
        ) as trace_id:
            assert trace_id == "test-span-id"
            
            # Test nested run
            with tracker.start_nested_run("retrieval", parent_run_id=trace_id) as span_id:
                assert span_id == "test-nested-span-id"
        
        # Verify spans were created
        assert mock_client.start_span.call_count == 2
        mock_client.flush.assert_called()
