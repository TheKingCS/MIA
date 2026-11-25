"""
tests.test_calculators_are_lookups
====================================

The pure calculators (board feet, concrete, Ohm's law, units, a subnet) only read (the observe tier), so a question
reaching for one keeps it (live sweep, 2026-11-25: "how many bags of concrete for a 10 by 10 slab?" reached
calculate_concrete, was taken for a change, and the model answered from memory); and the building calculators' answers
are said as they are, figures and all.
"""

from core.main_thread import changes_records
from core.tool_loop import SAID_AS_IS

CALCULATORS = ("calculate_board_feet", "calculate_concrete", "calculate_ohms_law", "convert_units", "calculate_subnet")


def test_the_pure_calculators_never_count_as_changes():
    for name in CALCULATORS:
        assert not changes_records(name), name


def test_the_building_calculators_are_said_as_they_are():
    assert {"calculate_concrete", "calculate_board_feet", "material_list", "cut_list", "feed_mix"} <= SAID_AS_IS
