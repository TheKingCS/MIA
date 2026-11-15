"""
tests.test_relevance
======================

World Intelligence's relevance from the person's own records (W2, DEC-0170; core/relevance.py): a find that fits a
goal, a project or the homestead plan's next step scores above one that only matched a watch, with a reason naming
each record; it can fit several at once; a long record name needs two of its words, not one; finished and paused
records stop pulling; and finds waiting to be offered are re-ranked as the records change.
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from core import relevance
from core.relevance import Anchor, words_of
from core.world_intel import WorldBook

NOW = datetime(2026, 11, 15, 9, 0)


def test_significant_words_drop_common_ones_and_fold_plurals():
    assert words_of("Polycarbonate Panels for the Greenhouse") == {"polycarbonate", "panel", "greenhouse"}
    assert words_of("glass") == {"glass"}  # "ss" isn't a plural


def test_a_find_fitting_several_records_counts_each_and_names_them():
    anchors = [Anchor("project:p1", "your project “Greenhouse”", words_of("Greenhouse"), 3),
               Anchor("intent:i1", "your goal “Grow our own food”", words_of("Grow our own food"), 4),
               Anchor("asset:a1", "your Raspberry Pi 5", words_of("Raspberry Pi 5 Raspberry"), 1)]
    points, reasons, refs = relevance.relevance("A Raspberry Pi greenhouse sensor that helps you grow food", anchors)
    assert refs == ["project:p1", "intent:i1", "asset:a1"]
    assert reasons[0] == "fits your project “Greenhouse” (greenhouse)" and points == 3 + 4 * 2 + 1


def test_a_long_record_needs_two_of_its_words_not_one():
    a = [Anchor("project:p", "your project “Garden beds for the south field”", words_of("Garden beds for the south field"), 3)]
    assert relevance.relevance("Ten garden tips for winter", a) == (0.0, [], [])
    assert relevance.relevance("Raised garden beds on a budget", a)[2] == ["project:p"]


def _context():
    """Stand-in stores: one open goal, one live project, one finished project, an active and a done mission."""
    intents = SimpleNamespace(all_intents=lambda: [SimpleNamespace(intent_id="i1", name="Grow our own food",
                                                                   description="", status="Active", primary=True)])
    projects = SimpleNamespace(all_projects=lambda: [
        SimpleNamespace(project_id="p1", name="Greenhouse", description="polycarbonate panels", status="Active"),
        SimpleNamespace(project_id="p2", name="Chicken coop", description="", status="Complete")])
    missions = SimpleNamespace(all_missions=lambda: [SimpleNamespace(mission_id="m1", name="Aquaponics pump", status="active"),
                                                     SimpleNamespace(mission_id="m2", name="Old thing", status="completed")])
    return SimpleNamespace(intents=intents, projects=projects, missions=missions)


def test_anchors_come_from_open_records_only():
    refs = {a.ref for a in relevance.anchors(_context())}
    assert {"intent:i1", "project:p1", "mission:m1"} <= refs
    assert "project:p2" not in refs and "mission:m2" not in refs
    assert next(a for a in relevance.anchors(_context()) if a.ref == "intent:i1").weight == 4  # the main goal


def test_the_homestead_plans_next_step_is_the_strongest_anchor(monkeypatch):
    from core import development_engine

    monkeypatch.setattr(development_engine, "plan", lambda context: {"next": {
        "id": "seed_shelf", "name": "A seed-starting shelf", "goal": {"id": "starts", "name": "Selling plant starts"}}})
    found = {a.ref: a for a in relevance.anchors(SimpleNamespace())}
    assert found["plan:seed_shelf"].weight == 4 and "next step" in found["plan:seed_shelf"].label
    assert found["plan_goal:seed_shelf"].weight == 3


def test_a_find_that_fits_the_records_outranks_one_that_only_matched_the_watch_and_is_reranked(tmp_path):
    book = WorldBook(MagicMock(), data_dir=tmp_path)
    w = book.add_watch("Panels", "panels")
    anchors = relevance.anchors(_context())
    fit = {"source": "hobby_farms", "title": "Polycarbonate panels for a greenhouse", "link": "https://e.org/a",
           "summary": ""}
    plain = {"source": "electrek", "title": "Solar panels get cheaper", "link": "https://e.org/b", "summary": ""}
    book.ingest([{"watch_id": w.watch_id, "items": [(plain, ["panels"]), (fit, ["panels"])]}], NOW, anchors)
    best = book.offers(NOW)[0]
    assert best.title.startswith("Polycarbonate") and best.refs == ["project:p1"] and best.fits
    assert "fits your project “Greenhouse” (greenhouse, panel, polycarbonate)" in best.why
    assert book.rescore([], NOW) == 1  # the project finished: the find no longer fits it
    assert book.get(best.discovery_id).refs == [] and not book.get(best.discovery_id).fits


# ------------------------------------------------------------------ watches MIA makes herself (W1b)


def test_mia_makes_a_watch_for_each_open_record_and_never_searches_with_it(tmp_path):
    book = WorldBook(MagicMock(), data_dir=tmp_path)
    made, removed = book.sync_own_watches(relevance.anchors(_context()), NOW)
    names = {w.name for w in made}
    assert {"Grow our own food", "Greenhouse", "Aquaponics pump"} <= names and removed == []
    mine = book.find_watch("Greenhouse")
    assert mine.made_by == "mia" and mine.reason == "For your project “Greenhouse”." and mine.refs == ["project:p1"]
    assert not any(w.search for w in made)  # feeds are matched on the PC: none of their words go out
    assert book.own_synced == NOW.date().isoformat()
    again, _ = book.sync_own_watches(relevance.anchors(_context()), NOW)
    assert again == []  # one per record


def test_her_watch_stops_with_its_record_and_one_the_person_stops_is_never_made_again(tmp_path):
    book = WorldBook(MagicMock(), data_dir=tmp_path)
    book.sync_own_watches(relevance.anchors(_context()), NOW)
    goal = book.find_watch("Grow our own food")
    book.remove_watch(goal.watch_id)
    assert "intent:i1" in book.declined
    made, _ = book.sync_own_watches(relevance.anchors(_context()), NOW)
    assert made == [] and book.find_watch("Grow our own food") is None
    fewer = [a for a in relevance.anchors(_context()) if a.ref != "project:p1"]  # the greenhouse is done
    _, removed = book.sync_own_watches(fewer, NOW)
    assert [w.name for w in removed] == ["Greenhouse"]
    assert book.add_watch("Mine", "greenhouse").made_by == "person"  # the person's own watches are never touched


def test_a_run_fetches_each_feed_once_for_every_watch_that_reads_it():
    from core import world_intel, world_sources

    calls = []

    def fetch(src, watch):
        """Counts fetches; gives one item matching both watches."""
        calls.append(src.source_id)
        return [{"source": src.source_id, "title": "Greenhouse panels and aquaponics pumps", "link": "https://e.org/x",
                 "summary": ""}]
    w1 = world_intel.Watch("w1", "Panels", "greenhouse panels", sources=["hobby_farms", "electrek"])
    w2 = world_intel.Watch("w2", "Pumps", "aquaponics pumps", sources=["hobby_farms", "electrek"])
    results = world_intel.run_watches([w1, w2], NOW, {"feed": fetch})
    assert sorted(calls) == ["electrek", "hobby_farms"]
    assert [len(r["items"]) for r in results] == [2, 2]
    assert world_sources.source("hobby_farms").kind == "feed"
