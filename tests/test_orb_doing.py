"""
tests.test_orb_doing
======================

What her orb says she's doing while a lookup runs (core/orb_state.doing, core/tool_loop.doing_words; brainstorm 1.1):
only while the tool really runs, from its domain, and sent with the state on the live stream.
"""

from types import SimpleNamespace

from core import orb_state, tool_loop


def test_the_words_show_only_while_the_lookup_runs():
    orb_state.reset()
    assert orb_state.detail() == ""
    with orb_state.doing("Reading your library"):
        assert orb_state.detail() == "Reading your library"
        with orb_state.doing("Checking your money"):
            assert orb_state.detail() == "Checking your money"
        assert orb_state.detail() == "Reading your library"
    assert orb_state.detail() == ""


def test_the_words_end_even_when_the_lookup_fails():
    orb_state.reset()
    try:
        with orb_state.doing("Checking your day"):
            raise RuntimeError("broken tool")
    except RuntimeError:
        pass
    assert orb_state.detail() == ""


def test_each_change_moves_the_version_so_the_page_hears_it():
    orb_state.reset()
    before = orb_state.version()
    with orb_state.doing("Looking it up"):
        assert orb_state.version() > before


def test_the_words_come_from_the_tools_domain():
    registry = SimpleNamespace(_actions={"look_up_offline": SimpleNamespace(domain="library"),
                                         "money_ahead": SimpleNamespace(domain="budget"),
                                         "odd": SimpleNamespace(domain="something_new")})
    assert tool_loop.doing_words(registry, "look_up_offline") == "Reading your library"
    assert tool_loop.doing_words(registry, "money_ahead") == "Checking your money"
    assert tool_loop.doing_words(registry, "odd") == "Looking it up"
    assert tool_loop.doing_words(registry, "missing") == "Looking it up"


def test_the_live_stream_and_the_page_carry_the_detail():
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    app = (root / "server" / "app.py").read_text(encoding="utf-8")
    assert "'detail': now_state[1]" in app
    shell = (root / "web" / "shell.js").read_text(encoding="utf-8")
    assert "presenceDetail = (e.detail && e.detail.detail)" in shell
