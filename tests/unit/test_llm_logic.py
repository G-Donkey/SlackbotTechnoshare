import pytest
from unittest.mock import MagicMock, patch
from technoshare_commentator.llm.stage_a import run_stage_a
from technoshare_commentator.llm.stage_b import run_stage_b
from technoshare_commentator.schemas.evidence import EvidencePack, EvidenceSource, EvidenceSnippet
from technoshare_commentator.schemas.outputs import StageAResult, StageBResult, KeyFact

# Sample Data Fixtures
@pytest.fixture
def sample_evidence():
    return EvidencePack(
        sources=[EvidenceSource(url="http://test.com", fetched_at="2024-01-01")],
        snippets=[EvidenceSnippet(id=1, content="Python 4.0 released today.", source_url="http://test.com")],
        coverage="full"
    )

@pytest.fixture
def sample_facts():
    return StageAResult(
        key_facts=[KeyFact(fact="Python 4.0 is out", supported_by_snippet_ids=[1])],
        unknowns=[],
        coverage_assessment="full"
    )

def test_stage_a_fact_extraction(sample_evidence):
    """
    WHY: Verify that Stage A correctly sends evidence to the LLM and parses the structural result.
    HOW: Mock `llm_client.run_structured` to return a valid `StageAResult` object.
    EXPECTED: The function should return the mock result without error.
    """
    from technoshare_commentator.llm.client import llm_client
    
    # Create the expected output object
    expected_output = StageAResult(
        key_facts=[KeyFact(fact="Python 4.0 released", supported_by_snippet_ids=[1])],
        unknowns=[],
        coverage_assessment="full"
    )
    
    # We patch the instance method on the imported client object
    with patch.object(llm_client, 'run_with_tools', return_value=expected_output) as mock_run:
        result = run_stage_a(sample_evidence)
        
        # Check call arguments
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        prompt_arg = call_args[0][0]
        
        # Verify prompt injection
        assert "# EvidencePack" in prompt_arg
        assert "Python 4.0 released today" in prompt_arg
        
        # Verify Return
        assert result == expected_output
        assert result.key_facts[0].fact == "Python 4.0 released"

def test_stage_b_composition(sample_facts):
    """
    WHY: Verify that Stage B correctly takes facts + context and generates the strictly formatted Slack reply.
    HOW: Mock `llm_client.run_structured` to return a valid `StageBResult`. Pass fake project context.
    EXPECTED: 
        1. Prompt contains facts and the YAML context.
        2. Returns the structured StageBResult.
    """
    from technoshare_commentator.llm.client import llm_client
    
    project_context = {"themes": [{"name": "AI Ops"}]}
    
    expected_output = StageBResult(
        summary_10_sentences=["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10"],
        project_relevance=["(Theme: AI Ops) Relevance point 1", "Point 2"],
        risks_unknowns=["Risk 1"],
        next_step="Do this.",
        confidence=0.9,
        coverage_label="full"
    )
    
    with patch.object(llm_client, 'run_structured', return_value=expected_output) as mock_run:
        result = run_stage_b(sample_facts, project_context)
        
        # Verify Prompt
        prompt = mock_run.call_args[0][0]
        assert "# KeyFacts" in prompt
        assert "Python 4.0 is out" in prompt
        assert "# ProjectContext" in prompt
        assert "AI Ops" in prompt
        
        assert len(result.summary_10_sentences) == 10
        assert result.confidence == 0.9

def test_llm_malformed_response_retry(sample_evidence):
    """
    WHY: LLMs sometimes fail to return valid JSON matching the schema. Our client (beta.parse) usually handles this, 
         but if it raises an error, we want to know it propagates or is handled.
    HOW: Mock `run_structured` to raise an OpenAI API error or Pydantic validation error.
    EXPECTED: The function should raise the exception (so the worker can retry later) or handle it.
              Current implementation assumes `client.py` handles retries or propagates. We verify propagation here.
    """
    from technoshare_commentator.llm.client import llm_client
    
    with patch.object(llm_client, 'run_with_tools', side_effect=ValueError("Invalid JSON")):
        with pytest.raises(ValueError):
            run_stage_a(sample_evidence)
