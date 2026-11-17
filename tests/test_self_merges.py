"""MIA's own changes going in on Claude's pass, the daily summary and the Undo (core/self_merges.py, DEC-0225)."""

from datetime import datetime
from types import SimpleNamespace

import pytest

from core import dev_lab, self_merges


def _proposal(pid="p1", status=dev_lab.READY, evidence=self_merges.SOURCE, refused=()):
    """A stand-in lab proposal."""
    return SimpleNamespace(proposal_id=pid, branch=f"lab/{pid}", status=status, evidence=evidence,
                           refused=list(refused), title=f"Night School: fix {pid}", problem="the problem",
                           tests={"summary": "10 passed", "base_summary": "9 passed, 1 failed"}, merged_as="",
                           note="")


class _Lab:
    """A stand-in lab: lists its proposals and records approvals."""
    READY, MERGED = dev_lab.READY, dev_lab.MERGED

    def __init__(self, proposals, outcome=dev_lab.MERGED):
        """Its proposals, and what an approval ends as."""
        self.proposals, self.outcome, self.approved = proposals, outcome, []

    def all_proposals(self):
        """The proposals."""
        return self.proposals

    def approve(self, pid):
        """Records the approval and returns the proposal as merged (or reverted)."""
        self.approved.append(pid)
        return SimpleNamespace(status=self.outcome, merged_as="abc123", note="In.")


def test_only_ready_night_school_proposals_free_of_protected_files_are_candidates():
    found = self_merges.candidates([_proposal("a"), _proposal("b", status=dev_lab.NOT_READY),
                                    _proposal("c", evidence="Zac asked"), _proposal("d", refused=["core/stop.py"])],
                                   entries=[])
    assert [p.proposal_id for p in found] == ["a"]


def test_a_proposal_already_reviewed_on_its_branch_is_not_reviewed_again():
    assert self_merges.candidates([_proposal("a")], entries=[{"key": "a:lab/a"}]) == []


@pytest.mark.parametrize("reply,reviewer,ready,expected", [
    ('{"verdict": "pass", "findings": [], "why": "w"}', "claude-code", True, "pass"),
    ('{"verdict": "pass"}', "codex", True, "hold"),
    ('{"verdict": "pass"}', "claude-code", False, "hold"),
    ("not json at all", "claude-code", True, "hold"),
    ('{"verdict": "hold", "findings": ["a bug"]}', "claude-code", True, "hold"),
])
def test_only_claudes_readable_pass_on_a_ready_change_is_a_pass(reply, reviewer, ready, expected):
    assert self_merges.verdict_from(reply, reviewer, ready)[0] == expected


def test_claudes_pass_merges_through_the_lab_and_a_hold_does_not(tmp_path):
    path = tmp_path / "m.json"
    lab = _Lab([_proposal("a"), _proposal("b")])
    done = self_merges.review_and_merge(lambda _p: '{"verdict": "pass", "why": "Fixes the timer"}', "claude-code",
                                        lab=lab, diff=lambda _pid: "+x", limit=2, path=path)
    assert lab.approved == ["a", "b"] and [d["status"] for d in done] == ["merged", "merged"]
    lab2 = _Lab([_proposal("c")])
    held = self_merges.review_and_merge(lambda _p: '{"verdict": "hold"}', "claude-code", lab=lab2,
                                        diff=lambda _pid: "+x", path=path)
    assert lab2.approved == [] and held[0]["status"] == "held"


def test_a_merge_the_lab_reverted_is_recorded_as_reverted(tmp_path):
    lab = _Lab([_proposal("a")], outcome=dev_lab.REVERTED)
    done = self_merges.review_and_merge(lambda _p: '{"verdict": "pass"}', "claude-code", lab=lab,
                                        diff=lambda _pid: "", path=tmp_path / "m.json")
    assert done[0]["status"] == "reverted"


def test_a_lab_without_proposals_reviews_nothing(tmp_path):
    assert self_merges.review_and_merge(lambda _p: "", "claude-code", lab=object(), path=tmp_path / "m.json") == []


def test_the_daily_summary_offers_each_merged_change_once_with_how_to_undo(tmp_path, monkeypatch):
    path = tmp_path / "m.json"
    self_merges.review_and_merge(lambda _p: '{"verdict": "pass", "why": "Fixes the timer"}', "claude-code",
                                 lab=_Lab([_proposal("a")]), diff=lambda _pid: "", path=path)
    monkeypatch.setattr("core.person_settings.person_id", lambda _c: "me")
    monkeypatch.setattr("core.self_report._owner", lambda _c: "me")
    first = self_merges.offer(None, datetime(2026, 11, 18, 9), path=path)
    assert len(first) == 1 and "Fixes the timer (a)" in first[0].message and "Undo" in first[0].message
    assert self_merges.offer(None, datetime(2026, 11, 19, 9), path=path) == []


def test_the_summary_goes_only_to_the_pcs_owner(tmp_path, monkeypatch):
    path = tmp_path / "m.json"
    self_merges.review_and_merge(lambda _p: '{"verdict": "pass"}', "claude-code", lab=_Lab([_proposal("a")]),
                                 diff=lambda _pid: "", path=path)
    monkeypatch.setattr("core.person_settings.person_id", lambda _c: "someone")
    monkeypatch.setattr("core.self_report._owner", lambda _c: "me")
    assert self_merges.offer(None, path=path) == []


def test_an_undone_change_is_shown_as_undone(tmp_path):
    path = tmp_path / "m.json"
    self_merges.review_and_merge(lambda _p: '{"verdict": "pass"}', "claude-code", lab=_Lab([_proposal("a")]),
                                 diff=lambda _pid: "", path=path)
    self_merges.mark_undone("a", path=path)
    assert [c["status"] for c in self_merges.recent(path=path)] == ["undone"]


def test_the_lab_refuses_to_undo_a_change_that_is_not_in(monkeypatch):
    monkeypatch.setattr(dev_lab, "get", lambda _pid: SimpleNamespace(status=dev_lab.READY, merged_as=""))
    with pytest.raises(ValueError, match="Only a change that's in"):
        dev_lab.revert("x")


def test_the_lab_reverts_a_merged_change_and_keeps_the_history(monkeypatch):
    p = dev_lab.Proposal("x", "t", "p", status=dev_lab.MERGED, files=["core/a.py"])
    p.merged_as = "abc"
    calls = []
    monkeypatch.setattr(dev_lab, "get", lambda _pid: p)
    monkeypatch.setattr(dev_lab, "_put", lambda q: q)
    monkeypatch.setattr(dev_lab, "_git", lambda *a, **k: calls.append(a) or "")
    assert dev_lab.revert("x").status == dev_lab.REVERTED
    assert ("revert", "-m", "1", "--no-edit", "abc") in calls


def test_undo_is_an_action_kind_with_its_tier_and_reach():
    from core import lab_actions  # noqa: F401 - registers the kinds
    from core.action_effects import EFFECTS
    from core.actions import ACTION_TYPES

    assert "lab.revert" in ACTION_TYPES and EFFECTS["lab.revert"][0] == "system"


def test_a_merge_or_revert_that_fails_is_backed_out_before_the_error(monkeypatch):
    from types import SimpleNamespace as NS

    ran = []

    def fake_run(args, **_kw):
        """git: the revert fails, the abort is recorded."""
        ran.append(args)
        return NS(returncode=1 if "revert" in args and "--abort" not in args else 0, stdout="", stderr="conflict")

    monkeypatch.setattr(dev_lab.subprocess, "run", fake_run)
    with pytest.raises(RuntimeError, match="conflict"):
        dev_lab._git("revert", "-m", "1", "--no-edit", "abc", undo=("revert", "--abort"))
    assert ran[-1] == ["git", "revert", "--abort"]


def test_the_merge_rechecks_the_protected_list_as_it_is_now(monkeypatch):
    p = dev_lab.Proposal("x", "t", "p", status=dev_lab.READY, files=["core/a.py"], branch="lab/x", base="b0")
    monkeypatch.setattr(dev_lab, "get", lambda _pid: p)
    monkeypatch.setattr(dev_lab, "_git", lambda *a, **k: "core/grants.py\ncore/a.py" if "diff" in a else "")
    with pytest.raises(ValueError, match="core/grants.py"):
        dev_lab.approve("x", suite=lambda _p: {"failed": []})


def test_the_daily_summary_waits_for_an_opening_rather_than_being_dropped(tmp_path, monkeypatch):
    from core.communication_gate import TIMELY

    path = tmp_path / "m.json"
    self_merges.review_and_merge(lambda _p: '{"verdict": "pass"}', "claude-code", lab=_Lab([_proposal("a")]),
                                 diff=lambda _pid: "", path=path)
    monkeypatch.setattr("core.person_settings.person_id", lambda _c: "me")
    monkeypatch.setattr("core.self_report._owner", lambda _c: "me")
    assert self_merges.offer(None, path=path)[0].urgency == TIMELY
