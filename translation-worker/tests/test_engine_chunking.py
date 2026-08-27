"""Tests du moteur : découpe des textes longs (échelle de séparateurs),
préservation de la mise en page, annulation entre lots."""

import pytest

from app.engine import JobCancelled, TranslationEngine


class _IdentityResult:
    def __init__(self, tokens):
        self.hypotheses = [tokens]


class _IdentityTranslator:
    """Simule CTranslate2 : renvoie les jetons tels quels (hors code source
    et EOS d'entrée), en préfixant la sortie par le code cible."""

    def translate_batch(self, token_lists, target_prefix=None):
        prefixes = target_prefix or [[] for _ in token_lists]
        outs = []
        for tokens, prefix in zip(token_lists, prefixes):
            body = tokens[1:-1]  # sans le code source ni l'EOS
            outs.append(_IdentityResult(list(prefix) + body))
        return outs


def make_engine(max_source_tokens=10):
    # __new__ pour contourner __init__ (pas de modèle réel requis) ; les
    # points d'entrée de tokenisation sont remplacés par des stubs simples
    # (1 jeton par mot).
    engine = TranslationEngine.__new__(TranslationEngine)
    engine._tokenize = lambda text: text.split(" ")
    engine._detokenize = lambda pieces: " ".join(pieces)
    engine._translator = _IdentityTranslator()
    engine._source_code = "SRC"
    engine._target_code = "TGT"
    engine.max_source_tokens = max_source_tokens
    engine.max_batch_size = 4
    return engine


# --- découpe des textes longs ---


def test_short_text_single_chunk():
    engine = make_engine(max_source_tokens=10)
    assert engine._chunk_text("un deux trois") == ["un deux trois"]


def test_long_text_split_one_sentence_per_chunk():
    engine = make_engine(max_source_tokens=10)
    text = " ".join(f"mot{i}." for i in range(25))  # 25 phrases de 1 mot
    chunks = engine._chunk_text(text)
    # Une phrase par morceau (les modèles type NLLB perdent des phrases
    # quand on en fournit plusieurs d'un coup).
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
    # Aucun mot coupé : tous les mots d'origine sont retrouvés intacts.
    words = {w for c in chunks for w in c.split()}
    assert len(words) == 20


def test_mixed_long_sentence_falls_through_separator_ladder():
    engine = make_engine(max_source_tokens=6)
    # Une « phrase » très longue avec des virgules : coupée aux virgules
    # plutôt qu'au milieu d'un mot.
    text = "a, " * 30 + "fin."
    chunks = engine._chunk_text(text)
    assert all(len(c.split()) <= 6 for c in chunks)
    assert "fin." in chunks[-1]


# --- préservation de la mise en page ---


def test_translate_preserves_line_breaks_and_indentation():
    engine = make_engine()
    text = "Hello world.\n\n\n  Indented line here.\nLast line."
    # Translation identité (morceaux renvoyés tels quels) : on vérifie la
    # structure (sauts de ligne, indentation) réinsérée telle quelle.
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


# --- annulation entre les lots ---


def test_translate_checks_should_continue_between_batches():
    engine = make_engine(max_source_tokens=50)
    engine.max_batch_size = 1
    calls = []

    def should_continue():
        calls.append(1)
        raise JobCancelled()

    with pytest.raises(JobCancelled):
        engine.translate(["a", "b", "c"], should_continue=should_continue)
    # Le premier lot part sans contrôle, l'annulation est vue avant le 2e.
    assert len(calls) == 1
