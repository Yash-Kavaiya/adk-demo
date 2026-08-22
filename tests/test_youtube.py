"""VTT -> timestamped text conversion (pure parsing, no network)."""

from bookforge.tools.youtube import load_transcript_text, vtt_to_text

SAMPLE_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
welcome to this tutorial

00:00:03.000 --> 00:00:05.000
welcome to this tutorial

00:00:05.500 --> 00:00:08.000
today we cover <c>neural</c> networks
"""


def test_vtt_to_text_strips_and_dedupes(tmp_path):
    vtt = tmp_path / "captions.en.vtt"
    vtt.write_text(SAMPLE_VTT, encoding="utf-8")
    out = vtt_to_text(vtt, tmp_path)
    lines = out.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "[00:00:01] welcome to this tutorial"
    # consecutive duplicate cue collapsed
    assert sum("welcome" in line for line in lines) == 1
    assert "[00:00:05] today we cover neural networks" in lines
    # idempotent: second call returns existing file unchanged
    assert vtt_to_text(vtt, tmp_path) == out


def test_load_transcript_text_truncates_middle(tmp_path):
    p = tmp_path / "transcript.txt"
    p.write_text("A" * 1000 + "B" * 1000 + "C" * 1000, encoding="utf-8")
    text = load_transcript_text(p, max_chars=400)
    assert "middle truncated" in text
    assert text.startswith("A" * 100)
    assert text.endswith("C" * 100)
