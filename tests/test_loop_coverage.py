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
    loop_coverage.save_decisions({"store:journal": {"status": "none", "why": "private: never measured"}}, path)
    rows = {r["id"]: r for r in loop_coverage.report(path=path)["rows"]}
    assert rows["store:journal"]["state"] == "declined" and rows["flow:talk"]["state"] == "covered"
    assert rows["module:notes"]["state"] == "new"
    loop_coverage.mark(["module:notes"], "proposed", task="T-0099", path=path)
    assert loop_coverage.decisions(path)["module:notes"] == {"status": "proposed", "task": "T-0099"}
