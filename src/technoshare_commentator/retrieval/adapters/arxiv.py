from . import GenericAdapter
from ...schemas.evidence import EvidencePack

class ArxivAdapter:
    def fetch_evidence(self, url: str) -> EvidencePack:
        # Abstract is on the main page. Generic scrape works well.
        # If we wanted PDF, we'd need to rewrite URL to /pdf/ and use a PDF parser.
        # POC: abstract only.
        adapter = GenericAdapter()
        return adapter.fetch_evidence(url)
