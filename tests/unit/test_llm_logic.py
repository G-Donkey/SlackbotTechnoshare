"""Tests for LLM analysis logic."""

import pytest
from unittest.mock import MagicMock, patch
from technoshare_commentator.llm.analyze import run_analysis
from technoshare_commentator.llm.schema import AnalysisResult
from technoshare_commentator.schemas.evidence import EvidencePack, EvidenceSource, EvidenceSnippet


@pytest.fixture
def sample_evidence():
    return EvidencePack(
        sources=[EvidenceSource(url="http://test.com", fetched_at="2024-01-01")],
        snippets=[EvidenceSnippet(id=1, content="Python 4.0 released today.", source_url="http://test.com")],
        coverage="full"
    )


def test_analysis_runs_with_evidence_and_context(sample_evidence):
    """
    WHY: Verify that run_analysis correctly sends evidence + context to the LLM.
    HOW: Mock `llm_client.run_structured` to return a valid `AnalysisResult`.
    EXPECTED: The function should return the mock result without error.
    """
    from technoshare_commentator.llm.client import llm_client
    
    expected_output = AnalysisResult(
        tldr=["Python 4.0 is revolutionary.", "It features async everywhere.", "Breaking changes expected."],
        summary="Python 4.0 brings revolutionary changes to the language. It features async everywhere as a core concept. The new release includes breaking changes that developers should expect. Performance improvements are significant across all benchmarks. The migration path is well documented.",
        projects=[
            "**AI Ops** — Migrate to Python 4.0 for async benefits.",
            "**Cloud Native** — Leverage new deployment features.",
            "**General** — Update existing codebases.",
        ],
        similar_tech=["**Rust** — faster but more complex."],
    )
    
    with patch.object(llm_client, 'run_structured', return_value=expected_output) as mock_run:
        result = run_analysis(sample_evidence)
        
        # Check call arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        prompt_arg = call_args[0][0]
        
        # Verify prompt contains evidence
        assert "# Evidence" in prompt_arg
        assert "Python 4.0 released today" in prompt_arg
        
        # Verify return
        assert result == expected_output
        assert len(result.tldr) == 3
        assert len(result.summary) >= 100  # summary is now a string with min 100 chars


def test_llm_malformed_response_propagates_error(sample_evidence):
    """
    WHY: LLMs sometimes fail to return valid JSON. We want errors to propagate.
    HOW: Mock `run_structured` to raise an error.
    EXPECTED: The function should raise the exception (so the worker can retry later).
    """
    from technoshare_commentator.llm.client import llm_client
    
    with patch.object(llm_client, 'run_structured', side_effect=ValueError("Invalid JSON")):
        with pytest.raises(ValueError):
            run_analysis(sample_evidence)
