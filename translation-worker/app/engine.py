"""
Translation engine: NLLB-200-distilled-600M converted to the CTranslate2
format (int8), tokenized with SentencePiece.

NLLB is a multilingual model: a single set of weights serves all
directions, the source/target language being carried by code tokens
(fra_Latn, eng_Latn...). It replaces the small bilingual OPUS-MT models
(2018) whose translations were too literal on idioms.
"""

import logging
import os
import re

from app.config import settings

logger = logging.getLogger(__name__)

# Single model shared by all directions (multilingual).
NLLB_REPO = "JustFrederik/nllb-200-distilled-600M-ct2-int8"

# One repo per direction (same underlying model): since the HuggingFace
# cache is shared, downloading a second direction is instantaneous.
DIRECTION_REPOS = {
    "fr-en": NLLB_REPO,
    "en-fr": NLLB_REPO,
}

# NLLB language tokens per direction.
LANGUAGE_CODES = {
    "fr-en": ("fra_Latn", "eng_Latn"),
    "en-fr": ("eng_Latn", "fra_Latn"),
}

# Required files: CT2 weights + CT2 vocabulary + SentencePiece tokenizer.
ALLOW_PATTERNS = [
    "model.bin",
    "config.json",
    "shared_vocabulary.txt",
    "sentencepiece.bpe.model",
]

# Translation models are limited in source positions (512 for OPUS-MT,
# 1024 for NLLB): long texts are split into chunks of at most
# max_source_tokens tokens, at sentence boundaries.
DEFAULT_MAX_SOURCE_TOKENS = 500

# A text chunk under ~1200 characters is under 500 tokens in almost all
# cases: this threshold avoids tokenizing whole texts just to measure
# their length (slow, and the source of "sequence length is longer than
# the specified maximum" warnings).
_SOFT_CHAR_LIMIT = 1200

# Separator ladder to split without cutting sentences at random: first
# sentences, then clauses, then enumerations, then words. Token-level
# splitting (inside a word) only happens as a last pathological resort
# (a single "word" longer than _SOFT_CHAR_LIMIT characters).
_BOUNDARY_LEVELS = [
    re.compile(r"(?<=[.!?…])\s+"),
    re.compile(r"(?<=[;:])\s+"),
    re.compile(r"(?<=[,])\s+"),
    re.compile(r"\s+"),
]


class JobCancelled(Exception):
    """Raised when cancellation is requested during translation."""


class TranslationEngine:
    """CTranslate2 + SentencePiece wrapper for a given direction."""

    def __init__(self, direction: str, model_path: str, compute_type: str = None,
                 max_batch_size: int = None):
        import ctranslate2
        import sentencepiece as spm

        self._source_code, self._target_code = LANGUAGE_CODES[direction]
        self._sp = spm.SentencePieceProcessor()
        self._sp.Load(os.path.join(model_path, "sentencepiece.bpe.model"))
        self._translator = ctranslate2.Translator(
            model_path,
            device="cpu",
            compute_type=compute_type or settings.translation_compute_type,
        )
        self.max_batch_size = max_batch_size or settings.translation_batch_size
        self.max_source_tokens = DEFAULT_MAX_SOURCE_TOKENS

    # -- tokenization (narrow entry points, easy to stub in tests)

    def _tokenize(self, text: str) -> list:
        return self._sp.encode(text, out_type=str)

    def _detokenize(self, pieces: list) -> str:
        return self._sp.DecodePieces(pieces)

    def _token_length(self, text: str) -> int:
        return len(self._tokenize(text))

    # -- API publique

    def translate(self, texts: list, should_continue=None) -> list:
        """
        Translates a list of texts while preserving layout (line breaks,
        leading/trailing spaces on a line). `should_continue` is consulted
        between each sentence batch and raises JobCancelled if the job
        cancellation was requested in the meantime.
        """
        # 1. Split by lines then sentences: text blocks are translated,
        #    separators (\n+) and spaces are reinserted verbatim.
        structures = []
        all_chunks = []  # all chunks (sentences), flattened
        for text in texts:
            structure = []
            for part in re.split(r"(\n+)", text):
                if not part:
                    continue
                core = part.strip()
                if not core:
                    structure.append(("raw", part))
                    continue
                leading = part[: len(part) - len(part.lstrip())]
                trailing = part[len(part.rstrip()):]
                chunks = self._chunk_text(core)
                structure.append(("text", leading, chunks, trailing))
                all_chunks.extend(chunks)
            structures.append(structure)

        # 2. Translate all chunks in batches of max_batch_size sentences
        #    (fine granularity: a cancellation is detected quickly).
        translated_chunks = []
        for start in range(0, len(all_chunks), self.max_batch_size):
            if should_continue is not None and start > 0:
                should_continue()
            translated_chunks.extend(
                self._translate_chunks(all_chunks[start : start + self.max_batch_size])
            )

        # 3. Reassembly: chunks -> blocks -> texts, with the original
        #    layout.
        it = iter(translated_chunks)
        results = []
        for structure in structures:
            out = []
            for element in structure:
                if element[0] == "raw":
                    out.append(element[1])
                else:
                    _, leading, chunks, trailing = element
                    out.append(leading + " ".join(next(it) for _ in chunks) + trailing)
            results.append("".join(out))
        return results

    def _translate_chunks(self, chunks: list) -> list:
        """Translates a list of chunks (one sentence each) in a single
        translate_batch call."""
        flat_tokens = []
        flat_prefixes = []
        for chunk in chunks:
            # NLLB/CTranslate2 convention: source language code first and
            # EOS ("</s>") at the end of the input; the target language is
            # provided via target_prefix (not inside the input).
            flat_tokens.append([self._source_code] + self._tokenize(chunk) + ["</s>"])
            flat_prefixes.append([self._target_code])

        results = self._translator.translate_batch(flat_tokens, target_prefix=flat_prefixes)

        outputs = []
        for result in results:
            hypothesis = result.hypotheses[0]
            # The output starts with the target language code: skip it.
            if hypothesis and hypothesis[0] == self._target_code:
                hypothesis = hypothesis[1:]
            outputs.append(self._detokenize(hypothesis))
        return outputs

    # -- splitting blocks that are too long for the model

    def _split_pieces(self, text: str, level: int = 0) -> list:
        """Recursive split along the separator ladder, never tokenizing a
        long text: only short pieces (<= _SOFT_CHAR_LIMIT characters) are
        produced, except on the pathological path."""
        if level >= len(_BOUNDARY_LEVELS):
            return [text] if text else []
        pieces = []
        for part in _BOUNDARY_LEVELS[level].split(text):
            if not part:
                continue
            if len(part) <= _SOFT_CHAR_LIMIT:
                pieces.append(part)
            else:
                pieces.extend(self._split_pieces(part, level + 1))
        return pieces

    def _chunk_text(self, text: str) -> list:
        """
        Splits a block (no line break) into chunks translated separately:
        one sentence per chunk (NLLB-like models drop whole sentences
        when fed several at once), an overly long sentence being itself
        split along the separator ladder then into tokens.
        """
        if len(text) <= _SOFT_CHAR_LIMIT and self._token_length(text) <= self.max_source_tokens:
            # Single short sentence: one chunk, no re-tokenization.
            if _BOUNDARY_LEVELS[0].search(text) is None or not text.strip():
                return [text]

        chunks = []
        for piece in self._split_pieces(text):
            if not piece.strip():
                continue
            piece_len = self._token_length(piece)
            if piece_len > self.max_source_tokens:
                # Atomic piece still too long (no separator at all):
                # token-level split, last resort.
                pieces = self._tokenize(piece)
                for index in range(0, len(pieces), self.max_source_tokens):
                    chunks.append(
                        self._detokenize(pieces[index : index + self.max_source_tokens])
                    )
            else:
                chunks.append(piece)
        return chunks

