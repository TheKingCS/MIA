"""
tests.test_review_17
======================

The seventeenth review's fixes (2026-11-25): a need is a short thing, never a time, a remark or a list ("tires in the
spring", "wipers, badly", "an oil change, a new filter"); the same task is found by its words' stems ("a tire
rotation" is Rotate Tires, "new brake pads" is Replace Brake Pads); a definition whose parameters are a schema is an
answer.
"""

from types import SimpleNamespace

from core import assistant_turn

LISTED = ("Maintenance tasks:\n- Rotate Tires (Truck): due in 3 days\n- Replace Brake Pads (Truck): due in 40 days\n"
          "- Battery check (Truck): due in 9 days")


def _context():
    """His truck with three tasks, and what a tool would run."""
    ran = []
    book = SimpleNamespace(all_assets=lambda: [SimpleNamespace(name="Truck"), SimpleNamespace(name="Mower")])
    return ran, SimpleNamespace(maintenance=book, assistant_actions=SimpleNamespace(
        execute=lambda c, n, a: ran.append((n, a)) or (LISTED if n == "list_maintenance_tasks" else "Added it.")))


def test_a_time_a_remark_or_a_list_is_never_a_task():
    ran, context = _context()
    for words in ("the truck needs tires in the spring", "the truck needs new tires before winter",
                  "the truck needs an oil change after the trip", "the truck needs an oil change asap",
                  "the truck needs new wipers, badly", "the truck needs an oil change, a new filter",
                  "the truck needs a lot of work", "the truck needs gas and oil", "the truck needs 3 quarts of oil"):
        assert assistant_turn._upkeep_reply(context, words) is None, words
    assert not any(n == "add_maintenance_task" for n, _ in ran)


def test_the_same_task_said_another_way_is_already_listed():
    for words in ("the truck needs a tire rotation", "the truck needs its tires rotated", "the truck needs new brake pads"):
        ran, context = _context()
        assert "already on your list" in assistant_turn._upkeep_reply(context, words), words
    for words in ("the truck needs a new battery", "the mower needs a tune-up", "the truck needs its 30,000 mile service"):
        ran, context = _context()
        assert assistant_turn._upkeep_reply(context, words) == "Added it.", words


def test_a_definition_with_a_parameter_schema_is_an_answer():
    context = SimpleNamespace(assistant_actions=SimpleNamespace(_actions={}))
    assert not assistant_turn._garbled('{"name": "make_note", "parameters": {"properties": {"x": {"description": '
                                       '"y"}}}}', context)
