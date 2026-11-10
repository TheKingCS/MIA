"""What MIA can do and how she's built (DEC-0041): the capability map from
the code, "can you…?" answered from it (or "not that I can find", never a
guess), MIA's own docs searched with the file each answer came from, and a status per capability (DEC-0057:
a boundary by design isn't partial, a missing piece is partial until it's built, what broke is inferred, a planned piece is never said as working)."""

from types import SimpleNamespace

import pytest

from core.capabilities import AREAS, GIST, LIMITS, OVERVIEW_SKIP, can_i, capability_map, introduction, overview
from core.self_docs import SelfDocs, answer, build
from core.web_surfaces import APPS


@pytest.fixture(scope="module")
def ctx():
    """A context holding only the desktop's full tool registry."""
    from tests.assistant_registry import build_desktop_registry

    return SimpleNamespace(assistant_actions=build_desktop_registry())


def test_every_app_has_a_limits_entry():
    """Add a line to core/capabilities.LIMITS for a new app ("" if nothing's worth saying)."""
    missing = [a.module_id for a in APPS if a.module_id not in LIMITS]
    assert missing == []
    assert not set(LIMITS) - {a.module_id for a in APPS}  # no entries for apps that are gone


def test_every_app_is_in_one_overview_area():
    """Put a new app in core/capabilities.AREAS with a GIST (or in OVERVIEW_SKIP)."""
    from core.web_surfaces import RETIRED

    placed = [i for _area, ids in AREAS for i in ids]
    assert len(placed) == len(set(placed)) and not set(placed) & OVERVIEW_SKIP
    assert sorted(set(placed) | OVERVIEW_SKIP) == sorted(a.module_id for a in APPS if a.module_id not in RETIRED)
    assert set(GIST) == set(placed)


def test_the_overview_is_short_and_leaves_out_freedom(ctx):
    said = overview(ctx)
    assert "Money: bills, income, spending and debts" in said and "Try \"" in said
    assert "freedom" not in said.lower() and "survival" not in said.lower()
    assert len(said) < 1600


def test_tell_me_about_yourself_is_scripted(ctx):
    r = ctx.assistant_actions
    for q in ("Can you tell me about yourself?", "Who are you?", "What is MIA?"):
        assert r.direct_lookup(q).name == "get_introduction", q
    said = introduction(ctx)
    assert said.startswith("I'm MIA, your own assistant.") and "freedom" not in said.lower()
    assert "feel" not in said.lower()  # facts, not feelings (docs/design/MIA_VOICE.md rule 10)


def test_the_map_comes_from_the_code(ctx):
    apps = {a["id"]: a for a in capability_map(ctx)}
    assert apps["budget"]["where"] == "web and desktop" and "list_bills" in apps["budget"]["look_up"]
    assert "mark_bill_paid" in apps["budget"]["change"]
    assert apps["compliance"]["where"] == "web" and apps["diagnostics"]["where"] == "web and desktop"  # its own page (parity.PAGE_ELSEWHERE)
    assert apps["dashboard"]["where"] == "retired"
    said = overview(ctx)
    assert said.startswith("I have ") and "tax deadlines" in said and "Dashboard" not in said


def test_can_you_answers_from_the_map_or_says_it_cant(ctx):
    assert can_i(ctx, "track my chickens").startswith("Closest match in MIA: Chickens")
    taxes = can_i(ctx, "file my taxes")
    assert taxes.startswith("Closest match in MIA: Compliance") and "never files, pays or signs" in taxes
    assert "Workshop" in can_i(ctx, "sell banana bread at the market")
    assert can_i(ctx, "fly a drone").startswith("I can't find anything in MIA that does \"fly a drone\"")


def test_the_questions_reach_the_tools(ctx):
    from tests.assistant_registry import demo_context, offered_tools

    r = ctx.assistant_actions
    for q in ("What can you do?", "What are you capable of?", "What are your capabilities?", "what is mia capable of"):
        assert r.direct_lookup(q).name == "what_can_you_do", q
    for q in ("What did we decide about eggs?", "Why can't you connect my bank from the phone?"):
        assert r.named_action(q, offered_tools(r, q, demo_context())) == "get_mia_docs", q
    assert "get_capability" in offered_tools(r, "Can you track my chickens?", demo_context())
    assert "get_capability" not in offered_tools(r, "Add milk to the grocery list", demo_context())


def test_docs_search_ranks_decisions_and_labels_history(tmp_path):
    (tmp_path / "specs").mkdir()
    (tmp_path / "DECISIONS.md").write_text(
        "# Decisions\n\n### DEC-0001: Eggs go into cartons\n- Status: APPROVED\n- Decision: eggs are cartoned by the dozen.\n\n"
        "### DEC-0002: Ducks maybe\n- Status: PROPOSED\n- Decision: ducks lay eggs too.\n", encoding="utf-8")
    (tmp_path / "ROADMAP.md").write_text("## Old egg plan\nEggs were going to be sold by the each.\n", encoding="utf-8")
    (tmp_path / "NEXT_SESSION.md").write_text("## Eggs\nBuy egg cartons.\n", encoding="utf-8")
    (tmp_path / "specs" / "FARM.md").write_text("## Eggs\nThe spec asks for egg tracking.\n", encoding="utf-8")
    kinds = {p.heading: p.kind for p in build(tmp_path)}
    assert kinds["DEC-0001: Eggs go into cartons"] == "decision" and kinds["DEC-0002: Ducks maybe"] == "proposal"
    assert kinds["Old egg plan"] == "history" and "Eggs" in kinds  # the spec; NEXT_SESSION isn't indexed
    docs = SelfDocs(tmp_path)
    top = docs.search("What did we decide about eggs?")
    assert top[0][1].heading == "DEC-0001: Eggs go into cartons"
    said = answer("What did we decide about eggs?", docs)
    assert said.startswith("From my own documents, an approved decision: DEC-0001 (Eggs go into cartons) "
                           "(docs/DECISIONS.md). eggs are cartoned by the dozen.")
    assert "Related:" in said and "**" not in said
    assert answer("quantum chromodynamics", docs).startswith("Nothing in my own documents covers that")


def test_the_real_docs_answer_about_mia():
    top = SelfDocs().search("What did we decide about eggs?")
    assert top and top[0][1].heading.startswith("DEC-0037")


def test_she_answers_from_her_code_and_the_knowledge_vault(tmp_path):
    """Her code's docstrings and the vault's live entries are searched and labelled: a definition with no
    docstring and a withdrawn entry are left out, her own unconfirmed write-up says so, and a changed file rebuilds
    the index."""
    from core import dev_knowledge

    docs, code, vault = tmp_path / "docs", tmp_path, tmp_path / "work" / "knowledge"
    docs.mkdir()
    (code / "core").mkdir()
    (code / "core" / "hives.py").write_text(
        '"""core.hives\n\nBeehives."""\n\n\nclass Hive:\n    """One hive."""\n\n    def harvest(self):\n'
        '        """Takes the honey frames, leaving two for the winter."""\n\n    def _quiet(self):\n        pass\n',
        encoding="utf-8")
    dev_knowledge.add("decision", "Why two frames stay in the hive", "Bees need two frames of honey to winter well.",
                      ["dec:DEC-0001"], by="claude", status="confirmed", folder=vault)
    dev_knowledge.add("lesson", "Old frame rule", "Leave one frame.", ["dec:DEC-0001"], folder=vault)
    old = dev_knowledge.entries(vault)[1]["id"]
    dev_knowledge.withdraw(old, "claude", "wrong", folder=vault)
    dev_knowledge.add("lesson", "Smoke calms bees", "Use a little smoke.", ["dec:DEC-0001"], folder=vault)
    found = SelfDocs(docs, code=code, knowledge=vault)
    kinds = {p.heading: p.kind for p in found._fresh()}
    assert kinds["core.hives.Hive.harvest"] == "code" and kinds["core.hives"] == "code"
    assert "core.hives.Hive._quiet" not in kinds  # no docstring, nothing to say
    assert not any("Old frame rule" in h for h in kinds)  # withdrawn
    assert any(k == "derived" and "Smoke" in h for h, k in kinds.items())  # MIA's own, unconfirmed
    said = answer("How is the honey harvested?", found)
    assert said.startswith("From my own documents, my code's own documentation: core.hives.Hive.harvest "
                           "(core/hives.py). Takes the honey frames")
    assert "what the team learned building me" in answer("Why do two frames stay in the hive?", found)
    assert "not confirmed yet" in answer("Does smoke calm bees?", found)
    (code / "core" / "hives.py").write_text('"""core.hives\n\nBeehives, rewritten."""\n', encoding="utf-8")
    import os
    os.utime(code / "core" / "hives.py", (1, 1))  # a different time, whatever the clock's resolution
    assert "core.hives.Hive.harvest" not in {p.heading for p in found._fresh()}  # rebuilt on a change


def test_the_real_index_holds_her_code_and_vault():
    """The shared index holds the docs, the code and the vault, and a decision still outranks the code on its
    subject."""
    from core.self_docs import index

    kinds = {p.kind for p in index()._fresh()}
    assert {"decision", "code", "knowledge"} <= kinds
    assert index().search("What did we decide about eggs?")[0][1].heading.startswith("DEC-0037")



def test_an_app_with_a_web_page_never_says_it_has_none():
    from core.capabilities import LIMITS
    from core.web_surfaces import APPS

    wrong = [a.module_id for a in APPS if a.page and "no web screen" in LIMITS.get(a.module_id, "").lower()]
    assert not wrong, wrong


# --- a status per capability (DEC-0057) ------------------------------------

def _status(monkeypatch, gaps=None, failures=()):
    """Every capability's status with these parity gaps and these page errors this week, as {id: row}."""
    from core import capabilities

    monkeypatch.setattr(capabilities, "_parity_gaps", lambda: dict(gaps or {}))
    log = SimpleNamespace(events=lambda days=7: [{"kind": "page_error", "page": p} for p in failures])
    return {r["id"]: r for r in capabilities.capability_status(SimpleNamespace(failures=log), "pc")}, capabilities


def test_a_boundary_by_design_is_not_partial_and_only_a_missing_piece_or_device_is(monkeypatch):
    rows, _ = _status(monkeypatch)
    assert rows["compliance"]["status"] == "implemented" and "never files" in rows["compliance"]["limit"]
    assert all(r["status"] != "partial" or "yet" in r["why"] or "not on the" in r["why"] for r in rows.values())
    assert rows["greenhouse"]["status"] == "implemented"  # sensors send their own readings since 2026-11-09
    assert rows["dungeon"]["status"] == "implemented"  # shift differentials and tips counted since 2026-11-09


def test_what_broke_this_week_is_malfunctioning_and_said_as_inferred(monkeypatch):
    rows, _ = _status(monkeypatch, failures=["kitchen", "kitchen"])
    assert rows["kitchen"]["status"] == "malfunctioning" and rows["kitchen"]["evidence"] == "inferred"
    assert rows["kitchen"]["why"] == "it broke 2 times this week"


def test_a_planned_piece_is_never_said_as_working(monkeypatch):
    rows, capabilities = _status(monkeypatch, gaps={"sight:glasses": {"status": "todo", "why": "the glasses' camera"},
                                                     "passwords:voice": {"status": "none", "why": "never by voice"}})
    assert rows["sight:glasses"]["status"] == "planned" and rows["sight"]["status"] == "partial"
    assert rows["passwords"]["status"] != "planned"  # decided against isn't planned
    said = capabilities.status_summary(SimpleNamespace(), "pc")
    assert "Planned, not built yet: Look on the glasses" in said


def test_a_pc_app_or_one_decided_against_is_unavailable_on_another_device(monkeypatch):
    from core import capabilities

    monkeypatch.setattr(capabilities, "_parity_gaps", lambda: {"passwords:voice": {"status": "none", "why": "never by voice"}})
    by_voice = {r["id"]: r for r in capabilities.capability_status(SimpleNamespace(), "voice")}
    assert by_voice["passwords"]["status"] == "unavailable here" and by_voice["passwords"]["why"] == "never by voice"


def test_the_weekly_report_ends_with_the_state_of_her_apps(monkeypatch):
    from core import self_report

    _status(monkeypatch)
    line = self_report._apps_line(SimpleNamespace())
    assert line.startswith("My apps: ") and " working, " in line and line.endswith("planned.")
