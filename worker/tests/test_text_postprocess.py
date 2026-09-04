from app.text_postprocess import (
    capitalize_first_letter,
    clean_segment_text,
    ensure_terminal_punctuation,
    postprocess_full_transcript,
    postprocess_segment_text,
)


def test_clean_segment_text_collapses_multiple_spaces():
    assert clean_segment_text("bonjour   le    monde") == "bonjour le monde"


def test_clean_segment_text_strips_leading_trailing_spaces():
    assert clean_segment_text("  bonjour le monde  ") == "bonjour le monde"


def test_clean_segment_text_removes_space_before_punctuation():
    assert clean_segment_text("bonjour , le monde !") == "bonjour, le monde!"


def test_capitalize_first_letter():
    assert capitalize_first_letter("bonjour") == "Bonjour"
    assert capitalize_first_letter("") == ""


def test_capitalize_first_letter_already_uppercase():
    assert capitalize_first_letter("Bonjour") == "Bonjour"


def test_ensure_terminal_punctuation_adds_period():
    assert ensure_terminal_punctuation("bonjour le monde") == "bonjour le monde."


def test_ensure_terminal_punctuation_keeps_existing_punctuation():
    assert ensure_terminal_punctuation("bonjour le monde !") == "bonjour le monde !"
    assert ensure_terminal_punctuation("comment ça va ?") == "comment ça va ?"


def test_ensure_terminal_punctuation_empty_string():
    assert ensure_terminal_punctuation("") == ""


def test_postprocess_segment_text_full_pipeline():
    raw = "  bonjour   ,  comment allez-vous  "
    assert postprocess_segment_text(raw) == "Bonjour, comment allez-vous"


def test_postprocess_full_transcript_joins_segments():
    segments = ["bonjour", "comment allez-vous", "très bien merci"]
    result = postprocess_full_transcript(segments)
    assert result == "Bonjour Comment allez-vous Très bien merci."


def test_postprocess_full_transcript_ignores_empty_segments():
    segments = ["bonjour", "  ", "", "au revoir"]
    result = postprocess_full_transcript(segments)
    assert result == "Bonjour Au revoir."


def test_postprocess_full_transcript_empty_list():
    assert postprocess_full_transcript([]) == ""
