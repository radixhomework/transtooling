"""Génération de fichiers WebVTT à partir des segments produits par faster-whisper."""

from app.text_postprocess import postprocess_segment_text


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def segments_to_vtt(segments) -> str:
    """
    Convertit les segments faster-whisper (avec .start, .end, .text) en
    contenu WebVTT. Le texte de chaque segment est nettoyé (espaces
    superflus, espace avant ponctuation, majuscule initiale) via
    app.text_postprocess avant d'être écrit.
    """
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = _format_timestamp(segment.start)
        end = _format_timestamp(segment.end)
        text = postprocess_segment_text(segment.text)
        if not text:
            continue
        lines.append(f"{start} --> {end}")
        lines.append(text)
        lines.append("")
    return "\n".join(lines)
