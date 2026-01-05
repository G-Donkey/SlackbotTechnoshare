from technoshare_commentator.quality.sentence import validate_sentence_list

def test_validate_sentence_list_exact_10():
    """
    WHY: Our strict output format requires exactly 10 sentences for consistency.
    HOW: Pass a list of 10 strings.
    EXPECTED: Return True.
    """
    sentences = [f"Sentence {i}" for i in range(10)]
    assert validate_sentence_list(sentences) == True

def test_validate_sentence_list_too_short():
    """
    WHY: Fewer than 10 sentences violates the contract.
    HOW: Pass 9 strings.
    EXPECTED: Return False.
    """
    sentences = [f"Sentence {i}" for i in range(9)]
    assert validate_sentence_list(sentences) == False

def test_validate_sentence_list_too_long():
    """
    WHY: More than 10 sentences violates the contract.
    HOW: Pass 11 strings.
    EXPECTED: Return False.
    """
    sentences = [f"Sentence {i}" for i in range(11)]
    assert validate_sentence_list(sentences) == False

def test_validate_sentence_list_empty_strings():
    """
    WHY: Empty strings are not valid sentences and indicate generation failure.
    HOW: Pass 10 items but one is an empty string.
    EXPECTED: Return False.
    """
    sentences = [f"Sentence {i}" for i in range(9)] + [""] # 10 items but one empty
    assert validate_sentence_list(sentences) == False
