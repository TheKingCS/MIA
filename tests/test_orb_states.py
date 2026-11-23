"""
tests.test_orb_states
=======================

WP-07 (REQ-VIS-009, REQ-VIS-010, DEC-0255): every state the orb can show has its own words and its own still glyph,
and its own style on the page; with reduced motion the page shows the glyph and the words; "offline" comes only from
the model really not answering, and the next answer clears it; "speaking" only while her reply really plays.
"""
import re
from pathlib import Path

import pytest

from core import orb_state

ROOT = Path(__file__).resolve().parent.parent
EVERY = set(orb_state.PRIORITY) | set(orb_state.PAGE_STATES) | {"idle"}


def test_every_state_has_its_own_words_and_its_own_still_glyph():
    """REQ-VIS-009: a label for each, none shared; a glyph for each, none shared."""
    assert set(orb_state.LOOK) == EVERY
    labels = [label for label, _ in orb_state.LOOK.values()]
    glyphs = [glyph for _, glyph in orb_state.LOOK.values()]
    assert all(labels) and len(set(labels)) == len(labels)
    assert all(glyphs) and len(set(glyphs)) == len(glyphs)
    assert orb_state.look()["offline"]["label"].startswith("Offline")


@pytest.mark.parametrize("state", sorted(EVERY - {"idle"}))
def test_each_state_has_its_own_style_on_the_orb(state):
    """One test per state (REQ-VIS-009): the orb's style sheet draws it differently from idle."""
    css = (ROOT / "web" / "ui.css").read_text(encoding="utf-8")
    assert re.search(r'\.mia-orb\[data-state="' + state + r'"\]', css), state


def test_reduced_motion_shows_the_glyph_and_the_words():
    """REQ-VIS-010: under reduced motion the orb's movement stops and its glyph and words are shown."""
    css = (ROOT / "web" / "ui.css").read_text(encoding="utf-8")
    block = css[css.index("@media (prefers-reduced-motion: reduce) {\n  .mia-orb, .skeleton"):]
    block = block[:block.index("\n}\n")]
    assert "animation: none" in block and "attr(data-glyph)" in block and "attr(data-label)" in block
    shell = (ROOT / "web" / "shell.js").read_text(encoding="utf-8")
    assert "o.dataset.glyph = look.glyph" in shell and "o.dataset.label = look.label" in shell


def test_offline_is_held_while_the_model_doesnt_answer_and_cleared_by_an_answer():
    """DEC-0255: only a real failure to reach the model shows offline; the next answer clears it."""
    from core.llm_manager import LLMManager, LLMUnavailableError

    class Backend:
        """A model server that's down until told otherwise."""
        up = False

        def is_available(self, timeout):
            """Whether it answers."""
            return self.up

        def generate(self, prompt, timeout=None):
            """An answer, or unavailable."""
            if not self.up:
                raise LLMUnavailableError("down")
            return "hello"

    backend = Backend()
    manager = LLMManager.__new__(LLMManager)
    manager._backend, manager._timeout, manager.home = backend, 1.0, None
    manager._ask = lambda call: call(backend)
    assert not manager.is_available() and orb_state.current() == "offline"
    backend.up = True
    assert manager.generate("hi") == "hello" and orb_state.current() == "idle"
    backend.up = False
    assert manager.generate("hi") is None and orb_state.current() == "offline"
    with orb_state.active("thinking"):
        assert orb_state.current() == "thinking"  # doing something outranks waiting to wake


def test_a_condition_that_isnt_one_is_ignored_and_only_a_change_moves_the_version():
    """hold() never raises, and holding what's already held doesn't wake every page."""
    orb_state.hold("not-a-state", True)
    assert orb_state.current() == "idle"
    orb_state.hold("offline", True)
    before = orb_state.version()
    orb_state.hold("offline", True)
    assert orb_state.version() == before


def test_speaking_comes_only_from_her_reply_really_playing():
    """The page says speaking when the reply's audio is playing, and stops when it ends, pauses (he cut in) or
    fails; cutting her off ends the speaking state itself, and a reply asked before he cut in is never played."""
    shell = (ROOT / "web" / "shell.js").read_text(encoding="utf-8")
    start = shell.index("function playReply(turn, hooks, epoch)")
    body = shell[start:shell.index("\n  }\n", start)]
    assert 'addEventListener("playing", () => { presenceHere("speaking");' in body
    assert all(f'addEventListener("{e}", done)' in body for e in ("ended", "pause", "error"))
    # cut off by him: stopSpeaking ends the speaking state itself, and a stale reply is never played
    stop = shell[shell.index("function stopSpeaking()"):start]
    assert 'if (presenceLocal === "speaking") presenceHere("");' in stop
    assert "epoch !== voiceEpoch) return null" in body


def test_the_frame_carries_the_orbs_words_for_every_page():
    """Every page's orb says the same: the frame's data holds the look."""
    from core.web_surfaces import _orb_look

    assert _orb_look() == orb_state.look()


def test_needs_you_shows_while_a_card_waits_and_stops_once_it_is_decided_or_expired(monkeypatch):
    """The orb spec's "Needs you": only a real card waiting for a yes, from seconds old (not a press's own card);
    approved, rejected or past its day, it stops."""
    from datetime import datetime, timedelta
    from types import SimpleNamespace

    from core import actions

    monkeypatch.setitem(actions.ACTION_TYPES, "zz.ok", actions.ActionType(
        "zz.ok", "Ok", {}, lambda c, p: "Do it", lambda c, p: "Done."))
    center = actions.ActionCenter()
    context = SimpleNamespace(config=None, undo=None, events=None, failures=None)
    first = center.propose(context, "zz.ok")
    assert orb_state.current() != "needs-you"  # a moment old: a press's own propose-then-approve
    first.created_at = (datetime.now() - timedelta(minutes=1)).isoformat(timespec="seconds")
    assert orb_state.current() == "needs-you"
    center.approve(context, first.proposal_id)
    assert orb_state.current() != "needs-you"
    second = center.propose(context, "zz.ok")
    center.reject(context, second.proposal_id)
    assert orb_state.current() != "needs-you"
    third = center.propose(context, "zz.ok")
    third.created_at = (datetime.now() - actions.KEEP_FOR - timedelta(minutes=1)).isoformat(timespec="seconds")
    assert orb_state.current() != "needs-you"
