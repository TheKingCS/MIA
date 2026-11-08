"""The flow loops Night School's teacher drafted (T-0047, core/loops.py): actions that broke or were turned
down, email drafts thrown away or left open, unprompted messages dismissed or expired. Each reads records
the person already keeps; an action's record carries its kind only, never what was in it."""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import loops
from core.actions import FAILED, PROPOSED, ActionCenter, Proposal
from core.failure_log import FailureLog

BY_ID = {l.id: l for l in loops.LOOPS}


def ago(**kw) -> str:
    """An ISO time that long before now."""
    return (datetime.now() - timedelta(**kw)).isoformat(timespec="seconds")


def test_a_failed_or_declined_action_is_kept_by_its_kind_only(tmp_path):
    book = FailureLog(None, data_dir=tmp_path)
    context = SimpleNamespace(failures=book, active_profile_id=None)
    center = ActionCenter()
    turned_down = Proposal("p1", "task.done", {"title": "Call the dentist"}, "Mark it done", None, proposed_by="mia")
    mine = Proposal("p2", "task.done", {"title": "x"}, "Mark it done", None)
    center._proposals = {"p1": turned_down, "p2": mine}
    center.get = lambda pid, who: center._proposals[pid]
    center.reject(context, "p1")
    center.reject(context, "p2")  # the person's own: not a suggestion of hers
    events = book.events()
    assert [(e["kind"], e["tool"]) for e in events] == [("declined", "task.done")]
    assert "dentist" not in str(events)


def test_the_action_loops(tmp_path):
    """The action loops count failed and declined actions, and the answers loop counts only rephrasings."""
    book = FailureLog(None, data_dir=tmp_path)
    book.record("action_failed", tool="bill.pay", surface="actions")
    book.record("declined", tool="task.done", surface="actions")
    book.record("rephrased")
    turns = [{"at": ago(hours=1), "seconds": 2}] * 25
    person = SimpleNamespace(failures=book, traces=SimpleNamespace(recent=lambda n: turns))
    failed = BY_ID["actions.failed"].measure(person)
    assert failed.value == 1 and "bill.pay" in failed.detail
    assert loops.judge(BY_ID["actions.failed"], failed, [])["state"] == "below"
    assert BY_ID["actions.declined"].measure(person).value == 4.0
    assert BY_ID["answers.failures"].measure(person).value == 4.0  # only the rephrase: an action has its own loops


def draft(status, days=1):
    """An email draft with a status, made that many days ago."""
    return SimpleNamespace(status=status, created_at=ago(days=days))


def test_the_email_loops():
    """The email loops measure the share of drafts thrown away and the drafts left open too long."""
    drafts = [draft("sent"), draft("discarded"), draft("discarded"), draft("sent"), draft("discarded"),
              draft("draft", days=10), draft("draft"), draft("sent", days=60)]
    store = SimpleNamespace(drafts=lambda: drafts, open_drafts=lambda: [d for d in drafts if d.status == "draft"])
    person = SimpleNamespace(email_drafts=store)
    thrown = BY_ID["email.discarded"].measure(person)
    assert (thrown.value, thrown.n) == (0.6, 5)
    assert loops.judge(BY_ID["email.discarded"], thrown, [])["state"] == "below"
    assert BY_ID["email.left_open"].measure(person).value == 1


def test_the_gate_loops():
    """The gate loops measure dismissed messages (urgent ones not counted) and ones dropped for waiting too long."""
    log = [{"at": ago(days=1), "action": "act", "urgency": "normal", "dismissed_at": ago(hours=20)},
           {"at": ago(days=1), "action": "act", "urgency": "normal"},
           {"at": ago(days=2), "action": "act", "urgency": "urgent", "dismissed_at": ago(days=2)},
           {"at": ago(days=1), "action": "defer"}, {"at": ago(days=1), "action": "defer"},
           {"at": ago(hours=3), "action": "drop", "reason": "waited too long; it's no longer current"},
           {"at": ago(days=20), "action": "act", "urgency": "normal", "dismissed_at": ago(days=20)}]
    gate = SimpleNamespace(entries_since=lambda since: [e for e in log if e["at"] >= since])
    person = SimpleNamespace(communication=gate)
    assert BY_ID["gate.dismissed"].measure(person).value == 0.5  # an urgent one always goes out: not counted
    assert BY_ID["gate.expired"].measure(person).value == 0.5


def test_nothing_to_measure_is_none():
    nobody = SimpleNamespace()
    for loop_id in ("actions.failed", "email.discarded", "email.left_open", "gate.dismissed", "gate.expired"):
        assert BY_ID[loop_id].measure(nobody) is None
