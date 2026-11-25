"""
tests.test_sweep_13
=====================

The seventh live sweep's fixes (2026-11-25): an answer never says the same paragraph or sentence twice ("The project
you're planning: goats" had come five times over), and the project picture speaks to him, never of him.
"""

from core.response_composer import polish, without_repeats


def test_a_paragraph_said_again_is_said_once():
    line = "The project you're planning: goats. It touches: money, materials, time, goals."
    assert without_repeats("\n\n".join([line] * 5)) == line
    assert polish(f"{line} {line}") == line
    listed = "- 2 posts\n- 2 posts"
    assert without_repeats(listed) == listed  # a list's lines stay
    assert without_repeats("Yes. Yes.") == "Yes. Yes."


def test_the_project_picture_speaks_to_him():
    from core import project_ripple, question_plans as qp

    sheet = qp.Sheet("project picture", "What a project touches")
    project_ripple.gather(None, sheet, "I'm thinking about getting goats")
    said = sheet.as_text()
    assert "you're planning" in said and "he's planning" not in said and "(a goats)" not in said


def test_what_to_build_next_for_the_shop_is_never_his_projects():
    from core import question_plans as qp

    assert qp.NOT_FOR["projects"].search("What should I build next for the shop?")
    assert not qp.NOT_FOR["projects"].search("what should I build next on the homestead?")


def test_a_one_sentence_paragraph_stays():
    text = "2 messages, from ten to eleven today.\n\nHere is what you asked:\n- How big should the coop be?"
    assert without_repeats(text) == text
