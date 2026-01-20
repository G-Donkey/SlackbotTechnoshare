"""Single-stage content analysis.

Analyzes web content and generates structured reply in one LLM call.
Combines fact extraction and composition for faster, simpler processing.
"""

from typing import Dict, Any
from .client import llm_client
from .prompts import load_prompt
from ..schemas.evidence import EvidencePack
from .schema import AnalysisResult
from ..config import get_settings

settings = get_settings()


def run_analysis(evidence: EvidencePack) -> AnalysisResult:
    """
    Analyze evidence and generate structured reply in a single LLM call.
    
    Args:
        evidence: Extracted web content (snippets and sources)
        
    Returns:
        AnalysisResult with tldr, summary, projects, similar_tech
    """
    prompt_template = load_prompt("analyze")
    
    evidence_dump = evidence.model_dump_json(indent=2)
    
    prompt = (
        f"{prompt_template}\n\n"
        f"# Evidence\n{evidence_dump}"
    )
    
    return llm_client.run_structured(prompt, AnalysisResult, model=settings.MODEL)
