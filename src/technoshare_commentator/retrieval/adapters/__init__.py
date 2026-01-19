"""Content retrieval adapters for different URL types.

Provides protocol-based adapters for fetching evidence from
various sources (generic web, YouTube, etc.).
"""

from typing import Dict, Any, Protocol
from ..fetch import fetcher
from ..extract import extract_content, create_snippets
from ...schemas.evidence import EvidencePack, EvidenceSource, EvidenceSnippet
from datetime import datetime

class Adapter(Protocol):
    def fetch_evidence(self, url: str) -> EvidencePack:
        ...

class GenericAdapter:
    def fetch_evidence(self, url: str) -> EvidencePack:
        try:
            html = fetcher.fetch_url(url)
            data = extract_content(html, url)
            text = data["text"]
            
            snippets_data = create_snippets(text, url)
            snippets = [EvidenceSnippet(**s) for s in snippets_data]
            
            return EvidencePack(
                sources=[EvidenceSource(url=url, title="Web Page", fetched_at=datetime.isoformat(datetime.now()))],
                snippets=snippets,
                coverage="full" if snippets else "failed"
            )
        except Exception as e:
            return EvidencePack(
                sources=[EvidenceSource(url=url, fetched_at=datetime.isoformat(datetime.now()))],
                snippets=[],
                coverage="failed",
                errors=[str(e)]
            )

def get_adapter(url: str):
    # Simple router
    if "github.com" in url:
        from .github import GithubAdapter
        return GithubAdapter()
    if "arxiv.org" in url:
        from .arxiv import ArxivAdapter
        return ArxivAdapter()
    return GenericAdapter()
