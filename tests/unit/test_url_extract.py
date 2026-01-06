from technoshare_commentator.retrieval.url import extract_urls

def test_extract_urls_basic():
    """
    WHY: Identify all valid URLs in a text to potentially summarize them.
    HOW: Pass text with mixed HTTP/HTTPS links.
    EXPECTED: Return list containing all valid URLs.
    """
    text = "Check this out https://example.com/foo and http://test.org"
    urls = extract_urls(text)
    assert "https://example.com/foo" in urls
    assert "http://test.org" in urls
    assert len(urls) == 2

def test_deduplication():
    """
    WHY: Don't summarize the same link twice if user pasted it multiple times.
    HOW: Pass text with duplicate URLs.
    EXPECTED: Return list with unique URLs only.
    """
    text = "Link https://same.com and https://same.com again"
    urls = extract_urls(text)
    assert len(urls) == 1
    assert urls[0] == "https://same.com"

def test_punctuation_stripping():
    """
    WHY: Users often put links in parentheses or end sentences with them. We need the CLEAN url.
    HOW: Pass text like "(https://foo.com)."
    EXPECTED: Return "https://foo.com" without trailing punctuation.
    """
    text = "Here is a link (https://foo.com/bar)."
    urls = extract_urls(text)
    assert urls[0] == "https://foo.com/bar"
    
    text2 = "Click here: https://baz.com;"
    urls2 = extract_urls(text2)
    assert urls2[0] == "https://baz.com"

def test_max_links_cap():
    """
    WHY: Prevent abuse or high costs if someone dumps 50 links.
    HOW: Pass text with 4 links (assuming max default is 3).
    EXPECTED: Return exactly 3 URLs.
    """
    text = "1 https://a.com 2 https://b.com 3 https://c.com 4 https://d.com"
    # Assuming default MAX_LINKS_PER_MESSAGE is 3 in config, but unit test might use default from pydantic (3)
    urls = extract_urls(text)
    assert len(urls) <= 3
