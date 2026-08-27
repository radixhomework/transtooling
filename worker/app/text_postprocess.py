"""
Post-traitement du texte issu de faster-whisper.

faster-whisper produit déjà une ponctuation de base correcte pour le français
(via son modèle), mais le texte brut segmenté peut contenir :
- des espaces superflus ou doublés
- des espaces avant la ponctuation (héritage de la tokenisation)
- une absence de majuscule en début de segment
- une absence de point final sur le dernier segment

Ce module effectue un nettoyage léger, non intrusif : il ne réécrit pas le
contenu (aucune reformulation), il normalise uniquement la forme.
"""

import re


def clean_segment_text(text: str) -> str:
    """Nettoie le texte d'un segment individuel (espaces, ponctuation)."""
    text = text.strip()
    # Supprime les espaces multiples
    text = re.sub(r"\s+", " ", text)
    # Supprime les espaces avant une ponctuation simple (. , ! ?)
    # NB : le français utilise une espace insécable avant : ; ! ? mais on
    # reste ici sur une espace normale pour rester cohérent avec un affichage
    # web basique ; ajuster si une typographie française stricte est requise.
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
    """Applique l'ensemble des règles de nettoyage à un segment."""
    text = clean_segment_text(text)
    text = capitalize_first_letter(text)
    return text


def postprocess_full_transcript(segments_text: list[str]) -> str:
    """
    Assemble les segments nettoyés en un texte continu, avec ponctuation
    finale garantie sur le dernier segment. Utilisé pour un éventuel export
    texte brut en plus du .vtt (segments conservés séparément dans le VTT).
    """
    cleaned = [postprocess_segment_text(t) for t in segments_text if t.strip()]
    if cleaned:
        cleaned[-1] = ensure_terminal_punctuation(cleaned[-1])
    return " ".join(cleaned)
