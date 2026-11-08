"""
tests.test_web_home_voice
===========================

Talking to MIA on the PC (DEC-0125): the desktop window lets her own page
use the microphone for Talk's mic, and nothing else: no other site, no
camera. Talk's mic and the shared recorder live in web/shell.js.
"""

from pathlib import Path

from modules.web_home.module import grants_microphone

LOCAL = "http://127.0.0.1:8765"


def test_her_own_page_may_use_the_microphone():
    """The local server's page, asking to hear."""
    assert grants_microphone("http://127.0.0.1:8765", LOCAL, "audio")
    assert grants_microphone("http://127.0.0.1:8765/", LOCAL, "audio")


def test_another_site_or_port_is_never_given_the_microphone():
    """A page her browser or a link opened elsewhere is turned down."""
    assert not grants_microphone("https://example.com", LOCAL, "audio")
    assert not grants_microphone("http://127.0.0.1:9000", LOCAL, "audio")
    assert not grants_microphone("http://127.0.0.1:8765", "", "audio")


def test_the_camera_and_anything_else_are_turned_down_even_for_her_page():
    """Only hearing."""
    assert not grants_microphone("http://127.0.0.1:8765", LOCAL, "other")


def test_talk_on_every_page_has_a_mic_that_sends_her_voice_path():
    """The shared frame's Talk form carries the mic, recording with the shared recorder and sending MIA.voice."""
    shell = (Path(__file__).resolve().parent.parent / "web" / "shell.js").read_text(encoding="utf-8")
    assert "talk-mic" in shell and "voiceRecorder()" in shell and "MIA.voice(audio)" in shell
    # the mic sits between the box (and the Look eye, DEC-0129) and Send
    assert "input, mic, el(\"button\"" in shell or "input, look, mic, el(\"button\"" in shell
