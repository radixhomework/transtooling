"""Engine tests: long-text splitting (separator ladder), layout
preservation, cancellation between batches."""

import pytest

from app.engine import JobCancelled, TranslationEngine


class _IdentityResult:
    def __init__(self, tokens):
        self.hypotheses = [tokens]


class _IdentityTranslator:
    """Simule CTranslate2 : renvoie les jetons tels quels (hors code source
    and EOS of the input), prefixing the output with the target code."""

    def translate_batch(self, token_lists, target_prefix=None):
        prefixes = target_prefix or [[] for _ in token_lists]
        outs = []
        for tokens, prefix in zip(token_lists, prefixes):
            body = tokens[1:-1]  # sans le code source ni l'EOS
            outs.append(_IdentityResult(list(prefix) + body))
        return outs


def make_engine(max_source_tokens=10):
    # __new__ to bypass __init__ (no real model required); the
    # tokenization entry points are replaced with simple stubs
    # (one token per word).
    engine = TranslationEngine.__new__(TranslationEngine)
    engine._tokenize = lambda text: text.split(" ")
    engine._detokenize = lambda pieces: " ".join(pieces)
    engine._translator = _IdentityTranslator()
    engine._source_code = "SRC"
    engine._target_code = "TGT"
    engine.max_source_tokens = max_source_tokens
    engine.max_batch_size = 4
    return engine


# --- Long-text splitting ---


def test_short_text_single_chunk():
    engine = make_engine(max_source_tokens=10)
    assert engine._chunk_text("un deux trois") == ["un deux trois"]


def test_long_text_split_one_sentence_per_chunk():
    engine = make_engine(max_source_tokens=10)
    text = " ".join(f"mot{i}." for i in range(25))  # 25 phrases de 1 mot
    chunks = engine._chunk_text(text)
    # One sentence per chunk (NLLB-like models drop sentences when fed
    # several at once).
    assert len(chunks) == 25
    assert all(len(c.split()) <= 10 for c in chunks)
    assert " ".join(chunks).count("mot") == 25


def test_text_without_punctuation_split_at_words():
    engine = make_engine(max_source_tokens=5)
    text = " ".join(f"w{i}" for i in range(20))  # aucune ponctuation
    chunks = engine._chunk_text(text)
    assert len(chunks) >= 4
    assert all(len(c.split()) <= 5 for c in chunks)
    assert sum(len(c.split()) for c in chunks) == 20
    # No word cut: all original words are found intact.
    words = {w for c in chunks for w in c.split()}
    assert len(words) == 20


def test_mixed_long_sentence_falls_through_separator_ladder():
    engine = make_engine(max_source_tokens=6)
    # A very long "sentence" with commas: split at the commas
    # rather than in the middle of a word.
    text = "a, " * 30 + "fin."
    chunks = engine._chunk_text(text)
    assert all(len(c.split()) <= 6 for c in chunks)
    assert "fin." in chunks[-1]


# --- Layout preservation ---


def test_translate_preserves_line_breaks_and_indentation():
    engine = make_engine()
    text = "Hello world.\n\n\n  Indented line here.\nLast line."
    # Identity translation (chunks returned as-is): we verify the
    # structure (line breaks, indentation) reinserted verbatim.
    result = engine.translate([text])[0]
    assert result == text


def test_translate_multiple_texts_layout_independent():
    engine = make_engine()
    results = engine.translate(["first block", "second\nblock"])
    assert results[0] == "first block"
    assert results[1] == "second\nblock"


def test_translate_preserves_trailing_spaces():
    engine = make_engine()
    result = engine.translate(["line with trailing   "])[0]
    assert result == "line with trailing   "


# --- Cancellation between batches ---


def test_translate_checks_should_continue_between_batches():
    engine = make_engine(max_source_tokens=50)
    engine.max_batch_size = 1
    calls = []

    def should_continue():
        calls.append(1)
        raise JobCancelled()

    with pytest.raises(JobCancelled):
        engine.translate(["a", "b", "c"], should_continue=should_continue)
    # The first batch goes without a check; cancellation is seen before the 2nd.
    assert len(calls) == 1
