import trafilatura
from typing import List, Dict, Any
from ..schemas.evidence import EvidenceSnippet

# Simple snippet generator
def create_snippets(text: str, source_url: str, max_snippets: int = 12) -> List[Dict[str, Any]]:
    """
    Splits text into chunks (naive sentence/paragraph split for POC).
    Returns list of dicts matching EvidenceSnippet structure (roughly).
    """
    if not text:
        return []
    
    # Trafilatura usually returns clean paragraphs separated by newlines.
    paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
    
    snippets = []
    for i, p in enumerate(paragraphs):
        if i >= max_snippets:
            break
        # Naive truncation
        content = p[:500] 
        snippets.append({
            "id": i + 1,
            "content": content,
            "source_url": source_url
        })
        
    return snippets

def extract_content(html: str, url: str) -> Dict[str, Any]:
    """
    Extracts main text from HTML.
    Returns dict with 'text', 'title', etc.
    """
    # use trafilatura
    extracted = trafilatura.extract(html, include_comments=False, include_tables=True, url=url)
    # trafilatura doesn't always give title easily if allow_duplicates=False etc.
    # We can try barebones extractMetadata if needed, but 'extracted' is just the string.
    
    return {
        "text": extracted or "",
        "url": url
    }
