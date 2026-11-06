"""The Chronicles' weekly issue (build plan step 17, core/chronicle_issue.py): told from approved series events, oldest
first; captions in code with the event named; lines from the model in the characters' voices; the Story Bible's five
rules checked in code; Zac's approval marks the events as told and lists the issue."""

import json
from pathlib import Path

import pytest

from core import chronicle_issue as ci
from core import saga


def event(root: Path, eid: str, at: str, **kw):
    e = {"id": eid, "at": at, "title": f"Event {eid}", "summary": "Claude Code and Codex shipped Night School for Zac.",
         "category": "milestone", "timeline": "real", "status": "built", "privacy": "series", "approved": "yes",
         "issue": None, "involved": ["claude", "codex", "zac"], "sources": ["dec:DEC-0100"], **kw}
    saga._save(e, root)
    return e


@pytest.fixture
def archive(tmp_path):
    root = tmp_path / "saga"
    event(root, "E-0002", "2026-11-06T10:00:00")
    event(root, "E-0001", "2026-11-05T10:00:00")
    event(root, "E-0003", "2026-11-06T11:00:00", privacy="private")
    event(root, "E-0004", "2026-11-06T12:00:00", status="planned", timeline="imagined", title="Sight on the glasses")
    return root


def test_the_cast_comes_from_the_bible():
    roster = ci.cast()
    assert {"MIA", "Forge", "Atlas", "Sentinel", "Ember", "Anvil"} <= set(roster)
    assert "gold light" in roster["Forge"]["appearance"] and roster["Forge"]["voice"]
    assert ci.series_name("claude", roster) == "Forge" and ci.series_name("codex", roster) == "Sentinel"
    assert ci.series_name("zac", roster) == "The Creator"
    assert ci._clean("Qwen Coder and Qwen helped Claude Code") == "Anvil and Ember helped Forge"


def test_the_material_follows_the_real_timeline(archive):
    assert [e["id"] for e in ci.material(archive)] == ["E-0001", "E-0002", "E-0004"]  # never the private one


def test_an_issue_in_code_with_the_models_lines(archive):
    asked = []

    def ask(prompt, schema):
        asked.append(prompt)
        return json.dumps({"lines": [{"who": "Forge", "line": "It passed. She'll study tonight."},
                                     {"who": "Sentinel", "line": "I checked twice."}]})
    issue = ci.draft(root=archive, ask=ask)
    assert issue["status"] == "checked" and issue["problems"] == [] and issue["events"] == ["E-0001", "E-0002", "E-0004"]
    first = issue["panels"][0]
    assert first["caption"] == "Forge and Sentinel shipped Night School for the Creator."
    assert first["who"] == ["MIA", "Forge", "Sentinel", "The Creator"] and first["real"]
    assert "Forge:" in asked[0] and "Claude" not in asked[0]
    planned = issue["panels"][2]
    assert not planned["real"] and planned["caption"].startswith("One day, perhaps:")  # rule 2: never shown as done


def test_continuity_catches_each_rule(archive):
    roster = ci.cast()
    events = {e["id"]: e for e in saga.events(archive)}
    bad = {"title": "Claude saves the day", "panels": [
        {"event": "E-0009", "real": True, "lines": [], "caption": ""},
        {"event": "E-0004", "real": True, "lines": [], "caption": ""},
        {"event": "E-0003", "real": True, "lines": [], "caption": ""},
        {"event": "E-0001", "real": True, "lines": [{"who": "Batman", "line": "Hi"}], "caption": ""}]}
    problems = " ".join(ci.check(bad, events, roster))
    for rule in ("(rule 1)", "(rule 2)", "(rule 3)", "(rule 4)", "(rule 5)"):
        assert rule in problems, rule


def test_a_line_with_a_real_name_keeps_it_a_draft(archive):
    issue = ci.draft(root=archive, ask=lambda p, s: json.dumps({"lines": [{"who": "Forge", "line": "Thanks, Codex!"}]}))
    assert issue["status"] == "draft" and "codex" in " ".join(issue["problems"])
    with pytest.raises(ValueError, match="continuity problems"):
        ci.approve(issue["id"], root=archive)


def test_zacs_yes(archive, tmp_path):
    bible = tmp_path / "bible"
    bible.mkdir()
    (bible / "issues.md").write_text("| # | Title | Week | Status | Events |\n|---|---|---|---|---|\n| — | *none yet* | | | |\n",
                                     encoding="utf-8")
    issue = ci.draft(root=archive, ask=False)  # no model: the captions carry it
    assert all(p["lines"] == [] for p in issue["panels"]) and issue["status"] == "checked"
    ci.approve(issue["id"], root=archive, bible=bible)
    assert {e["id"]: e["issue"] for e in saga.events(archive)}["E-0001"] == "I-0001"
    assert ci.material(archive) == []  # told: the next issue starts after them
    listing = (bible / "issues.md").read_text(encoding="utf-8")
    assert "| 001 | Event E-0001 |" in listing and "none yet" not in listing
    assert ci.panel_prompts(ci.issues(archive)[0])[0]["file"] == "I-0001-01.png"


def test_sundays_only_with_something_new(archive, monkeypatch):
    from datetime import date

    from core import loops

    monkeypatch.setattr(loops, "_has_repo", lambda: True)
    sunday = date(2026, 11, 8)
    assert ci.due(sunday, archive) and not ci.due(date(2026, 11, 9), archive)
    ci.draft(root=archive, ask=False, today=sunday)
    assert not ci.due(sunday, archive)  # one a week
