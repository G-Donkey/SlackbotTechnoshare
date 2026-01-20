"""Unit tests for Langfuse tracing."""

import pytest
from unittest.mock import patch, MagicMock


class TestLangfuseTracer:
    """Tests for LangfuseTracer class."""
    
    @patch('technoshare_commentator.mlops.tracing._get_langfuse')
    @patch('technoshare_commentator.mlops.tracing.get_settings')
    def test_tracer_disabled_when_langfuse_disabled(self, mock_settings, mock_get_langfuse):
        """Tracer should be disabled when LANGFUSE_ENABLED is False."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracing import LangfuseTracer
        tracer = LangfuseTracer()
        
        assert tracer.enabled is False
    
    @patch('technoshare_commentator.mlops.tracing._get_langfuse')
    @patch('technoshare_commentator.mlops.tracing.get_settings')
    def test_span_yields_none_when_disabled(self, mock_settings, mock_get_langfuse):
        """span() should yield None when disabled."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracing import LangfuseTracer
        tracer = LangfuseTracer()
        
        with tracer.span("test_span") as ctx:
            assert ctx is None
    
    @patch('technoshare_commentator.mlops.tracing._get_langfuse')
    @patch('technoshare_commentator.mlops.tracing.get_settings')
    def test_trace_methods_noop_when_disabled(self, mock_settings, mock_get_langfuse):
        """Trace methods should be no-op when disabled."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracing import LangfuseTracer
        tracer = LangfuseTracer()
        
        # These should not raise
        tracer.trace_llm_call("gpt-4o", "prompt", "response")
        tracer.trace_retrieval("https://example.com", "GenericAdapter", "full", 5)
        tracer.trace_quality_gates([], 5)
        tracer.flush()


class TestTracedOperationDecorator:
    """Tests for traced_operation decorator."""
    
    @patch('technoshare_commentator.mlops.tracing._get_langfuse')
    @patch('technoshare_commentator.mlops.tracing.get_settings')
    def test_traced_operation_decorator(self, mock_settings, mock_get_langfuse):
        """traced_operation decorator should work when disabled."""
        mock_settings.return_value.LANGFUSE_ENABLED = False
        mock_get_langfuse.return_value = None
        
        from technoshare_commentator.mlops.tracing import traced_operation
        
        @traced_operation("test.function")
        def my_function(x):
            return x * 2
        
        result = my_function(5)
        assert result == 10
