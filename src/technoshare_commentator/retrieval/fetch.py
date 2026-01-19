"""HTTP fetching with retry logic.

Fetches web content with exponential backoff and user-agent headers.
"""

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from ..config import get_settings
from ..log import get_logger

settings = get_settings()
logger = get_logger("fetch")

class Fetcher:
    def __init__(self):
        self.headers = {
            "User-Agent": "TechnoShareCommentator/1.0 (internal research tool)"
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type(httpx.RequestError)
    )
    def fetch_url(self, url: str) -> str:
        """
        Fetches the content of a URL. Returns text/html content.
        Raises exception on failure after retries.
        """
        # Using sync fetch for simplicity in the worker loop if we want,
        # but httpx is great. Let's use sync .get for now to avoid async complexity in strict sync worker,
        # or just .get().
        with httpx.Client(timeout=15.0, follow_redirects=True, headers=self.headers) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.text

fetcher = Fetcher()
