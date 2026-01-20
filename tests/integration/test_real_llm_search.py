import pytest
from pydantic import BaseModel
from typing import List
from technoshare_commentator.llm.client import llm_client

pytestmark = pytest.mark.integration


class SimpleFactResult(BaseModel):
    """Simple schema for testing LLM tool usage."""
    key_facts: List[str]
    source_used: bool


@pytest.mark.timeout(60)
def test_real_openai_search_meta_blog(allow_integration, openai_api_key):
    """
    WHY: Verify that the LLM can use the 'search' tool to read a real URL and extract facts.
    """
    if not allow_integration:
        pytest.skip("Set RUN_INTEGRATION_TESTS=1 to run integration tests")
    if not openai_api_key:
        pytest.skip("OPENAI_API_KEY not set")

    url = "https://ai.meta.com/blog/sam-audio/"
    prompt = (
        f"Extract key facts from this link: {url}. "
        "Use your 'search' tool to read the content first. "
        "Return as JSON with key_facts (list of strings) and source_used (boolean)."
    )

    # Use return_meta=True to get observability
    result = llm_client.run_with_tools(prompt, SimpleFactResult, return_meta=True)

    # 1. Check Structure
    assert isinstance(result.parsed, SimpleFactResult)
    assert len(result.parsed.key_facts) >= 1
    
    # 2. Check Observability (Did it actually use the tool?)
    assert "search" in result.meta.tool_calls
    assert any(url in s for s in result.meta.sources)
    
    # 3. Soft Content Check
    all_facts_text = " ".join(f.lower() for f in result.parsed.key_facts)
    # Just ensure it's not empty or hallucinated gibberish; look for reasonable length
    assert len(all_facts_text) > 50
    
    print(f"\nExtracted Facts: {result.parsed.key_facts}")