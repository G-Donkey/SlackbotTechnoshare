from .client import llm_client
from .prompts import load_prompt
from ..schemas.evidence import EvidencePack
from ..schemas.outputs import StageAResult
from ..config import get_settings

settings = get_settings()

def run_stage_a(evidence: EvidencePack) -> StageAResult:
    prompt_template = load_prompt("stage_a_extract_facts")
    
    # Simple injection
    evidence_dump = evidence.model_dump_json(indent=2)
    prompt = f"{prompt_template}\n\n# EvidencePack\n{evidence_dump}"
    
    return llm_client.run_structured(prompt, StageAResult, model=settings.MODEL_STAGE_A)
