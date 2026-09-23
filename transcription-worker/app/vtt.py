"""WebVTT generation from faster-whisper segments."""

from app.text_postprocess import postprocess_segment_text


def _format_timestamp(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def segments_to_vtt(segments) -> str:
    """
    Converts faster-whisper segments (with .start, .end, .text) to WebVTT
    content. Each segment's text is cleaned (extra spaces, space before
    punctuation, initial capital) through app.text_postprocess before
    being written.
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
