"""Quality gate validation for LLM outputs.

Ensures analysis results meet formatting and content requirements
before posting to Slack.
"""

from typing import List
from ..llm.schema import AnalysisResult
from ..config import get_settings

settings = get_settings()

def run_quality_gates(result: AnalysisResult) -> List[str]:
    """
    Returns list of failure reasons. Empty list = pass.
    """
    failures = []
    
    # 1. Summary: minimum 100 characters (enforced by Pydantic, but double-check)
    if len(result.summary) < 100:
        failures.append(f"Summary must be at least 100 characters, got {len(result.summary)}")
    
    # 2. tldr: exactly 3 sentences (enforced by Pydantic, but double-check)
    if len(result.tldr) != 3:
        failures.append(f"tldr must have exactly 3 sentences, got {len(result.tldr)}")

    # 3. Project bullets: minimum 3 bullets
    if len(result.projects) < 3:
        failures.append(f"Projects must have at least 3 bullets, got {len(result.projects)}")
            
    return failures
