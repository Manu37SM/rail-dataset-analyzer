from normalizer import normalize_name


def test_lowercases_and_strips_whitespace():
    assert normalize_name("  NEW DELHI  ") == "new delhi"


def test_applies_city_rename_replacements():
    assert normalize_name("Bombay Central") == "mumbai central"
    assert normalize_name("Madras Central") == "chennai central"
    assert normalize_name("Bangalore City") == "bengaluru city"
    assert normalize_name("Calcutta") == "kolkata"


def test_expands_junction_abbreviation():
    assert normalize_name("Mathura Jn") == "mathura junction"


def test_removes_text_in_brackets():
    assert normalize_name("New Delhi (NDLS)") == "new delhi"


def test_removes_punctuation():
    assert normalize_name("St. Thomas, Mount") == "st thomas mount"


def test_collapses_repeated_whitespace():
    assert normalize_name("New    Delhi") == "new delhi"


def test_empty_or_falsy_input_returns_empty_string():
    assert normalize_name("") == ""
    assert normalize_name(None) == ""
