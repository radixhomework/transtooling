"""
Post-processing of faster-whisper output text.

faster-whisper already produces decent base punctuation for French (through
its model), but the raw segmented text can contain:
- extra or doubled spaces
- spaces before punctuation (a tokenization leftover)
- a missing capital at the start of a segment
- a missing final period on the last segment

This module performs light, non-intrusive cleanup: it does not rewrite
content (no rephrasing), it only normalizes form.
"""

import re


def clean_segment_text(text: str) -> str:
    """Cleans an individual segment's text (spaces, punctuation)."""
    text = text.strip()
    # Removes multiple spaces
    text = re.sub(r"\s+", " ", text)
    # Removes spaces before simple punctuation (. , ! ?)
    # NB: French uses a non-breaking space before : ; ! ? but we keep a
    # regular space here to stay consistent with basic web display;
    # adjust if strict French typography is required.
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    return text


def capitalize_first_letter(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def ensure_terminal_punctuation(text: str) -> str:
    if not text:
        return text
    if text[-1] not in ".!?":
        return text + "."
    return text


def postprocess_segment_text(text: str) -> str:
    """Applies the full set of cleanup rules to a segment."""
    text = clean_segment_text(text)
    text = capitalize_first_letter(text)
    return text


def postprocess_full_transcript(segments_text: list[str]) -> str:
    """
    Assembles the cleaned segments into continuous text, with terminal
    punctuation guaranteed on the last segment. Used for a possible plain
    text export in addition to the .vtt (segments kept separate in VTT).
    """
    cleaned = [postprocess_segment_text(t) for t in segments_text if t.strip()]
    if cleaned:
        cleaned[-1] = ensure_terminal_punctuation(cleaned[-1])
    return " ".join(cleaned)
