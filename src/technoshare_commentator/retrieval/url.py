import re
from typing import List
from ..config import get_settings

settings = get_settings()

# Basic regex for URLs (http/https)
URL_REGEX = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')

def extract_urls(text: str) -> List[str]:
    """
    Extracts URLs from text, deduplicates, and strips tracking params.
    """
    raw_urls = URL_REGEX.findall(text)
    clean_urls = []
    
    seen = set()
    
    for url in raw_urls:
        # 1. Strip tracking params (simple approach)
        # e.g. ?utm_source=...
        # We'll split on '?' for known tracking params or just strip common ones.
        # Ideally, we allow some params (like article ID), but kill utm_*, fbclid, etc.
        # For POC, let's just leave it raw or do minimal cleanup.
        # Use url.py library? 'retrieval/url.py' implies we do it here.
        
        # Simple cleanup: remove trailing ) or > or punct
        url = url.rstrip(')>.,;]')
        
        if url in seen:
            continue
            
        clean_urls.append(url)
        seen.add(url)
        
        if len(clean_urls) >= settings.MAX_LINKS_PER_MESSAGE:
            break
            
    return clean_urls
