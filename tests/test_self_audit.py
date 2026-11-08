"""
tests.test_self_audit
=======================

MIA's weekly self-audit (core/self_audit.py) and her best-practices series
(core/practices.py), DEC-0108: what the code audit finds, what the
interconnection audit finds and leaves out by design, the docs audit's task, the weekly run's
report and tasks, and the series written from the principles and the vault.
"""

from __future__ import annotations

from core import dev_knowledge, practices
from core import self_audit as sa
from core.dev_store import DevStore

LONG_BODY = "\n".join(f"    x{i} = {i}" for i in range(sa.LONG + 2))
SHARED = "    total = 0\n" + "\n".join(f"    total += {i}" for i in range(sa.SAME_BODY)) + "\n    return total\n"


def _code(root):
    """A tiny codebase with one of each thing the audit looks for."""
    (root / "core").mkdir()
    (root / "core" / "a.py").write_text(
        '"""a."""\n\n\ndef long_one():\n' + LONG_BODY + "\n\n\n"
        "def many(a, b, c, d, e, f, g, h, i):\n    return a\n\n\n"
        "def nested(x):\n    if x:\n        for y in x:\n            while y:\n                with y:\n"
        "                    if y:\n                        return y\n\n\n"
        "def quiet():\n    try:\n        return 1\n    except Exception:\n        pass\n\n\n"
        "def adds():\n" + SHARED + "\n# TODO: something later\n", encoding="utf-8")
    (root / "core" / "b.py").write_text('"""b."""\n\n\ndef adds_too():\n' + SHARED, encoding="utf-8")
    (root / "core" / "fine.py").write_text('"""fine."""\n\n\ndef f(self, a):\n    return a\n', encoding="utf-8")


def test_the_code_audit_finds_each_kind_of_place_to_look(tmp_path):
    """Long, many-parameter, deeply nested, silent and duplicated functions and TODOs are found, each with a stable
    id; a small tidy file isn't."""
    _code(tmp_path)
    found = sa.code_findings(tmp_path)
    kinds = {(f["kind"], f["name"]) for f in found}
    assert {("long_function", "long_one"), ("many_params", "many"), ("deep_nesting", "nested"),
            ("silent_except", "core/a.py"), ("todo", "core/a.py")} <= kinds
    same = [f for f in found if f["kind"] == "same_body"]
    assert len(same) == 1 and "adds_too in core/b.py" in same[0]["detail"]
    assert not any(f["file"] == "core/fine.py" for f in found)
    assert all(f["id"] == f"{f['kind']}:{f['file']}:{f['name']}" for f in found)
    assert found == sorted(found, key=lambda f: (-f["weight"], f["file"], f["line"]))


def test_connections_leave_out_what_a_store_goes_without_on_purpose(tmp_path):
    """A store missing connections is a finding (more missing weighs more); BY_DESIGN's are never findings or
    counted against the share; an event nobody hears or nobody sends is a finding."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "x.py").write_text(
        'def f(context):\n    context.events.publish("thing.done")\n    context.events.subscribe("never.sent", f)\n',
        encoding="utf-8")
    full = dict(history=True, links=True, assistant=True, life_state=True, web=True)
    rows = [{"store": "budget", "class": "BudgetManager", **full},
            {"store": "boss_book", "class": "BossBook", **dict(full, links=False, web=False)},
            {"store": "passwords", "class": "PasswordVault", **dict(full, history=False, links=False, assistant=False,
                                                                     life_state=False)}]
    found = sa.connection_findings(tmp_path, rows)
    ids = [f["id"] for f in found]
    assert "store:boss_book" in ids and "store:budget" not in ids and "store:passwords" not in ids
    boss = next(f for f in found if f["id"] == "store:boss_book")
    assert boss["missing"] == ["links", "web"] and "can't depend on" in boss["detail"]
    assert {"event:thing.done", "event:never.sent"} <= set(ids)
    assert sa.connected_share(rows) == round(9 / 11, 3)  # 5 + 5 wanted, and only the web page of the passwords


def test_the_weekly_audit_keeps_a_report_opens_tasks_once_and_writes_the_practices(tmp_path, monkeypatch):
    """The report is kept and due() waits a week; one task per audit for its top finding, and none again for a
    finding that already has one; the practices are written where asked."""
    _code(tmp_path)
    monkeypatch.setattr(sa, "store_connections", lambda root: [
        {"store": "boss_book", "class": "BossBook", "history": False, "links": False, "assistant": True,
         "life_state": False, "web": True}])
    store, tasks, log = DevStore(tmp_path / "audit"), tmp_path / "tasks", tmp_path / "activity.jsonl"
    assert sa.due(store=store)
    report = sa.weekly(tmp_path, store=store, tasks_dir=tasks, log=log, practices_out=tmp_path / "practices")
    assert report["code"]["findings"] >= 6 and report["connections"]["share"] == 0.4 and len(report["tasks"]) == 2
    assert sa.latest(store)["tasks"] == report["tasks"] and not sa.due(store=store)
    assert (tmp_path / "practices" / "README.md").exists() and "audit" in log.read_text(encoding="utf-8")
    again = sa.weekly(tmp_path, store=store, tasks_dir=tasks, log=log, practices_out=tmp_path / "practices")
    assert again["tasks"] and not set(again["tasks"]) & set(report["tasks"])  # the next findings, not the same ones


def test_every_by_design_store_is_a_real_store():
    """BY_DESIGN names only stores that exist, and only connections the audit knows."""
    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

    names = {n for n, _c in PERSONAL_STORES + HOUSEHOLD_STORES}
    assert set(sa.BY_DESIGN) <= names
    assert all(set(kinds) <= set(sa.CONNECTION_WHY) and why for kinds, why in sa.BY_DESIGN.values())


def test_the_practices_gather_what_was_learned(tmp_path):
    """An entry lands in each area it teaches, by the files it concerns or its title; withdrawn ones never, MIA's
    own unconfirmed ones apart; the front page counts the lessons."""
    vault = tmp_path / "vault"
    dev_knowledge.add("lesson", "Never choose settings on the scoring set", "What happened: it flattered the model. More.",
                      ["dec:DEC-0106"], ["core/model_forge.py"], by="claude", status="confirmed", folder=vault)
    dev_knowledge.add("lesson", "A flaky test hides a race", "It did.", ["dec:DEC-0001"], ["tests/test_x.py"],
                      folder=vault)
    dev_knowledge.add("lesson", "Old model advice", "Wrong.", ["dec:DEC-0001"], ["core/model_forge.py"],
                      by="claude", status="confirmed", folder=vault)
    old = next(e["id"] for e in dev_knowledge.entries(vault) if e["title"] == "Old model advice")
    dev_knowledge.withdraw(old, "claude", "wrong", folder=vault)
    said = practices.write(tmp_path / "out", vault)
    ai = (tmp_path / "out" / "ai_building.md").read_text(encoding="utf-8")
    assert "**Never choose settings on the scoring set**" in ai and ": it flattered the model." in ai
    assert "Old model advice" not in ai
    testing = (tmp_path / "out" / "testing.md").read_text(encoding="utf-8")
    assert "Her own write-ups, not confirmed yet" in testing and "A flaky test hides a race" in testing
    front = (tmp_path / "out" / "README.md").read_text(encoding="utf-8")
    assert "[Building AI](ai_building.md)" in front and "1 lesson learned" in front
    assert said == f"{len(practices.AREAS)} areas, 1 lessons placed"
    assert len({a.id for a in practices.AREAS}) == len(practices.AREAS) and all(a.principles for a in practices.AREAS)


def test_the_weekly_audit_opens_a_task_for_a_doc_that_disagrees_with_the_repository(tmp_path, monkeypatch):
    """The docs audit is the third: its top finding becomes one task, naming the doc to fix."""
    from core import work_tasks

    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "GUIDE.md").write_text("See `core/gone.py`.\n", encoding="utf-8")
    monkeypatch.setattr(sa, "store_connections", lambda root: [])
    report = sa.weekly(tmp_path, store=DevStore(tmp_path / "audit"), tasks_dir=tmp_path / "tasks",
                       log=tmp_path / "activity.jsonl", practices_out=tmp_path / "practices")
    assert report["docs"]["findings"] == 1 and len(report["tasks"]) == 1
    task = work_tasks.load(tmp_path / "tasks")[report["tasks"][0]]
    assert task.source == "audit:doc:docs/GUIDE.md:core/gone.py" and task.files == ["docs/GUIDE.md"]
