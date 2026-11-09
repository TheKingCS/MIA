"""
tests.test_carpentry
======================

The Carpentry apprentice program (core/carpentry.py, DEC-0149): a learning path on core/paths.py's method, three
stages in an apprentice's order (safety first), every lesson with steps, why and what to watch for, every check
verifiable, found by the words someone uses, and a trade specialist for each trade Zac named.
"""

from core import carpentry, paths
from core import specialists as sp


def test_the_program_is_whole_and_starts_with_safety():
    """It passes the learning paths' own checks, its stages run safety and tools, layout and cutting, then framing,
    and its XP goes to the Carpentry skill."""
    assert paths.problems(carpentry.PROGRAM) == []
    assert [s.name for s in carpentry.STAGES] == ["Safety, tools and measuring", "Layout and cutting",
                                                  "Framing basics"]
    assert carpentry.STAGES[0].lessons[0].id == "safety" and carpentry.PROGRAM.skill == "carpentry"
    assert all(l.watch for s in carpentry.STAGES for l in s.lessons)


def test_wanting_to_learn_carpentry_finds_it():
    """"I want to learn carpentry" and "teach me framing" both mean this program."""
    paths._builtins()
    assert paths.find_program(None, "I want to learn carpentry").id == "carpentry"
    assert paths.find_program(None, "teach me framing").id == "carpentry"


def test_each_trade_has_its_own_specialist_watching_the_depth_loop():
    """Carpentry, plumbing, electrical, HVAC, appliances and the exterior each study their own trade, and a question
    goes to its own trade's specialist."""
    trades = {"carpentry", "plumbing", "electrical", "hvac", "appliances", "exterior"}
    assert trades <= set(sp.BY_ID)
    assert all("trades.depth" in sp.BY_ID[t].loops and "permit" in sp.BY_ID[t].limits for t in trades)
    assert sp.who_knows("my dryer runs but won't heat")[0].id == "appliances"
    assert sp.who_knows("how do I flash a window with house wrap")[0].id == "exterior"
