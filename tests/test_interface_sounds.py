"""
tests.test_interface_sounds
=============================

WP-06 (DEC-0240, REQ-VIS-023, REQ-VIS-026, REQ-VIS-012): interface sounds come from her orb's real changes of state,
each with its visual twin (the orb's state and words), all off with the one sound setting, and never the alarm's;
while a local model generates, auto glass drops to light effects and the ambient drift holds still.
"""
import re
from pathlib import Path

from core import orb_state

WEB = Path(__file__).resolve().parent.parent / "web"
SOUND = (WEB / "sound.js").read_text(encoding="utf-8")
SHELL = (WEB / "shell.js").read_text(encoding="utf-8")


def _cues() -> dict:
    """The state -> tune map in web/sound.js."""
    body = re.search(r"const CUES = \{([^}]*)\}", SOUND).group(1)
    return dict(re.findall(r'"?([\w-]+)"?: "(\w+)"', body))


def test_each_interface_sound_has_its_tune_and_its_visual_twin():
    """Every cue is a tune that exists, for an orb state that has words (core/orb_state.LOOK)."""
    cues = _cues()
    assert cues == {"listening": "listenOn", "needs-you": "needsYou", "warning": "error"}
    for state, tune in cues.items():
        assert re.search(rf"\b{tune}: \(\) =>", SOUND), tune
        assert state in orb_state.LOOK and orb_state.LOOK[state][0]
    assert "listenOff: () =>" in SOUND and 'before === "listening" ? "listenOff"' in SOUND


def test_done_and_message_are_made_but_off_by_default():
    """Q-84: a finished change and a gate message make no sound unless chosen later."""
    off = re.search(r"const OFF_BY_DEFAULT = \{([^}]*)\}", SOUND).group(1)
    assert "done" in off and "message" in off and "success" not in _cues() and "notification" not in _cues()


def test_one_setting_turns_them_all_off_and_the_alarm_is_never_one_of_them():
    """They go through play(), which sound.on stops; nothing here names or replaces an alarm."""
    assert "if (cue) play(cue);" in SOUND and "if (!settings.on || !TUNES[name]) return;" in SOUND
    assert "alarm" not in " ".join(_cues()).lower() and "alarm" not in re.search(
        r"const TUNES = \{.*?\n  \};", SOUND, re.S).group(0).lower()


def test_the_page_sounds_only_real_changes_of_her_state():
    """showPresence passes each state to the sounds; a state that didn't change makes none."""
    assert "MIASound.presence(state)" in SHELL
    assert "if (shown === before) return" in SOUND


def test_while_a_model_generates_auto_glass_goes_light_and_the_drift_holds():
    """REQ-VIS-026 and REQ-VIS-012: thinking or the council marks generating; auto effects go light and come back."""
    assert 'generating(state === "thinking" || state === "council")' in SHELL
    body = SHELL[SHELL.index("function generating(on)"):]
    body = body[:body.index("\n  }\n")]
    assert 'root.dataset.effects = "light"' in body and "effectsBefore" in body and "ambient();" in body
    assert "generating: false" in SHELL
