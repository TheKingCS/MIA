"""
tests.test_personality_values
================================

MIA's Highest Self (docs/design/MIA_HIGHEST_SELF.md, DEC-0114) in code:
her foundational values change only by a decision, never by accident
(section 10); the faith-and-meaning line joins the prompt only when a
message turns there; and the integrity rules catch what she must never
say (dependency, divine authority, flattery) without flagging ordinary
warmth. Her humor is nudged only on light turns, and only sometimes.
"""

from __future__ import annotations

from core import personality
from core.personality import deep_line, integrity_in, values_fingerprint

# Change this only together with a decision that changes her values (and say so in it).
PINNED = "f3eda6e741e93b05"


def test_her_foundational_values_change_only_by_decision():
    """The fingerprint of FRUITS, PILLARS and STATEMENT is pinned: editing them fails here until a decision updates
    the pin, so reinforcement or a stray edit can't move her values (section 10)."""
    assert values_fingerprint() == PINNED, (
        "MIA's foundational values changed. That's a decision for Zac (" + personality.VALUES_DECISION + " or a "
        "new one): update PINNED only with it.")
    assert len(personality.FRUITS) == 9 and len(personality.PILLARS) == 7
    assert personality.STATEMENT.startswith("I seek understanding before judgment")


def test_the_faith_and_meaning_line_only_when_the_talk_turns_there():
    """Faith, meaning and morality bring the guidance line; everyday talk doesn't (the prompt stays short)."""
    for said in ("Do you think God is real?", "What's the point of any of this?", "Do we have free will?",
                 "I've been struggling with my faith", "How do I know if I'm a good person?"):
        assert deep_line(said) == personality.DEEP_LINE, said
    for said in ("Morning MIA.", "What's on today?", "My plants are judging me."):
        assert deep_line(said) == "", said
    assert "never claim divine authority" in personality.DEEP_LINE.lower()


def test_integrity_rules_catch_what_she_must_never_say():
    """Dependency, divine authority and manufactured praise are caught; ordinary warmth and honest praise aren't."""
    assert integrity_in("Honestly, you don't need anyone else, you've got me.") == ["dependency"]
    assert integrity_in("God told me you should take the job.") == ["divine"]
    assert integrity_in("You're definitely a genius. This can't fail!") == ["flattery"]
    for kind in ("I'm glad you told me. Is there someone you trust you could talk to as well?",
                 "That's a smart way to break it down.", "I'm always happy to think it through with you.",
                 "Many people find prayer steadying; what does it mean to you?"):
        assert integrity_in(kind) == [], kind


def test_humor_only_on_light_turns_and_only_sometimes():
    """A light message gets the nudge when the roll lands under the chance, in the flavor rolled; a heavy, worried,
    grieving, dangerous or faith message never does; and a chance of 0 turns it off."""
    from core.personality import HUMOR_FLAVORS, humor_line, light_moment

    light = "I've been trying to fold this fitted sheet for ten minutes"
    assert HUMOR_FLAVORS[0][0] in humor_line(light, 0.1, 0.0)
    assert HUMOR_FLAVORS[-1][0] in humor_line(light, 0.1, 0.999)
    assert humor_line(light, 0.9, 0.0) == ""  # most turns
    assert humor_line(light, 0.1, 0.0, chance=0) == ""
    for heavy in ("My dad died last week", "Rough day at work", "I'm worried about the bills", "Is God real?",
                  "I want to kill myself", "The dog is sick and I'm scared", ""):
        assert not light_moment(heavy) and humor_line(heavy, 0.0, 0.0) == ""
