"""Tests for MLflow tracing functionality."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from technoshare_commentator.mlops.tracing import MLflowTracer, traced_operation


@pytest.fixture
def mock_settings_enabled():
    """Mock settings with tracing enabled."""
    with patch('technoshare_commentator.mlops.tracing.settings') as mock:
        mock.MLFLOW_ENABLE_TRACING = True
        mock.MLFLOW_TRACKING_URI = "http://localhost:5000"
        yield mock


@pytest.fixture
def mock_settings_disabled():
    """Mock settings with tracing disabled."""
    with patch('technoshare_commentator.mlops.tracing.settings') as mock:
        mock.MLFLOW_ENABLE_TRACING = False
        yield mock


class TestMLflowTracerEnabled:
    """Tests for MLflowTracer when enabled."""
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_tracer_initialization_enabled(self, mock_mlflow, mock_settings_enabled):
        """Test tracer initializes correctly when enabled."""
        tracer = MLflowTracer()
        
        assert tracer.enabled is True
        mock_mlflow.set_tracking_uri.assert_called_once_with("http://localhost:5000")
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_span_creation(self, mock_mlflow, mock_settings_enabled):
        """Test span is created with correct parameters."""
        tracer = MLflowTracer()
        
        mock_span = Mock()
        mock_mlflow.start_span.return_value.__enter__.return_value = mock_span
        
        attributes = {"model": "gpt-4o", "temperature": 0.7}
        inputs = {"prompt": "test"}
        
        with tracer.span("test_operation", "LLM", attributes, inputs) as span:
            assert span is mock_span
        
        # Verify span was started
        mock_mlflow.start_span.assert_called_once()
        call_kwargs = mock_mlflow.start_span.call_args[1]
        assert call_kwargs['name'] == "test_operation"
        assert call_kwargs['span_type'] == "LLM"
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    @patch('technoshare_commentator.mlops.tracing.time')
    def test_span_tracks_latency(self, mock_time, mock_mlflow, mock_settings_enabled):
        """Test span tracks execution latency."""
        tracer = MLflowTracer()
        
        mock_span = Mock()
        mock_mlflow.start_span.return_value.__enter__.return_value = mock_span
        mock_time.time.side_effect = [1000.0, 1001.5]  # 1.5 second duration
        
        with tracer.span("test_operation", "LLM"):
            pass
        
        # Verify latency was set
        mock_span.set_attribute.assert_called_once_with("latency_ms", 1500)
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_trace_llm_call(self, mock_mlflow, mock_settings_enabled):
        """Test tracing LLM call details."""
        tracer = MLflowTracer()
        
        # Mock the current span
        mock_span = Mock()
        mock_mlflow.get_current_active_span.return_value = mock_span
        
        tracer.trace_llm_call(
            model="gpt-4o",
            prompt="test prompt",
            response="test response",
            tool_calls=["search"],
            sources=["https://example.com"],
            tokens={"prompt_tokens": 100, "completion_tokens": 50}
        )
        
        # Verify get_current_active_span was called
        mock_mlflow.get_current_active_span.assert_called_once()
        # Verify attributes were set on the span
        mock_span.set_attributes.assert_called_once()
        attributes = mock_span.set_attributes.call_args[0][0]
        assert attributes["model"] == "gpt-4o"
        assert attributes["tool_calls"] == "search"
        assert attributes["tool_call_count"] == 1
        assert attributes["sources"] == "https://example.com"
        assert attributes["source_count"] == 1
        assert attributes["prompt_tokens"] == 100
        assert attributes["completion_tokens"] == 50
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_trace_retrieval(self, mock_mlflow, mock_settings_enabled):
        """Test tracing retrieval operation."""
        tracer = MLflowTracer()
        
        # Mock the current span
        mock_span = Mock()
        mock_mlflow.get_current_active_span.return_value = mock_span
        
        tracer.trace_retrieval(
            url="https://example.com",
            adapter_name="GenericAdapter",
            coverage="full",
            snippet_count=5
        )
        
        # Verify get_current_active_span was called
        mock_mlflow.get_current_active_span.assert_called_once()
        # Verify attributes were set on the span
        mock_span.set_attributes.assert_called_once()
        attributes = mock_span.set_attributes.call_args[0][0]
        assert attributes["url"] == "https://example.com"
        assert attributes["adapter"] == "GenericAdapter"
        assert attributes["coverage"] == "full"
        assert attributes["snippet_count"] == 5
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_trace_quality_gates(self, mock_mlflow, mock_settings_enabled):
        """Test tracing quality gate results."""
        tracer = MLflowTracer()
        
        # Mock the current span
        mock_span = Mock()
        mock_mlflow.get_current_active_span.return_value = mock_span
        
        failures = ["gate1", "gate2"]
        tracer.trace_quality_gates(failures, total_gates=5)
        
        # Verify get_current_active_span was called
        mock_mlflow.get_current_active_span.assert_called_once()
        # Verify attributes were set on the span
        mock_span.set_attributes.assert_called_once()
        attributes = mock_span.set_attributes.call_args[0][0]
        assert attributes["gate_failures"] == 2
        assert attributes["gate_total"] == 5
        assert attributes["gate_pass_rate"] == 0.6
        assert attributes["failed_gates"] == "gate1,gate2"


class TestMLflowTracerDisabled:
    """Tests for MLflowTracer when disabled."""
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_tracer_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test tracer is disabled correctly."""
        tracer = MLflowTracer()
        
        assert tracer.enabled is False
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_span_noop_when_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test span is no-op when disabled."""
        tracer = MLflowTracer()
        
        with tracer.span("test_operation", "LLM") as span:
            assert span is None
        
        mock_mlflow.start_span.assert_not_called()
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_trace_llm_call_noop_when_disabled(self, mock_mlflow, mock_settings_disabled):
        """Test tracing LLM call is no-op when disabled."""
        tracer = MLflowTracer()
        
        tracer.trace_llm_call("gpt-4o", "prompt", "response")
        
        mock_mlflow.set_span_attributes.assert_not_called()


class TestTracedOperationDecorator:
    """Tests for the traced_operation decorator."""
    
    @patch('technoshare_commentator.mlops.tracing.tracer')
    def test_decorator_traces_function(self, mock_tracer):
        """Test decorator creates span for function execution."""
        mock_span = Mock()
        mock_tracer.span.return_value.__enter__.return_value = mock_span
        mock_tracer.span.return_value.__exit__ = Mock(return_value=False)
        
        @traced_operation("test_func", span_type="CHAIN")
        def test_function(x, y):
            return x + y
        
        result = test_function(1, 2)
        
        assert result == 3
        mock_tracer.span.assert_called_once_with(name="test_func", span_type="CHAIN")


class TestMLflowTracerGracefulDegradation:
    """Tests for graceful degradation when tracing fails."""
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_initialization_failure_disables_tracer(self, mock_mlflow):
        """Test tracer disables itself if initialization fails."""
        with patch('technoshare_commentator.mlops.tracing.settings') as mock_settings:
            mock_settings.MLFLOW_ENABLE_TRACING = True
            mock_mlflow.set_tracking_uri.side_effect = Exception("Connection failed")
            
            tracer = MLflowTracer()
            
            assert tracer.enabled is False
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_span_handles_failure(self, mock_mlflow, mock_settings_enabled):
        """Test span creation handles failures gracefully."""
        tracer = MLflowTracer()
        mock_mlflow.start_span.side_effect = Exception("Span creation failed")
        
        # Should raise since we changed to propagate exceptions
        with pytest.raises(Exception, match="Span creation failed"):
            with tracer.span("test_operation", "LLM") as span:
                pass
    
    @patch('technoshare_commentator.mlops.tracing.mlflow')
    def test_trace_llm_call_handles_failure(self, mock_mlflow, mock_settings_enabled):
        """Test tracing LLM call handles failures gracefully."""
        tracer = MLflowTracer()
        mock_mlflow.get_current_active_span.side_effect = Exception("Tracing failed")
        
        # Should not raise - errors are caught and logged
        tracer.trace_llm_call("gpt-4o", "prompt", "response")
