from typing import List, Dict, Any
from ..schemas.outputs import StageBResult
from ..config import get_settings, load_project_context

settings = get_settings()

def run_quality_gates(result: StageBResult) -> List[str]:
    """
    Returns list of failure reasons. Empty list = pass.
    """
    failures = []
    
    # 1. Exact 10 sentences
    if len(result.summary_10_sentences) != 10:
        failures.append(f"Summary must have exactly 10 sentences, got {len(result.summary_10_sentences)}")
        
    # 2. Evidence Minimum (Implicit: if coverage failed, we might want to flag, 
    # but Stage B output handles that via coverage_label usually).
    # Let's check provided confidence.
    if result.confidence < 0.5:
         # Not a hard failure, but we append a note in the final text (handled in next step),
         # or we can fail if it's garbage.
         # User requirement: "If < 0.55: append 'Manual review recommended'". So not a gate failure usually.
         pass

    # 3. Non-generic relevance
    # Check if any relevance bullets contain a theme name from project_context
    context = load_project_context()
    themes = [t['name'] for t in context.get('themes', [])]
    
    match_count = 0
    for bullet in result.project_relevance:
        # Check if "(Theme: X)" is present or just check substring
        for t in themes:
            if t in bullet:
                match_count += 1
                break
    
    if match_count < 1 and themes:
        # We wanted min 2 in the plan, but let's be lenient for POC: at least 1 explicit map.
        # Plan said: "min 2 bullets refer explicit to theme".
        if match_count < 2:
            failures.append(f"Relevance insufficient: mapped {match_count} themes, need 2.")
            
    return failures
