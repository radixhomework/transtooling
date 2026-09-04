from dataclasses import dataclass

from app.vtt import segments_to_vtt


@dataclass
class FakeSegment:
    """Simule un segment retourné par faster-whisper (start, end, text)."""
    start: float
    end: float
    text: str


def test_segments_to_vtt_basic_structure():
    segments = [
        FakeSegment(start=0.0, end=2.5, text="Bonjour tout le monde."),
        FakeSegment(start=2.5, end=5.0, text="Ceci est un test."),
    ]
    vtt = segments_to_vtt(segments)

    assert vtt.startswith("WEBVTT\n\n")
    assert "00:00:00.000 --> 00:00:02.500" in vtt
    assert "00:00:02.500 --> 00:00:05.000" in vtt
    assert "Bonjour tout le monde." in vtt
    assert "Ceci est un test." in vtt


def test_segments_to_vtt_applies_text_cleanup():
    segments = [FakeSegment(start=0.0, end=1.0, text="  bonjour   ,  le monde  ")]
    vtt = segments_to_vtt(segments)
    assert "Bonjour, le monde" in vtt


def test_segments_to_vtt_skips_empty_segments():
    segments = [
        FakeSegment(start=0.0, end=1.0, text="   "),
        FakeSegment(start=1.0, end=2.0, text="Texte valide."),
    ]
    vtt = segments_to_vtt(segments)
    assert vtt.count("-->") == 1
    assert "Texte valide." in vtt


def test_segments_to_vtt_empty_list():
    vtt = segments_to_vtt([])
    assert vtt == "WEBVTT\n"


def test_segments_to_vtt_timestamp_format_hours():
    segments = [FakeSegment(start=3661.25, end=3665.0, text="Test.")]
    vtt = segments_to_vtt(segments)
    # 3661.25s = 1h01m01.250s
    assert "01:01:01.250" in vtt
