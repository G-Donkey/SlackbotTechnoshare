from .client import llm_client
from .prompts import load_prompt
from ..schemas.evidence import EvidencePack
from ..schemas.outputs import StageAResult
from ..config import get_settings

settings = get_settings()

def run_stage_a(evidence: EvidencePack) -> StageAResult:
    prompt_template = load_prompt("stage_a_extract_facts")
    
    # Updated prompt injection to encourage tool usage
    evidence_dump = evidence.model_dump_json(indent=2)
    prompt = (
        f"{prompt_template}\n\n"
        f"# EvidencePack\n{evidence_dump}\n\n"
        "NOTE: You have a 'search' tool available. If the snippets in the EvidencePack are insufficient "
        "or if the link content seems truncated, use the 'search' tool to fetch the full page content from the source URL "
        "before checking for facts."
    )
    
    return llm_client.run_with_tools(prompt, StageAResult, model=settings.MODEL_STAGE_A)
