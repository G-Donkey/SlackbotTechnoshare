from typing import List, Dict, Any
from ..llm.stage_b_schema import StageBResult
from ..config import get_settings, load_project_context

settings = get_settings()

def run_quality_gates(result: StageBResult) -> List[str]:
    """
    Returns list of failure reasons. Empty list = pass.
    """
    failures = []
    
    # 1. Summary: 10-15 sentences (enforced by Pydantic, but double-check)
    if not (10 <= len(result.summary) <= 15):
        failures.append(f"Summary must have 10-15 sentences, got {len(result.summary)}")
    
    # 2. TDLR: exactly 3 sentences (enforced by Pydantic, but double-check)
    if len(result.tdlr) != 3:
        failures.append(f"TDLR must have exactly 3 sentences, got {len(result.tdlr)}")

    # 4. Theme mapping in projects
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
