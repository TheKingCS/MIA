"""The Chronicle Archive (DEC-0084, core/saga.py): story material found in
the real records by rule, joined only by Zac, personal moments never in the
repo."""

import json
from types import SimpleNamespace

import pytest

from core import saga


def task(tid, title, decisions=()):
    """A task with its id, title and decisions."""
    return SimpleNamespace(id=tid, title=title, decisions=list(decisions))


ACTIVITY = [
    {"at": "2026-11-03T09:00:00+00:00", "who": "claude", "action": "done", "task": "T-0005",
     "detail": "tests: 48 passed; commit ed641da MIA-DII step 5"},
    {"at": "2026-11-03T15:22:00+00:00", "who": "QA Engineer (ollama-coder)", "action": "review", "task": "T-0019",
     "detail": "changes: unused name"},
    {"at": "2026-11-03T15:23:00+00:00", "who": "QA Engineer (ollama-coder)", "action": "review", "task": "T-0019",
     "detail": "changes: again"},
    {"at": "2026-11-03T15:40:00+00:00", "who": "zac", "action": "approve", "task": "T-0019",
     "detail": "reverted: It broke here: tests/test_plaid_manager.py"},
    {"at": "2026-11-05T10:00:00+00:00", "who": "zac", "action": "approve", "task": "T-0019", "detail": "merged abc1234567"},
    {"at": "2026-11-05T11:00:00+00:00", "who": "zac", "action": "approve", "task": "T-0020", "detail": "merged def"},
]
TASKS = {"T-0005": task("T-0005", "The dashboard", ["DEC-0068"]), "T-0019": task("T-0019", "A shared baseline"),
         "T-0020": task("T-0020", "Inspection")}


def test_the_rules_find_milestones_setbacks_and_firsts():
    found = {c["ref"]: c for c in saga.find(ACTIVITY, TASKS, [], [])}
    assert set(found) == {"task:T-0005", "first-review:ollama-coder", "revert:T-0019@2026-11-03T15:40:00+00:00",
                          "first-merge:T-0019"}  # one first review per provider, one first merge
    done = found["task:T-0005"]
    assert done["category"] == "milestone" and done["significance"] == 3  # tied to a decision
    assert done["sources"] == ["task:T-0005", "dec:DEC-0068", "commit:ed641da"]
    assert found["revert:T-0019@2026-11-03T15:40:00+00:00"]["category"] == "setback"
    assert found["first-merge:T-0019"]["significance"] == 4


def test_decisions_and_council_threads(tmp_path):
    decisions = tmp_path / "DECISIONS.md"
    decisions.write_text("### DEC-0001: Approved one\n- Status: APPROVED\n- Proposed by: x · Approved by: zac, 2026-10-01 (yes)\n"
                         "### DEC-0002: Not yet\n- Status: PROPOSED\n", encoding="utf-8")
    assert saga._decisions(decisions) == [{"id": "DEC-0001", "title": "Approved one", "at": "2026-10-01"}]
    one = [{"id": "a", "who": "zac", "text": "q", "kind": "message", "at": "1"},
           {"id": "b", "who": "claude", "kind": "answer"}]
    two = [{"id": "c", "who": "zac", "text": "debate it", "kind": "message", "at": "2"},
           {"id": "d", "who": "claude", "kind": "answer"}, {"id": "e", "who": "codex", "kind": "answer"},
           {"id": "f", "who": "mia", "kind": "summary"}]
    found = saga.find([], {}, [], [one, two, two])
    assert [c["title"] for c in found] == ["The first council debate", "A council discussion"]  # one member isn't a debate
    assert found[0]["involved"] == ["claude", "codex", "mia", "zac"] and found[0]["significance"] == 4


def test_nothing_joins_until_zac_accepts_and_a_drop_stays_dropped(tmp_path, monkeypatch):
    root = tmp_path / "saga"
    c = saga.find(ACTIVITY, TASKS, [], [])
    monkeypatch.setattr(saga, "candidates", lambda root=root: [x for x in c if x["ref"] not in saga._decided(root)])
    assert saga.events(root) == []
    event = saga.accept(c[0], root=root)
    assert event["id"] == "E-0001" and event["approved"] == "yes" and event["privacy"] == "series"
    assert event["sources"] == c[0]["sources"] and event["timeline"] == "real"
    private = saga.accept(c[1], privacy="private", root=root)
    saga.drop(c[2]["ref"], root=root)
    assert [x["ref"] for x in saga.candidates(root)] == [c[3]["ref"]]  # accepted and dropped never come back
    assert saga.mark(private["id"], "series", root=root)["privacy"] == "series"
    with pytest.raises(ValueError):
        saga.accept(c[3], privacy="never", root=root)  # "never" is for personal moments
    on_disk = json.loads((root / "events" / "E-0001.json").read_text(encoding="utf-8"))
    assert on_disk["source_ref"] == c[0]["ref"]


def test_zac_can_add_one_himself(tmp_path):
    e = saga.note_idea("What if MIA could guide a hike through the glasses?", root=tmp_path)
    assert e["category"] == "idea" and e["status"] == "planned" and e["evidence"] == "none"
    assert saga.note_idea("The first council meeting on the glasses", root=tmp_path)["category"] == "milestone"
    with pytest.raises(ValueError):
        saga.note_idea("  ", root=tmp_path)


def test_moments_are_personal_private_and_said_aloud(tmp_path):
    moments = saga.SagaMoments(data_dir=tmp_path / "profiles" / "zac")
    last = {"asked": "MIA, are you proud of the council?", "said": "I am. It's how I'm learning."}
    context = SimpleNamespace(saga_moments=moments, traces=SimpleNamespace(recent=lambda n: [last]))
    said = saga.remember_command(context, "MIA, remember this for the Chronicles")
    assert said.startswith("Kept for the Chronicles (M-0001)")
    m = moments.recent(1)[0]
    assert m["said"] == last["asked"] and m["replied"] == last["said"] and m["privacy"] == "private"
    saga.remember_command(context, "save this for the chronicles: the first time she answered through the glasses")
    assert moments.recent(1)[0]["summary"] == "the first time she answered through the glasses"
    assert saga.remember_command(context, "keep that private").endswith("stays out of the Chronicles.")
    assert moments.recent(1)[0]["privacy"] == "never"
    assert saga.remember_command(context, "remember to buy milk") is None  # not this
    again = saga.SagaMoments(data_dir=tmp_path / "profiles" / "zac")
    assert [m["id"] for m in again.recent()] == ["M-0001", "M-0002"]  # kept in the person's own folder
    assert (tmp_path / "profiles" / "zac" / "saga_moments.json").exists()


def test_moments_are_a_personal_store():
    from core.personal_data import PERSONAL_STORES

    assert ("saga_moments", saga.SagaMoments) in PERSONAL_STORES


def test_said_to_mia_it_needs_no_model(tmp_path, monkeypatch):
    from core import quick_commands

    moments = saga.SagaMoments(data_dir=tmp_path)
    context = SimpleNamespace(saga_moments=moments, traces=None, fitness=None, actions=None)
    monkeypatch.setattr("core.child_accounts.is_child", lambda c, p: False)
    monkeypatch.setattr("core.person_settings.person_id", lambda c: "zac")
    monkeypatch.setattr(quick_commands, "_workout", lambda c, t: None)
    assert "Kept for the Chronicles" in quick_commands.handle(context, "remember this for the chronicles: issue one idea")
