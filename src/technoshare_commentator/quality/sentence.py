from typing import List

def count_sentences_naive(text: str) -> int:
    """
    Naive sentence counter. 
    Assumes list of strings is passed usually, so this is just helper if we get raw text.
    """
    if not text:
        return 0
    # Split by period space/newline
    # This is fragile for arbitrary text, but for our 'list of strings' input it's unused.
    # If we need to validate a single string block:
    import re
    sentences = re.split(r'[.!?]+', text)
    return len([s for s in sentences if s.strip()])

def validate_sentence_list(sentences: List[str]) -> bool:
    """
    Checks if list is exactly 10 items and none are empty.
    """
    if len(sentences) != 10:
        return False
    return all(len(s.strip()) > 10 for s in sentences) # Min length sanity check
