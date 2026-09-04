"""
Moteur de traduction : modèle NLLB-200-distilled-600M converti au format
CTranslate2 (int8), tokenisé par SentencePiece.

NLLB est un modèle multilingue : une seule paire de poids sert toutes les
directions, la langue source/cible étant portée par des jetons de code
(fra_Latn, eng_Latn...). Il remplace les petits modèles OPUS-MT bilingues
(2018) dont les traductions étaient trop littérales sur les idiomes.
"""

import logging
import os
import re

from app.config import settings

logger = logging.getLogger(__name__)

# Modèle unique partagé par toutes les directions (multilingue).
NLLB_REPO = "JustFrederik/nllb-200-distilled-600M-ct2-int8"

# Un dépôt par direction (même modèle sous-jacent) : le cache HuggingFace
# étant partagé, le téléchargement d'une seconde direction est immédiat.
DIRECTION_REPOS = {
    "fr-en": NLLB_REPO,
    "en-fr": NLLB_REPO,
}

# Jetons de langue NLLB par direction.
LANGUAGE_CODES = {
    "fr-en": ("fra_Latn", "eng_Latn"),
    "en-fr": ("eng_Latn", "fra_Latn"),
}

# Fichiers nécessaires : poids CT2 + vocabulaire CT2 + tokenizer SentencePiece.
ALLOW_PATTERNS = [
    "model.bin",
    "config.json",
    "shared_vocabulary.txt",
    "sentencepiece.bpe.model",
]

# Les modèles de traduction sont limités en positions source (512 pour les
# OPUS-MT, 1024 pour NLLB) : on découpe les textes longs en morceaux d'au
# plus max_source_tokens jetons, aux frontières de phrases.
DEFAULT_MAX_SOURCE_TOKENS = 500

# Un morceau de texte de moins de ~1200 caractères fait moins de 500 jetons
# dans la quasi-totalité des cas : ce seuil évite de tokeniser des textes
# entiers juste pour mesurer leur longueur (lent, et source d'avertissements
# « sequence length is longer than the specified maximum »).
_SOFT_CHAR_LIMIT = 1200

# Échelle de séparateurs pour découper sans couper les phrases au hasard :
# d'abord les phrases, puis les propositions, puis les énumérations, puis
# les mots. La coupure en jetons (dans un mot) n'intervient qu'en dernier
# recours pathologique (un « mot » de plus de _SOFT_CHAR_LIMIT caractères).
_BOUNDARY_LEVELS = [
    re.compile(r"(?<=[.!?…])\s+"),
    re.compile(r"(?<=[;:])\s+"),
    re.compile(r"(?<=[,])\s+"),
    re.compile(r"\s+"),
]


class JobCancelled(Exception):
    """Levée quand une annulation est demandée en cours de traduction."""


class TranslationEngine:
    """Enveloppe CTranslate2 + SentencePiece pour une direction donnée."""

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

    # -- tokenisation (points d'entrée étroits, facilement simulables en test)

    def _tokenize(self, text: str) -> list:
        return self._sp.encode(text, out_type=str)

    def _detokenize(self, pieces: list) -> str:
        return self._sp.DecodePieces(pieces)

    def _token_length(self, text: str) -> int:
        return len(self._tokenize(text))

    # -- API publique

    def translate(self, texts: list, should_continue=None) -> list:
        """
        Traduit une liste de textes en préservant la mise en page (sauts de
        ligne, espaces en début/fin de ligne). `should_continue` est consulté
        entre chaque lot de phrases et lève JobCancelled si l'annulation du
        job a été demandée entre-temps.
        """
        # 1. Découpe par lignes puis par phrases : les blocs de texte sont
        #    traduits, les séparateurs (\n+) et espaces réinsérés tels quels.
        structures = []
        all_chunks = []  # tous les morceaux (phrases), à plat
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

        # 2. Traduction de tous les morceaux par lots de max_batch_size
        #    phrases (granularité fine : une annulation est vue rapidement).
        translated_chunks = []
        for start in range(0, len(all_chunks), self.max_batch_size):
            if should_continue is not None and start > 0:
                should_continue()
            translated_chunks.extend(
                self._translate_chunks(all_chunks[start : start + self.max_batch_size])
            )

        # 3. Réassemblage : morceaux -> blocs -> textes, avec la mise en page
        #    d'origine.
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
        """Traduit une liste de morceaux (une phrase chacun) en un seul
        appel translate_batch."""
        flat_tokens = []
        flat_prefixes = []
        for chunk in chunks:
            # Convention NLLB/CTranslate2 : code de langue source en tête
            # et EOS (« </s> ») en fin d'entrée ; la langue cible est
            # fournie via target_prefix (et non dans l'entrée).
            flat_tokens.append([self._source_code] + self._tokenize(chunk) + ["</s>"])
            flat_prefixes.append([self._target_code])

        results = self._translator.translate_batch(flat_tokens, target_prefix=flat_prefixes)

        outputs = []
        for result in results:
            hypothesis = result.hypotheses[0]
            # La sortie commence par le code de langue cible : l'ignorer.
            if hypothesis and hypothesis[0] == self._target_code:
                hypothesis = hypothesis[1:]
            outputs.append(self._detokenize(hypothesis))
        return outputs

    # -- découpe des blocs trop longs pour le modèle

    def _split_pieces(self, text: str, level: int = 0) -> list:
        """Découpe récursive selon l'échelle de séparateurs, sans jamais
        tokeniser un texte long : seuls des morceaux courts (≤ _SOFT_CHAR_LIMIT
        caractères) sont produits, sauf chemin pathologique."""
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
        Découpe un bloc (sans saut de ligne) en morceaux traduits
        séparément : une phrase par morceau (les modèles type NLLB perdent
        des phrases entières quand on leur fournit plusieurs phrases d'un
        coup), une phrase trop longue étant elle-même découpée selon
        l'échelle de séparateurs puis en jetons.
        """
        if len(text) <= _SOFT_CHAR_LIMIT and self._token_length(text) <= self.max_source_tokens:
            # Phrase unique courte : un seul morceau, pas de re-tokenisation.
            if _BOUNDARY_LEVELS[0].search(text) is None or not text.strip():
                return [text]

        chunks = []
        for piece in self._split_pieces(text):
            if not piece.strip():
                continue
            piece_len = self._token_length(piece)
            if piece_len > self.max_source_tokens:
                # Pièce atomique encore trop longue (sans aucun séparateur) :
                # coupe en jetons, dernier recours.
                pieces = self._tokenize(piece)
                for index in range(0, len(pieces), self.max_source_tokens):
                    chunks.append(
                        self._detokenize(pieces[index : index + self.max_source_tokens])
                    )
            else:
                chunks.append(piece)
        return chunks

