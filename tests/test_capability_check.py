"""Tests for a capability's four descriptions read as one (DEC-0283, LS-04, core/capability_check.py): the tool, the
action kind, the manifest's tier and the effects table must agree."""
from types import SimpleNamespace

from core import capability_check as cc


def test_every_capability_of_mias_agrees_across_its_four_descriptions():
    """The repository's tools, kinds, manifests and effects table, checked as one."""
    assert cc.check() == []


def test_a_tool_looser_than_the_kind_it_proposes_is_caught():
    """A tool that would let her past the kind's tier, a missing tier, an irreversible kind she could do within a
    grant, and a destructive tool that only observes are each said."""
    def proposes_bill(context, args):
        """Proposes bill.pay."""
        return context.actions.propose(context, "bill.pay", {})

    described = cc.describe(
        {"pay_it": SimpleNamespace(destructive=False, handler=proposes_bill),
         "wipe": SimpleNamespace(destructive=True, handler=None),
         "untiered": SimpleNamespace(destructive=False, handler=None)},
        {"bill.pay": None, "myfile.delete": None},
        {"pay_it": "act_within_grant", "wipe": "observe", "bill.pay": "act_with_approval",
         "myfile.delete": "act_within_grant"}, set())
    assert described["pay_it"]["proposes"] == ["bill.pay"]
    assert cc.disagreements(described) == [
        "myfile.delete can't be undone but is act_within_grant",
        "pay_it is act_within_grant but proposes bill.pay, which is act_with_approval",
        "untiered has no tier in its app's manifest",
        "wipe is destructive but only observe",
    ]


def test_a_failure_says_which_of_four_kinds_it_is():
    """An ActionError is invalid unless it's a Refused or an Unavailable; anything else is failed."""
    from core.actions import ActionError, Refused, Unavailable, error_kind

    assert [error_kind(p) for p in (ActionError("x"), Refused("x"), Unavailable("x"), RuntimeError("x"))] == \
        ["invalid", "refused", "unavailable", "failed"]


def test_outside_work_ends_at_the_stop_or_its_time_between_steps():
    """The stop comes first; then the time; check() raises the matching kind."""
    import pytest

    from core.actions import Refused, Unavailable
    from core.deadline import Deadline

    now = [0.0]
    stopped = [False]
    limit = Deadline(10, "the task", clock=lambda: now[0], stopped=lambda: stopped[0])
    assert limit.why_not() == ""
    now[0] = 11
    assert limit.why_not() == "the task took longer than 10 seconds"
    with pytest.raises(Unavailable):
        limit.check()
    stopped[0] = True
    assert limit.why_not() == "everything is stopped"
    with pytest.raises(Refused):
        limit.check()
