"""Quality gate validation for LLM outputs.

Ensures analysis results meet formatting and content requirements
before posting to Slack.
"""

from typing import List, Dict, Any, Union
from ..llm.schema import AnalysisResult
from ..config import get_settings, load_project_context

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

    # 3. Theme mapping in projects
    # Check if any project bullets contain a theme name from project_context
    context = load_project_context()
    themes = [t['name'] for t in context.get('themes', [])]
    
    match_count = 0
    for bullet in result.projects:
        # Each bullet should start with "**Theme:** <ThemeName>"
        for t in themes:
            if t in bullet:
                match_count += 1
                break
    
    if match_count < 2 and themes:
        # We want at least 2 explicit theme mappings
        failures.append(f"Project relevance insufficient: mapped {match_count} themes, need at least 2.")
            
    return failures
