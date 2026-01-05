from . import GenericAdapter
from ...schemas.evidence import EvidencePack, EvidenceSource, EvidenceSnippet, EvidencePack
from ..fetch import fetcher
from datetime import datetime

class GithubAdapter:
    def fetch_evidence(self, url: str) -> EvidencePack:
        # POC: Just try to fetch the README. Usually main branch.
        # Clean URL -> raw content URL? 
        # Or just use GenericAdapter which scrapes the HTML of the repo page?
        # Creating a proper API fetch is better but scraping is often surprisingly effective for READMEs.
        # Let's try GenericAdapter logic first but maybe strip UI elements if we were advanced.
        # For POC, let's just use GenericAdapter behavior but labeled as Github.
        
        # Real improvement: Convert github.com/user/repo -> raw.githubusercontent.com/user/repo/main/README.md
        # But branch name is unknown. 'master' or 'main'. 
        # Let's just scrape the repo page. Trafilatura usually gets the README content well.
        
        adapter = GenericAdapter()
        pack = adapter.fetch_evidence(url)
        # Maybe adjust title or coverage label
        return pack
