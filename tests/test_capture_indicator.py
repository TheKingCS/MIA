"""
tests.test_capture_indicator
==============================

REQ-DSK-025 (FW-11): whenever a page of MIA's has the microphone open, the frame shows it, and one press closes it:
Talk's recorder and the guitar check register with the frame's indicator, and its Stop closes every stream.
"""
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
SHELL = (WEB / "shell.js").read_text(encoding="utf-8")


def test_the_recorder_shows_the_microphone_while_it_records_and_lets_go_after():
    """start() registers the capture; a finished or cancelled recording releases it; the frame exposes capture."""
    body = SHELL[SHELL.index("function voiceRecorder(onCancel)"):]
    body = body[:body.index("\n  }\n")]
    assert 'release = capture("microphone", cancel);' in body and body.count("release();") >= 2
    assert "capture };" in SHELL


def test_one_press_on_stop_closes_every_stream_and_the_indicator_goes():
    """Stop calls each capture's own close, then the pill is removed when none is left."""
    body = SHELL[SHELL.index("function drawCapture()"):]
    body = body[:body.index("\n  }\n")]
    assert "c.stop()" in body and "captures.clear()" in body and "capturePill.remove()" in body
    assert '"Stop"' in body and 'role: "status"' in body


def test_the_guitar_check_shows_its_microphone_and_stop_ends_the_take():
    """The few seconds of listening register with the frame, and Stop ends them early."""
    guitar = (WEB / "guitar.js").read_text(encoding="utf-8")
    assert 'MIAShell.capture("microphone"' in guitar and "release();" in guitar
