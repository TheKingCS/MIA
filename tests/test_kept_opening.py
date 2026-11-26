"""
tests.test_kept_opening
=========================

A library answer trimmed of figures the text didn't give keeps the trim only with its first sentence (core/tool_loop
.kept_its_opening, the live sweep 2026-11-26: the potato answer was left starting "This allows...").
"""

from core import tool_loop


def test_a_trim_that_took_the_opening_is_not_kept():
    said = "Plant them about 4 inches deep. This allows the tubers to form. Hill them as they grow."
    assert not tool_loop.kept_its_opening(said, "This allows the tubers to form. Hill them as they grow.")
    assert tool_loop.kept_its_opening(said, "Plant them about 4 inches deep. Hill them as they grow.")


def test_the_librarys_general_guidance_words_are_the_ones_it_says():
    """The marker the loop reads is the library's own wording for having nothing."""
    import inspect

    from core import assistant_tools, offline_library  # noqa: F401

    sources = "".join(inspect.getsource(m) for m in (assistant_tools,))
    try:
        sources += inspect.getsource(offline_library)
    except Exception:  # noqa: BLE001
        pass
    assert tool_loop.GENERAL_GUIDANCE in sources
