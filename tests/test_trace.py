"""
tests.test_trace
==================

LS-01 (DEC-0280): one trace id for everything one cause did. A turn runs under one id; a proposal carries the id of
what proposed it, and approving it later (from another request) runs under that same id, so what it changed and
recorded can be found from the cause; each scheduled job run is a cause of its own; and the turn's trace keeps the id
and the version of the code that built its prompt.
"""

from __future__ import annotations

from types import SimpleNamespace

from core import actions, trace
from core.scheduler import Scheduler


def test_tracing_keeps_an_id_for_the_block_and_puts_back_what_was_there():
    assert trace.current() == ""
    with trace.tracing() as outer:
        assert trace.current() == outer and len(outer) == 12
        with trace.tracing() as inner:
            assert inner == outer  # a step inside keeps its cause's id
        with trace.tracing("given") as given:
            assert given == "given" == trace.current()
        assert trace.current() == outer
    assert trace.current() == ""


def test_a_proposal_carries_its_causes_id_and_approving_it_later_runs_under_that_id():
    seen = []
    actions.ACTION_TYPES["test.traced"] = actions.ActionType(
        "test.traced", "Traced", {}, lambda c, p: "Traced", lambda c, p: seen.append(trace.current()) or "done")
    try:
        center, ctx = actions.ActionCenter(), SimpleNamespace(config=None)
        with trace.tracing("turn-1"):
            proposal = center.propose(ctx, "test.traced", {})
        assert proposal.trace == "turn-1" and trace.current() == ""
        center.approve(ctx, proposal.proposal_id)  # later, outside the turn: a press on the card
        assert seen == ["turn-1"]
        pressed = center.propose(ctx, "test.traced", {})  # a press on a screen starts a cause of its own
        assert len(pressed.trace) == 12 and pressed.trace != "turn-1"
    finally:
        actions.ACTION_TYPES.pop("test.traced", None)


def test_a_change_kept_for_undo_carries_the_id_of_its_cause():
    from core.undo_log import Change

    with trace.tracing("cause-7"):
        assert Change("action_x", "p1").trace == "cause-7"
    assert Change("action_x", "p1").trace == ""


def test_each_scheduled_job_run_is_a_cause_of_its_own():
    seen, now = [], [0.0]
    scheduler = Scheduler(clock=lambda: now[0])
    scheduler.add("watch", 10, lambda: seen.append(trace.current()), first_after=0)
    scheduler.run_due()
    now[0] = 20.0
    scheduler.run_due()
    assert len(seen) == 2 and all(len(t) == 12 for t in seen) and seen[0] != seen[1]


def test_the_turns_trace_keeps_its_id_and_the_prompt_codes_version():
    from core import turn_trace

    kept = []
    context = SimpleNamespace(traces=SimpleNamespace(add=kept.append), llm=None)
    conversation = SimpleNamespace(conversation_id="c1", mode="", current_privacy=lambda: "")
    turn = SimpleNamespace(replies=["Hi"], route="model", tools_offered=[], tools_called=[], used=[])
    with trace.tracing("turn-9"):
        turn_trace.record(context, conversation, "hello", turn, 0.5)
    assert kept and kept[0]["trace"] == "turn-9" and len(kept[0]["template"]) == 8


def test_a_life_event_carries_the_id_of_what_caused_it_and_survives_a_reload(tmp_path):
    from core import life_events

    where = SimpleNamespace(data_dir=tmp_path, context=None)
    with trace.tracing("cause-3"):
        event = life_events.record(where, "test_happened", "Something happened", profile_id="p1")
    assert event.trace == "cause-3"
    again = [e for e in life_events.LifeEventLog(None, tmp_path).all_events() if e.event_id == event.event_id]
    assert again and again[0].trace == "cause-3"  # read back from the sealed line
