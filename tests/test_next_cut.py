"""
tests.test_next_cut
=====================

A plan's cut list read one cut at a time in the shop (next_cut): the plan he names, then "next cut" walking on from
where he is, the last one said, "start the cuts over", a plan with no cuts or none named answered plainly, going
back to a plan carrying on, a finished one named starting again, a vague name never picking a plan by its summary,
and the first cut of hay never the cut list.
"""

from types import SimpleNamespace

from core.assistant_plan_actions import _action_next_cut as next_cut

PLAN = {"id": "P1", "title": "Potting bench", "materials": {"cuts": [
    {"part": "legs", "qty": 4, "length_in": 34.0, "stock": "2x4"},
    {"part": "top slats", "qty": 6, "length_in": 48.0, "stock": "1x6"}]}}


WORKBENCH = {"id": "P2", "title": "Shop workbench", "summary": "a sturdy bench", "materials": {"cuts": [
    {"part": "legs", "qty": 4, "length_in": 33.0, "stock": "4x4"}]}}


class _Library:
    """The plans shelf, as much as next_cut uses of it."""

    def best(self, name):
        """The plan a name means (like the real shelf, a summary word is enough)."""
        low = name.lower()
        return PLAN if "potting" in low else WORKBENCH if "bench" in low or not low.strip() else None

    def get(self, plan_id):
        """A plan by id, either of the two."""
        return {"P1": PLAN, "P2": WORKBENCH}.get(plan_id)

    def worked_out(self, plan, **sizes):
        """No calculator here."""
        return None


def _ctx():
    """A context with the shelf."""
    import core.assistant_plan_actions as ap

    ap._CUT_PLACES.clear()
    return SimpleNamespace(plans=_Library(), config=None)


def test_the_cuts_are_read_one_at_a_time_and_start_over():
    ctx = _ctx()
    assert next_cut(ctx, {"plan": "the potting bench"}).startswith("Cut 1 of 2 for Potting bench: 4 x legs at")
    second = next_cut(ctx, {})
    assert "Cut 2 of 2" in second and "That's the last one." in second
    assert next_cut(ctx, {}).startswith("That's every cut for Potting bench")
    assert next_cut(ctx, {"start_over": "yes"}).startswith("Cut 1 of 2")


def test_no_plan_named_or_no_cuts_is_said_plainly():
    assert next_cut(_ctx(), {}).startswith("Which plan's cuts?")


def test_going_back_to_a_plan_carries_on_and_a_finished_one_starts_again():
    ctx = _ctx()
    next_cut(ctx, {"plan": "the potting bench"})
    next_cut(ctx, {"plan": "shop workbench"})
    assert next_cut(ctx, {"plan": "the potting bench"}).startswith("Cut 2 of 2")
    assert next_cut(ctx, {"plan": "the potting bench"}).startswith("Cut 1 of 2")  # finished: named again, again


def test_a_vague_name_never_picks_a_plan_by_its_summary():
    ctx = _ctx()
    assert next_cut(ctx, {"plan": "the plan"}).startswith("Which plan's cuts?")
    assert next_cut(ctx, {"plan": "garden bench"}).startswith("I don't have a plan called garden bench")


def test_the_hay_is_never_the_cut_list():
    from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools

    registry = build_desktop_registry()
    for said in ("When should I take the first cut of hay?", "What were the cuts for the hay last year?"):
        assert "next_cut" not in offered_tools(registry, said, demo_context()), said
