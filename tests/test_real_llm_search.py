import pytest
import os
from dotenv import load_dotenv
from technoshare_commentator.llm.client import llm_client
from technoshare_commentator.schemas.outputs import StageAResult

load_dotenv()

def test_real_openai_search_meta_blog():
    """
    WHY: Verify that the LLM can use the 'search' tool to read a real URL and extract facts.
    HOW: Provide a URL within the prompt and call run_with_tools.
    EXPECTED: 
        1. Model calls the 'search' tool.
        2. Model returns a StageAResult with facts about SAM 2 / Audio from the Meta blog.
    """
    # 1. Mock 'reading a link from slack' - we just provide it in the prompt
    slack_message = "Check this out: https://ai.meta.com/blog/sam-audio/"
    
    # Check if API key is present
    if not os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY") == "sk-...":
        pytest.skip("OPENAI_API_KEY not set for real integration test")

    # 2. Make actual OpenAI call with search tool
    prompt = f"Extract key facts from this link: {slack_message}. Use your 'search' tool to read the content first."
    
    result = llm_client.run_with_tools(prompt, StageAResult)
    
    # Assertions
    assert isinstance(result, StageAResult)
    assert len(result.key_facts) > 0
    
    # Check for keywords expected from the specific Meta blog post (Segment Anything Model / Audio)
    all_facts_text = " ".join([f.fact.lower() for f in result.key_facts])
    assert "audio" in all_facts_text or "sam" in all_facts_text
    
    print(f"\nExtracted Facts: {result.key_facts}")
    print(f"Unknowns: {result.unknowns}")
    print(f"Coverage: {result.coverage_assessment}")

