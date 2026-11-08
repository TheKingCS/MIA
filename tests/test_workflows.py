"""Workflows MIA makes (ACAF step 3, DEC-0092, core/workflows.py): a trigger
and steps from a fixed vocabulary, approved once for exactly what they list,
messages only through the gate, adds through actions, every run logged."""

from datetime import datetime

import pytest

from core import creation_maker, workflows as wf
from tests.test_creations import DESIGN, _history, act, model, world  # noqa: F401  (the fixture)


def seed_bank(w):
    """Makes and publishes a seed-bank creation with three varieties saved."""
    creation_maker.make(w, "keep track of the seeds I save please", ask=model(DESIGN))
    act(w, "creation.publish", {"creation_id": "C-0001"})
    for v, n in (("Hopi Blue", 60), ("Glass Gem", 120), ("Moon and Stars", 25)):
        act(w, "records.add", {"creation_id": "C-0001", "values": {"variety": v, "count": n, "saved_on": "2026-11-01"}})


WEEKLY = {"kind": "workflow", "title": "Seed check", "owner": "household", "trigger": {"every": "week", "weekday": 6},
          "limits": {"adds_per_run": 1},
          "steps": [{"step": "read", "source": "creation:C-0001", "within_days": 30, "as": "seeds"},
                    {"step": "count", "of": "seeds", "as": "kinds"},
                    {"step": "sum", "of": "seeds.count", "as": "total"},
                    {"step": "when", "value": "kinds", "above": 2, "then": [
                        {"step": "tell", "title": "Seeds", "text": "{kinds} kinds saved this month, {total} seeds."},
                        {"step": "add", "to": "creation:C-0001", "values": {"variety": "Checked {kinds}"}}]}]}


def test_a_workflow_is_checked_against_what_the_person_has(world):
    w = world
    seed_bank(w)
    assert wf.check(WEEKLY, w) == []
    assert any("no source 'creation:C-0009'" in p for p in wf.check(
        {**WEEKLY, "steps": [{"step": "read", "source": "creation:C-0009", "as": "x"}]}, w))
    assert any("{nope} isn't a number" in p for p in wf.check(
        {**WEEKLY, "steps": WEEKLY["steps"][:2] + [{"step": "tell", "text": "{nope}"}]}, w))
    assert any("adds_per_run of 1 or more" in p for p in wf.check({**WEEKLY, "limits": {}}, w))
    nested = {**WEEKLY, "steps": WEEKLY["steps"][:2] + [{"step": "when", "value": "kinds", "above": 1, "then": [
        {"step": "when", "value": "kinds", "above": 2, "then": [{"step": "tell", "text": "x"}]}]}]}
    assert any("can't hold another when" in p for p in wf.check(nested, w))
    assert any("Unknown part 'script'" in p for p in wf.check({**WEEKLY, "script": "rm"}, w))
    spend = {**WEEKLY, "limits": {}, "steps": [{"step": "read", "source": "history:spending", "as": "s"},
                                                {"step": "sum", "of": "s.amount", "as": "spent"},
                                                {"step": "tell", "text": "{spent} this week"}]}
    assert wf.check(spend, w) == [] and any("no source 'history:spending'" in p for p in wf.check(spend, w, child=True))


def test_approved_once_for_what_it_lists_then_it_runs_and_logs(world):
    w = world
    seed_bank(w)
    w.creations.draft(WEEKLY, [], why="a weekly seed check", blueprint="")
    proposal = w.actions.propose(w, "creation.publish", {"creation_id": "C-0002"})
    assert "tell you things (through MIA's message limits)" in proposal.summary
    assert "add up to 1 record(s) a run to C-0001" in proposal.summary
    w.actions.approve(w, proposal.proposal_id)
    dry = wf.run(w, "C-0002", dry=True, now=datetime(2026, 11, 8, 9))
    assert "would tell: 3 kinds saved this month, 205 seeds." in dry["lines"]
    assert len(w.record_sets.sets[0]["records"]) == 3  # a dry run changes nothing
    done = wf.run(w, "C-0002", now=datetime(2026, 11, 8, 9))
    assert done["added"] == 1 and done["offers"][0].message == "3 kinds saved this month, 205 seeds."
    assert done["offers"][0].topic == "workflow:C-0002"  # through the gate, never around it
    assert w.record_sets.sets[0]["records"][-1]["values"]["variety"] == "Checked 3"
    assert w.creations.get("C-0002")["runs"][-1]["at"].startswith("2026-11-08")


def test_it_runs_when_its_trigger_comes_round_and_not_twice(world):
    w = world
    seed_bank(w)
    w.creations.draft(WEEKLY, [], why="weekly", blueprint="")
    act(w, "creation.publish", {"creation_id": "C-0002"})
    assert wf.run_due(w, datetime(2026, 11, 7, 9)) == []  # a Saturday: not its day
    offers = wf.run_due(w, datetime(2026, 11, 8, 9))  # Sunday
    assert len(offers) == 1
    assert wf.run_due(w, datetime(2026, 11, 8, 18)) == []  # already ran today
    assert wf.run_due(w, datetime(2026, 11, 15, 9))  # the next Sunday


def test_triggers_and_words():
    """A weekly or monthly workflow is due once per period, and is described in words, with what it may do."""
    week = {"trigger": {"every": "week", "weekday": 0}}
    assert wf.due(week, "", datetime(2026, 11, 9)) and not wf.due(week, "2026-11-09T08:00", datetime(2026, 11, 9, 20))
    month = {"trigger": {"every": "month", "day": 1}}
    assert wf.due(month, "2026-10-01", datetime(2026, 11, 1)) and not wf.due(month, "2026-11-01", datetime(2026, 11, 1, 9))
    assert wf.describe(WEEKLY)[0] == "Every week on Sunday:"
    assert "  tell you: “{kinds} kinds saved this month, {total} seeds.”" in wf.describe(WEEKLY)
    assert wf.may({"steps": [{"step": "read"}]}) == ["only read"]


def test_made_from_a_sentence_and_held_to_what_was_meant(world):
    """"fewer than 20 eggs a week" must add up the eggs, not count the collections."""
    import json as json_mod

    w = world
    eggs = {"title": "Low eggs", "owner": "household", "trigger": {"every": "week"},
            "steps": [{"step": "read", "source": "history:eggs", "within_days": 7, "as": "week"},
                      {"step": "count", "of": "week", "as": "n"},
                      {"step": "when", "value": "n", "below": 20, "then": [{"step": "tell", "text": "Only {n} eggs."}]}]}
    fixed = json_mod.loads(json_mod.dumps(eggs))
    fixed["steps"][1] = {"step": "sum", "of": "week.eggs", "as": "n"}
    ask = model(eggs, fixed)
    made = creation_maker.make_workflow(w, "Let me know if the chickens lay fewer than 20 eggs in a week", ask=ask)
    assert made["versions"][-1]["spec"]["steps"][1]["step"] == "sum" and "use \"sum\" of week.eggs" in ask.asked[1]
    assert any("takes no field" in p for p in wf.check(
        {**eggs, "steps": [eggs["steps"][0], {"step": "count", "of": "week.eggs", "as": "n"}]}, w))
    from core.creation_maker import RECURRING

    assert RECURRING.search("every Sunday tell me what I spent") and RECURRING.search("remind me to water")
    assert not RECURRING.search("keep track of the seeds I save")
