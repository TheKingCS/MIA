"""Every process MIA has is watched by a loop or has a reason not to be (DEC-0101,
core/loop_coverage.py). When this fails, something new joined MIA without anyone
deciding how it will be watched: give it a loop in core/loops.py (its `covers`)
or a line in work/loop_coverage.json (status todo, or none with a why)."""

from core import loop_coverage


def test_every_process_is_accounted_for():
    r = loop_coverage.report()
    new = [row["id"] for row in r["rows"] if row["state"] == "new"]
    assert not new, ("New processes nobody has decided how to watch: " + ", ".join(new) +
                     ". Give each a loop (core/loops.py, covers=) or a line in work/loop_coverage.json.")
    assert not r["unknown_covers"], "Loops cover processes that don't exist: " + ", ".join(r["unknown_covers"])


def test_a_decline_needs_a_reason():
    for pid, entry in loop_coverage.decisions().items():
        assert entry.get("status") in loop_coverage.STATUSES, pid
        if entry["status"] == "none":
            assert entry.get("why"), f"{pid} is declined without saying why"
        if entry["status"] == "proposed":
            assert entry.get("task"), f"{pid} is proposed without its task"


def test_the_inventory_reads_the_code(tmp_path):
    every = loop_coverage.processes()
    assert "store:journal" in every and "check:loops" in every and "module:notes" in every
    assert "action:bill" in every and "flow:talk" in every and "dev:night_school" in every
    path = tmp_path / "coverage.json"
    loop_coverage.save_decisions({"store:private_journal": {"status": "none", "why": "private: never measured"}}, path)
    rows = {r["id"]: r for r in loop_coverage.report(path=path)["rows"]}
    assert rows["store:private_journal"]["state"] == "declined" and rows["flow:talk"]["state"] == "covered"
    assert rows["store:passwords"]["state"] == "new" and rows["module:notes"]["state"] == "covered"  # screens.broken
    loop_coverage.mark(["store:passwords"], "proposed", task="T-0099", path=path)
    assert loop_coverage.decisions(path)["store:passwords"] == {"status": "proposed", "task": "T-0099"}


def test_the_corrections_loops_cover_their_areas_action_families():
    rows = {r["id"]: r for r in loop_coverage.report()["rows"]}
    assert rows["action:bill"]["loops"] == ["corrections.money"] and rows["action:recipe"]["loops"] == ["corrections.kitchen"]
    assert rows["action:playlist"]["loops"] == ["corrections.music"] and rows["store:relationships"]["loops"] == [
        "corrections.people"]  # a store, by the hand-chosen list


def test_the_hand_chosen_corrections_list_names_real_processes():
    from core.corrections import AREAS

    every = loop_coverage.processes()
    assert not [p for p in loop_coverage.CORRECTED_IN if p not in every]  # a renamed store or app: update the list
    assert set(loop_coverage.CORRECTED_IN.values()) <= set(AREAS)
