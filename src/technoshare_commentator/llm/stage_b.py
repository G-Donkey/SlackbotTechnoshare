from typing import Dict, Any
from .client import llm_client
from .prompts import load_prompt
from ..schemas.outputs import StageAResult
from .stage_b_schema import StageBResult
from ..config import get_settings

settings = get_settings()

def run_stage_b(facts: StageAResult, project_context: Dict[str, Any]) -> StageBResult:
    prompt_template = load_prompt("stage_b_compose_reply")
    
    facts_dump = facts.model_dump_json(indent=2)
    context_dump = str(project_context) # YAML dict as string
    
    prompt = f"{prompt_template}\n\n# KeyFacts\n{facts_dump}\n\n# ProjectContext\n{context_dump}"
    
    return llm_client.run_structured(prompt, StageBResult, model=settings.MODEL_STAGE_B)
