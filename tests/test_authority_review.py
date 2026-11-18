"""
tests.test_authority_review
=============================

The defects Fable's review of 2026-11-18 found in what MIA may do on her own, each kept fixed by a test here: an undo
can't lift a stop or revive a standing yes; a standing yes covers only routine entries; her own merges can't be passed
half-read, by someone else's proposal, with tests deleted or erroring, or while everything is stopped; a spoken yes
can't approve what needs a press; and her reports to him aren't paused away.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from core import dev_lab, kind_grants, self_merges, spoken_approval, stop, undo_log
from core import communication_gate as gate


# ------------------------------------------------------------------ an undo and the two settings it never puts back


def test_an_undo_of_the_config_keeps_todays_stop_and_drops_a_yes_he_took_back():
    old = {"display": {"theme": "aquatic"}, "grants": {"kinds": {"routine.log": {"given": "2026-11-01"}}},
           "profiles": {"p1": {"name": "A", "settings": {"grants.kinds": {"expense.add": {"given": "2026-11-01"}}}}}}
    now = {"display": {"theme": "light"}, "mia": {"stop_everything": {"since": "2026-11-18T10:00:00", "until": ""}},
           "profiles": {"p1": {"name": "A", "settings": {"mia.stop_everything": {"since": "2026-11-18T10:00:00"}}}}}
    restored = undo_log._carry_sticky(now, old)
    assert restored["display"]["theme"] == "aquatic"  # the change being undone is undone
    assert restored["mia"]["stop_everything"]["since"] == "2026-11-18T10:00:00"  # the stop stays on
    assert "kinds" not in restored.get("grants", {})  # the yes he took back stays taken back
    assert restored["profiles"]["p1"]["settings"] == {"mia.stop_everything": {"since": "2026-11-18T10:00:00"}}


def test_restoring_the_config_file_goes_through_that_rule_and_other_files_are_untouched(tmp_path, monkeypatch):
    from core import config_manager

    config = tmp_path / "config.json"
    monkeypatch.setattr(config_manager, "_CONFIG_FILE", config)
    config.write_text(json.dumps({"mia": {"stop_everything": {"since": "now"}}, "a": 2}), encoding="utf-8")
    kept = json.loads(undo_log.keep_sticky(config, json.dumps({"a": 1}).encode("utf-8")))
    assert kept == {"a": 1, "mia": {"stop_everything": {"since": "now"}}}
    assert undo_log.keep_sticky(tmp_path / "notes.json", b"x") == b"x"
    config.write_text("{not json", encoding="utf-8")  # unreadable now: left as it is, never restored without the stop
    assert undo_log.keep_sticky(config, b'{"a": 1}') == b"{not json"


# ------------------------------------------------------------------ what a standing yes may cover


@pytest.mark.parametrize("kind", [
    "setting.set", "lab.propose", "connection.allow", "connect.rental_calendar", "activity.noting", "comms.limit",
    "news.turn_on", "browser.run_task", "do_browser_task", "keep_taught_skill", "run_taught_skill", "memory.forget",
    "life_note.forget", "records.remove", "confirm_workspace_entry", "teamwork.confirm", "grocery.clear_checked",
    "scan_ports", "set_activity_noting", "world_watch.add", "grant.take_back", "steps.run"])
def test_a_kind_that_widens_her_reach_or_removes_something_never_gets_a_standing_yes(kind):
    assert kind_grants.always_asks(kind) and not kind_grants.grantable(kind)


@pytest.mark.parametrize("kind", ["routine.log", "expense.add", "grocery.add", "log_workout", "maintenance.done"])
def test_a_routine_entry_in_his_records_is_not_made_to_ask_by_that_rule(kind):
    assert not kind_grants.always_asks(kind)


def test_noting_a_use_cant_bring_back_a_yes_that_is_no_longer_in_force(monkeypatch):
    kept = {"setting.set": {"given": "2026-11-01T00:00:00", "last_used": "2026-11-01T00:00:00"}}
    monkeypatch.setattr(kind_grants, "_all", lambda context: {k: dict(v) for k, v in kept.items()})
    saved = []
    monkeypatch.setattr(kind_grants, "_save", lambda context, kinds: saved.append(kinds))
    kind_grants.used(None, "setting.set", now=datetime(2026, 11, 18))
    assert saved == []  # setting.set always asks now, so its old yes isn't refreshed


def test_while_everything_is_stopped_a_standing_yes_runs_nothing(monkeypatch):
    from core import actions, grants

    monkeypatch.setattr(stop, "_held_known", True)
    monkeypatch.setattr(stop, "_held_until", datetime.max)
    monkeypatch.setattr(grants, "tier_of", lambda capability: grants.WITHIN_GRANT)
    assert actions._may_run_now("routine.log") is False
    monkeypatch.setattr(stop, "_held_until", None)
    assert actions._may_run_now("routine.log") is True


# ------------------------------------------------------------------ the lab's rules


def test_the_protected_list_covers_every_manifest_and_ignores_case_and_slashes():
    hits = dev_lab.touches_protected(["apps/money/manifest.json", "Core\\Stop.py", "pytest.ini", "tests/conftest.py",
                                      "core/spoken_approval.py", "apps/money/screen.py", "core/notes.py"])
    assert hits == ["apps/money/manifest.json", "Core\\Stop.py", "pytest.ini", "tests/conftest.py",
                    "core/spoken_approval.py"]


def test_a_change_that_deletes_a_test_file_is_named():
    lines = ["M\tcore/notes.py", "D\ttests/test_notes.py", "A\ttests/test_new.py", "D\tdocs/old.md"]
    assert dev_lab.removed_tests(lines) == ["tests/test_notes.py"]


def test_an_error_in_the_suite_counts_as_a_failure_and_passed_tests_are_counted():
    out = "ERROR tests/test_x.py::test_a - fixture broke\n==== 4000 passed, 3 errors in 9s ===="
    result = dev_lab.suite_result(out)
    assert result["failed"] == ["tests/test_x.py::test_a"] and result["finished"]
    assert dev_lab.suite_result("==== 10 passed, 1 error in 1s ====")["failed"] == ["(the suite reported errors)"]
    assert dev_lab.passed_count("4000 passed, 3 errors in 9s") == 4000 and dev_lab.passed_count("no summary") is None


def test_a_merge_is_refused_while_everything_is_stopped(monkeypatch):
    monkeypatch.setattr(dev_lab, "get", lambda pid: SimpleNamespace(status=dev_lab.READY))
    stop._mark_on_disk({"since": "2026-11-18T10:00:00", "until": ""})
    with pytest.raises(ValueError, match="stopped"):
        dev_lab.approve("p1")


def test_the_stops_mark_is_read_by_any_process_and_ends_at_its_time():
    now = datetime(2026, 11, 18, 12, 0)
    assert stop.held_on_disk(now) is False
    stop._mark_on_disk({"since": "x", "until": (now + timedelta(hours=1)).isoformat()})
    assert stop.held_on_disk(now) is True and stop.held_on_disk(now + timedelta(hours=2)) is False
    stop._mark_on_disk({"since": "x", "until": "not a time"})
    assert stop.held_on_disk(now) is True  # unreadable: held
    stop._mark_on_disk(None)
    assert stop.held_on_disk(now) is False


# ------------------------------------------------------------------ her own merges


def _proposal(pid):
    """A ready stand-in proposal carrying Night School's evidence text."""
    return SimpleNamespace(proposal_id=pid, branch=f"lab/{pid}", status=dev_lab.READY, evidence=self_merges.SOURCE,
                           refused=[], title="t", problem="p", tests={}, merged_as="", note="")


def test_only_a_proposal_night_school_itself_made_can_go_in_on_a_pass():
    found = self_merges.candidates([_proposal("mine"), _proposal("someone_elses")], entries=[], kept={"mine"})
    assert [p.proposal_id for p in found] == ["mine"]


def test_a_change_too_large_to_review_whole_is_held_without_asking(tmp_path, monkeypatch):
    monkeypatch.setattr(self_merges, "night_schools_own", lambda: {"big"})
    asked, approved = [], []
    lab = SimpleNamespace(READY=dev_lab.READY, MERGED=dev_lab.MERGED, all_proposals=lambda: [_proposal("big")],
                          approve=lambda pid: approved.append(pid))
    done = self_merges.review_and_merge(lambda prompt: asked.append(prompt) or '{"verdict": "pass"}', self_merges.MERGER,
                                        lab=lab, diff=lambda pid: "x" * (self_merges.MAX_DIFF + 1),
                                        path=tmp_path / "m.json")
    assert asked == [] and approved == [] and done[0]["verdict"] == self_merges.HOLD
    assert "too large" in done[0]["findings"][0]


# ------------------------------------------------------------------ a spoken yes


def test_a_card_that_reaches_outside_or_cant_be_undone_needs_his_press(monkeypatch):
    from core import action_effects

    monkeypatch.setattr(action_effects, "effect_of", lambda kind: {"send.it": ("outside", "compensable"),
                                                                    "wipe.it": ("records", "irreversible")}.get(
        kind, ("records", "undoable")))
    assert spoken_approval.needs_press("send.it") and spoken_approval.needs_press("wipe.it")
    assert spoken_approval.needs_press("lab.approve") and not spoken_approval.needs_press("routine.log")


# ------------------------------------------------------------------ her reports to him


def test_the_reports_his_yes_rests_on_are_never_paused_away():
    assert {self_merges.TOPIC, "self_repair"} <= gate.NEVER_PAUSED


def test_a_change_that_fails_part_way_puts_back_what_it_had_written(tmp_path):
    """Prompt 21's Fable review (2026-11-18): a failure said "nothing was changed" while its first writes stayed."""
    from core import actions
    from core.atomic_write import atomic_write_text

    first, second = tmp_path / "first.json", tmp_path / "second.json"
    first.write_text('{"v": 1}', encoding="utf-8")

    def execute(context, params):
        """Writes one store, then breaks before the second."""
        atomic_write_text(first, '{"v": 2}')
        raise RuntimeError("the second store broke")

    actions.ACTION_TYPES["test.half_write"] = actions.ActionType("test.half_write", "Half", {}, lambda c, p: "Half", execute)
    try:
        center = actions.ActionCenter()
        ctx = SimpleNamespace(config=None)
        done = center.approve(ctx, center.propose(ctx, "test.half_write", {}).proposal_id)
        assert done.status == actions.FAILED and "nothing was changed" in done.result
        assert first.read_text(encoding="utf-8") == '{"v": 1}' and not second.exists()
    finally:
        actions.ACTION_TYPES.pop("test.half_write", None)
