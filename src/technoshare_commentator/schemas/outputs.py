from pydantic import BaseModel, Field
from typing import List

class KeyFact(BaseModel):
    fact: str
    supported_by_snippet_ids: List[int]

class StageAResult(BaseModel):
    key_facts: List[KeyFact]
    unknowns: List[str]
    coverage_assessment: str # "full", "partial", "failed"

class StageBResult(BaseModel):
    summary_10_sentences: List[str] = Field(..., min_length=10, max_length=10)
    project_relevance: List[str]
    risks_unknowns: List[str]
    next_step: str
    confidence: float
    coverage_label: str
