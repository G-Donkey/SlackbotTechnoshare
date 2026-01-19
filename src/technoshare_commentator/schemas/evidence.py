"""Pydantic schemas for evidence and retrieval data.

Defines EvidencePack, EvidenceSource, and EvidenceSnippet models.
"""

from pydantic import BaseModel
from typing import List, Optional

class EvidenceSnippet(BaseModel):
    id: int
    content: str
    source_url: str

class EvidenceSource(BaseModel):
    url: str
    title: Optional[str] = None
    fetched_at: str

class EvidencePack(BaseModel):
    sources: List[EvidenceSource]
    snippets: List[EvidenceSnippet]
    coverage: str # "full", "partial", "failed"
    errors: List[str] = []
