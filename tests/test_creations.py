"""ACAF's first working demonstration (DEC-0088 to DEC-0091): from one
sentence about information MIA has no screen for, she makes a record set and
a screen, checked, previewed, published on approval, used, undone and
rolled back, all through her own design system and the action contract."""

import json

import pytest

from core import blueprints, creation_maker, creation_spec
from core.creations import Creations
from core.record_sets import RecordError, RecordSets, coerce
from tests.engine_world import build_world

DESIGN = {"title": "Seed Bank", "icon": "greenhouse", "about": "Seeds saved for next season.", "owner": "household",
          "set_name": "Seeds", "blueprint": "tracker",
          "fields": [{"name": "variety", "label": "Variety", "type": "text"},
                     {"name": "saved_on", "label": "Saved on", "type": "date"},
                     {"name": "count", "label": "How many", "type": "number"},
                     {"name": "germination", "label": "Germination", "type": "choice", "choices": ["Good", "Fair", "Poor"]}]}


@pytest.fixture
def world(tmp_path, monkeypatch):
    w = build_world(tmp_path, monkeypatch)
    w.creations = Creations(w, data_dir=w.my_dir)
    w.record_sets = RecordSets(w, data_dir=w.home_dir)
    w.my_record_sets = RecordSets(w, data_dir=w.my_dir)
    from core.actions import ActionCenter

    w.actions = ActionCenter()
    return w


def model(*designs):
    """A stand-in for MIA's local model: the designs it gives, in order."""
    replies = [json.dumps(d) for d in designs]
    asked = []

    def ask(prompt, schema):
        asked.append(prompt)
        return replies.pop(0)
    ask.asked = asked
    return ask


def act(w, kind, params):
    proposal = w.actions.propose(w, kind, params)
    return w.actions.approve(w, proposal.proposal_id)


def test_from_one_sentence_to_a_working_screen(world):
    w = world
    ask = model(DESIGN)
    made = creation_maker.make(w, "I want to keep track of the seeds I save, when, how many and how they germinate", ask=ask)
    assert made["status"] == "draft" and made["id"] == "C-0001" and "tracker" in made["versions"][-1]["blueprint"]
    assert w.record_sets.sets == []  # a draft changes no data
    spec = made["versions"][-1]["spec"]
    assert creation_spec.check(spec) == []
    preview = creation_spec.assemble(spec, None, money=lambda v: f"${v:,.2f}")
    assert [b["block"] for b in preview["blocks"]] == ["stats", "chart", "table", "form"]

    done = act(w, "creation.publish", {"creation_id": "C-0001"})
    assert done.status == "executed" and w.creations.get("C-0001")["status"] == "published"
    seeds = w.record_sets.sets[0]
    assert seeds["name"] == "Seeds" and (w.home_dir / "record_sets.json").exists()  # the household's, as designed

    for variety, when, n, g in (("Cherokee Purple", "2026-09-01", 40, "Good"), ("Moon and Stars", "2026-09-20", 25, "Fair"),
                                ("Hopi Blue", "2026-10-02", 60, "Good")):
        assert act(w, "records.add", {"creation_id": "C-0001", "values": {"variety": variety, "saved_on": when,
                                                                          "count": n, "germination": g}}).status == "executed"
    screen = creation_spec.assemble(w.creations.shown("C-0001")["spec"], w.record_sets.get(seeds["id"]),
                                    money=lambda v: f"${v:,.2f}")
    stats = {i["label"]: i["value"] for i in screen["blocks"][0]["items"]}
    assert stats == {"Kept": "3", "Latest": "Hopi Blue", "Total how many": "125"}
    chart = screen["blocks"][1]
    assert {p["label"]: p["value"] for p in chart["points"]} == {"Fair": 1, "Good": 2} and "Good: 2" in chart["text"]
    table = screen["blocks"][2]
    assert table["columns"] == ["Variety", "Saved on", "How many", "Germination"]
    assert [r["cells"][0] for r in table["rows"]] == ["Hopi Blue", "Moon and Stars", "Cherokee Purple"]  # newest saved first

    from core.undo_log import undo_last
    from core.person_settings import person_id

    undo_last(w, person_id(w))  # "undo that": the last record goes
    w.record_sets._load()
    assert len(w.record_sets.get(seeds["id"])["records"]) == 2


def test_a_new_version_waits_for_approval_and_rolls_back(world):
    w = world
    creation_maker.make(w, "keep track of the seeds I save please", ask=model(DESIGN))
    act(w, "creation.publish", {"creation_id": "C-0001"})
    v2 = {**w.creations.latest("C-0001")["spec"], "title": "Seed Vault",
          "blocks": [{"block": "cards", "title_field": "variety", "detail_fields": ["germination"]}, {"block": "form"}]}
    w.creations.draft(v2, creation_spec.check(v2), why="cards are nicer", creation_id="C-0001")
    assert w.creations.shown("C-0001")["version"] == 1  # the sidebar keeps version 1 until it's approved
    act(w, "creation.publish", {"creation_id": "C-0001"})
    assert w.creations.get("C-0001")["title"] == "Seed Vault" and len(w.record_sets.sets) == 1  # same records
    act(w, "creation.rollback", {"creation_id": "C-0001"})
    assert w.creations.get("C-0001")["version"] == 1 and w.creations.get("C-0001")["title"] == "Seed Bank"


def test_her_own_layout_is_used_when_it_passes_and_the_blueprint_when_it_doesnt():
    bps = blueprints.load()
    own = {**DESIGN, "blocks": [{"block": "timeline", "date_field": "saved_on", "title_field": "variety"}, {"block": "form"}]}
    spec, used = creation_maker.spec_from(own, bps)
    assert used == "" and [b["block"] for b in spec["blocks"]] == ["timeline", "form"]  # a combination no blueprint has
    bad = {**DESIGN, "blocks": [{"block": "chart", "type": "pie", "x": "nope"}]}
    spec, used = creation_maker.spec_from(bad, bps)
    assert used == "tracker@1" and creation_spec.check(spec) == []


def test_a_failing_design_goes_back_once_with_the_reasons(world):
    broken = {**DESIGN, "fields": [{"name": "Variety Name", "label": "V", "type": "colour"}]}
    ask = model(broken, DESIGN)
    made = creation_maker.make(world, "keep track of the seeds I save please", ask=ask)
    assert made["status"] == "draft" and "had these problems" in ask.asked[1]
    with pytest.raises(creation_maker.MakerError, match="passes its checks"):
        creation_maker.make(world, "keep track of the seeds I save please", ask=model(broken, broken))


def test_the_checker_refuses_what_a_screen_may_not_do():
    spec, _ = creation_maker.spec_from(DESIGN, blueprints.load())
    assert creation_spec.check({**spec, "html": "<script>"}) == ["Unknown part 'html'."]
    sneaky = {**spec, "blocks": [{"block": "table", "columns": ["variety"], "onclick": "x"}]}
    assert any("unknown part 'onclick'" in p for p in creation_spec.check(sneaky))
    assert any("sum needs a number" in p for p in creation_spec.check(
        {**spec, "blocks": [{"block": "stats", "items": [{"label": "x", "value": {"sum": "variety"}}]}, {"block": "form"}]}))
    assert any("no field 'price'" in p for p in creation_spec.check(
        {**spec, "blocks": [{"block": "table", "columns": ["price"]}]}))
    money = {**spec, "owner": "personal", "record_set": {"name": "x", "fields": [{"name": "cost", "type": "money"}]},
             "blocks": [{"block": "table", "columns": ["cost"]}]}
    assert creation_spec.check(money) == []
    assert "Money doesn't go on a child's screen." in creation_spec.check(money, child=True)
    assert "A child's screens are their own, not the household's." in creation_spec.check(spec, child=True)
    assert any("a line runs over a date" in p for p in creation_spec.check(
        {**spec, "blocks": [{"block": "chart", "type": "line", "x": "variety", "y": {"count": True}}, {"block": "form"}]}))


def test_nothing_publishes_that_no_longer_passes(world):
    w = world
    made = creation_maker.make(w, "keep track of the seeds I save please", ask=model(DESIGN))
    made["versions"][-1]["spec"]["blocks"] = [{"block": "chart", "type": "pie"}]  # changed behind its back
    with pytest.raises(Exception):
        act_result = act(w, "creation.publish", {"creation_id": made["id"]})
        assert act_result.status == "failed"
        raise RuntimeError
    assert w.creations.get(made["id"])["status"] == "draft" and w.record_sets.sets == []


def test_records_keep_their_types():
    assert coerce({"name": "n", "type": "money"}, "$1,250.50") == 1250.5
    assert coerce({"name": "d", "type": "date"}, "2026-11-04T10:00") == "2026-11-04"
    assert coerce({"name": "c", "type": "choice", "choices": ["Good", "Fair"]}, "good") == "Good"
    with pytest.raises(RecordError):
        coerce({"name": "c", "label": "Germination", "type": "choice", "choices": ["Good"]}, "great")
    with pytest.raises(RecordError):
        coerce({"name": "n", "label": "How many", "type": "number"}, "lots")


def test_published_creations_join_the_sidebar(world):
    from core.web_surfaces import shell

    w = world
    creation_maker.make(w, "keep track of the seeds I save please", ask=model(DESIGN))
    assert shell(w)["made"] == []
    act(w, "creation.publish", {"creation_id": "C-0001"})
    assert shell(w)["made"] == [{"id": "C-0001", "name": "Seed Bank", "icon": "greenhouse", "page": "made.html?id=C-0001"}]


def test_the_blueprints_are_valid_and_fill_from_any_fields():
    bps = blueprints.load()
    assert set(bps) == {"tracker", "log", "collection"}
    only_text = [{"name": "idea", "label": "Idea", "type": "text"}]
    for bp in bps.values():
        blocks = blueprints.fill(bp, only_text)
        spec = {"kind": "screen", "title": "Ideas", "owner": "personal",
                "record_set": {"name": "Ideas", "fields": only_text}, "blocks": blocks}
        assert creation_spec.check(spec) == [] or bp["id"] == "log", bp["id"]  # a log needs a date and a number


def test_the_whole_way_through_the_server(tmp_path, monkeypatch):
    """The demonstration over the real API: make a draft from a sentence, see it, publish it, add a
    record from its form, find it in the sidebar; a child can't make one."""
    import core.creations
    import core.record_sets
    from tests import test_server_app as srv

    monkeypatch.setattr(core.record_sets, "_DATA_DIR", tmp_path / "rs")
    monkeypatch.setattr(core.creations, "_DATA_DIR", tmp_path / "cr")
    monkeypatch.setattr(creation_maker, "_ollama", model(DESIGN))
    context = srv.context.__wrapped__(tmp_path, monkeypatch) if hasattr(srv.context, "__wrapped__") else None
    if context is None:
        pytest.skip("server fixture shape changed")
    from fastapi.testclient import TestClient

    client = TestClient(srv.server_app_module.create_app(context))
    token = srv._login(client, context)
    auth = {"Authorization": f"Bearer {token}"}
    made = client.post("/api/made", json={"need": "I want to keep track of the seeds I save"}, headers=auth)
    assert made.status_code == 200, made.text
    cid = made.json()["id"]
    page = client.get(f"/api/made/{cid}", headers=auth).json()
    assert page["status"] == "draft" and page["screen"]["title"] == "Seed Bank"
    assert [b["block"] for b in page["screen"]["blocks"]] == ["stats", "chart", "table", "form"]
    for kind, params in (("creation.publish", {"creation_id": cid}),
                         ("records.add", {"creation_id": cid, "values": {"variety": "Hopi Blue", "count": "60"}})):
        p = client.post("/api/actions/propose", json={"kind": kind, "params": params}, headers=auth).json()
        done = client.post(f"/api/actions/{p['proposal_id']}/approve", headers=auth).json()
        assert done["status"] == "executed", done.get("result")
    page = client.get(f"/api/made/{cid}", headers=auth).json()
    assert page["status"] == "published" and page["screen"]["records"] == 1
    assert page["screen"]["blocks"][2]["rows"][0]["cells"][:1] == ["Hopi Blue"]
    shell = client.get("/api/shell", headers=auth).json()
    assert {"id": cid, "name": "Seed Bank", "icon": "greenhouse", "page": f"made.html?id={cid}"} in shell["made"]
    assert client.get("/api/made/C-9999", headers=auth).status_code == 404


def _history(w, kind, summary, payload):
    from core import life_events

    class Here:  # the household's folder, as a store would be
        data_dir = w.home_dir
    life_events.record(Here(), kind, summary, payload=payload)


def test_a_screen_over_history_she_already_keeps(world):
    """ACAF step 2: "how many eggs a week?" needs no new store: it reads the history (core/creation_sources.py)."""
    w = world
    for day, n in (("2026-10-26", 6), ("2026-10-27", 7), ("2026-11-02", 5), ("2026-11-03", 8)):
        _history(w, "eggs_collected", f"Collected {n} eggs", {"eggs": n, "date": day})
    eggs = {"title": "Eggs by Week", "icon": "flock", "owner": "household", "set_name": "", "fields": [],
            "blueprint": "log", "source": "eggs",
            "blocks": [{"block": "stats", "items": [{"label": "Eggs", "value": {"sum": "eggs"}}]},
                       {"block": "chart", "type": "bar", "x": "date", "by": "week", "y": {"sum": "eggs"}}]}
    made = creation_maker.make(w, "show me how many eggs we get each week", ask=model(eggs))
    spec = made["versions"][-1]["spec"]
    assert spec["source"] == "history:eggs" and "record_set" not in spec and creation_spec.check(spec) == []
    from core import creation_sources

    screen = creation_spec.assemble(spec, {"records": creation_sources.records(w, "eggs")}, money=str)
    assert screen["blocks"][0]["items"][0]["value"] == "26"
    assert {p["label"]: p["value"] for p in screen["blocks"][1]["points"]} == {"Week of Oct 26": 13, "Week of Nov 2": 13}
    done = act(w, "creation.publish", {"creation_id": made["id"]})
    assert done.status == "executed" and w.record_sets.sets == []  # nothing new stored
    refused = w.actions.propose  # adding goes to the app that keeps it
    from core.actions import ActionError

    with pytest.raises(ActionError, match="add to it in Chickens"):
        refused(w, "records.add", {"creation_id": made["id"], "values": {"eggs": 3}})


def test_sources_keep_their_rules():
    base = {"kind": "screen", "title": "Spend", "owner": "personal", "source": "history:spending",
            "blocks": [{"block": "stats", "items": [{"label": "Spent", "value": {"sum": "amount"}}]}]}
    assert creation_spec.check(base) == []
    assert "Money doesn't go on a child's screen." in creation_spec.check(base, child=True)
    assert any("no form" in p for p in creation_spec.check({**base, "blocks": base["blocks"] + [{"block": "form"}]}))
    assert any("There's no source" in p for p in creation_spec.check({**base, "source": "history:passwords"}))
    assert any("by is day, week or month" in p for p in creation_spec.check(
        {**base, "blocks": [{"block": "chart", "type": "bar", "x": "category", "by": "week", "y": {"count": True}}]}))
    from core import creation_sources

    assert "spending" not in creation_sources.describe(child=True) and "eggs" in creation_sources.describe(child=True)


def test_code_points_the_model_at_history_and_the_period_asked_for():
    from core import creation_sources

    assert creation_sources.matching("how many eggs do the hens lay") == ["eggs"]
    assert creation_sources.matching("what did I spend on bills") == ["spending", "bills_paid"]
    assert creation_sources.matching("what did I spend", child=True) == []  # money isn't offered to a child
    spec, _ = creation_maker.spec_from({"title": "Eggs", "owner": "household", "source": "eggs", "blueprint": "log"},
                                       blueprints.load(), "eggs each week")
    chart = next(b for b in spec["blocks"] if b["block"] == "chart")
    assert chart["by"] == "week" and not any(b["block"] == "form" for b in spec["blocks"])
