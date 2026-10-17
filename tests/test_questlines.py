"""
Questlines and seasons (DEC-0028): linked chapters, each one a mission;
finishing a chapter opens the next with MIA's line for it; seasons follow
the date and the hemisphere.
"""

from datetime import date

import pytest

from core.actions import ActionCenter, ActionError
from core.questlines import (QuestBook, STARTERS, available, parse_chapters, parse_objective, quests_section,
                             season_id, season_note, season_of, season_span)
from core.web_progress import missions_page
from tests.engine_world import build_world


@pytest.fixture
def world(tmp_path, monkeypatch):
    context = build_world(tmp_path, monkeypatch)
    context.actions = ActionCenter()
    context.quest_book = QuestBook(context, data_dir=context.my_dir)
    return context


def do(world, kind, **params):
    proposal = world.actions.propose(world, kind, params)
    done = world.actions.approve(world, proposal.proposal_id)
    assert done.status == "executed", done.result
    return proposal, done


def test_seasons_follow_the_hemisphere():
    assert season_of(date(2026, 10, 17)) == "Fall" and season_of(date(2026, 10, 17), "AU") == "Spring"
    assert season_of(date(2027, 1, 5)) == "Winter" and season_of(date(2027, 1, 5), "NZ") == "Summer"
    assert season_span(date(2026, 10, 17)) == (date(2026, 9, 1), date(2026, 11, 30))
    assert season_span(date(2027, 2, 10)) == (date(2026, 12, 1), date(2027, 2, 28))
    assert season_id(date(2027, 2, 10)) == "Winter 2026"


def test_parsing_your_own():
    assert parse_objective("Work out|3") == ("Work out", 3.0) and parse_objective("Plant") == ("Plant", 1.0)
    chapters = parse_chapters("1. prep the beds: clear them; add compost\n\nPlant\n- Harvest: pick, share")
    assert [c["title"] for c in chapters] == ["Prep The Beds", "Plant", "Harvest"]
    assert chapters[0]["objectives"] == ["clear them", "add compost"] and chapters[1]["objectives"] == ["Plant"]


def test_starters_are_generic_and_well_formed():
    for s in STARTERS:
        assert 2 <= len(s.chapters) <= 5 and s.season in ("", "Winter", "Spring", "Summer", "Fall")
        assert all(title and story and objectives for title, story, objectives in s.chapters)


def test_offers_this_season_and_only_what_fits(world):
    names = {s.starter_id for s in available(world, date(2026, 10, 17))}
    assert "ready_for_winter" in names and "new_skill" in names
    assert "harvest_home" not in names  # nothing growing to hang it on
    assert "spring_cleaning" not in names
    world.maintenance.add_asset("Raised bed", "Garden/Plant")
    assert "harvest_home" in {s.starter_id for s in available(world, date(2026, 10, 17))}


def test_play_a_questline_chapter_by_chapter(world):
    _p, done = do(world, "quest.start", starter_id="ready_for_winter")
    assert "Chapter 1: Check The House" in done.result
    quest = world.quest_book.quests[0]
    assert quest.season.startswith(season_of(date.today()))
    first = world.missions.get_mission(quest.chapters[0].mission_id)
    assert first.assigned_by == "mia" and len(first.objectives) == 3 and first.reward_credits == 0
    assert "ready_for_winter" not in {s.starter_id for s in available(world)}

    _p, done = do(world, "mission.complete", mission_id=first.mission_id)
    assert "Chapter 2: Seal It Up" in done.result and "Keep the warm in." in done.result
    second = world.missions.get_mission(quest.chapters[1].mission_id)
    assert second.status == "active" and second.reward_xp == 75

    do(world, "mission.complete", mission_id=second.mission_id)
    last = world.missions.get_mission(world.quest_book.quests[0].chapters[2].mission_id)
    assert last.reward_credits == 100
    _p, done = do(world, "mission.complete", mission_id=last.mission_id)
    assert "complete: every chapter done" in done.result
    section = quests_section(world)
    assert not section["active"] and section["finished"][0]["percent"] == 100
    from core.life_events import events_for

    assert any(e.type == "questline_finished" for e in events_for(world, "2000-01-01", "2999-12-31"))


def test_your_own_and_removing_one(world):
    with pytest.raises(ActionError):
        world.actions.propose(world, "quest.add", {"name": "Solo", "chapters": "Only one"})
    do(world, "quest.add", name="Garage Glow-Up", chapters="Clear it out: sort; toss\nOrganize: shelves|2")
    quest = world.quest_book.quests[0]
    mission = world.missions.get_mission(quest.chapters[0].mission_id)
    assert [o.description for o in mission.objectives] == ["sort", "toss"]
    page = missions_page(world)
    card = page["quests"]["active"][0]
    assert [c["state"] for c in card["chapters"]] == ["current", "locked"] and card["chapters"][1]["objectives"] == []
    do(world, "quest.remove", quest_id=quest.quest_id)
    assert not world.quest_book.quests and world.missions.get_mission(mission.mission_id) is not None


def test_a_chapter_finished_elsewhere_still_moves_on(world):
    do(world, "quest.start", starter_id="new_skill")
    quest = world.quest_book.quests[0]
    world.missions.update_mission(quest.chapters[0].mission_id, status="completed")
    section = quests_section(world)
    assert section["active"][0]["current"] == 1 and quest.chapters[1].mission_id


def test_season_note_once_there_is_something(world):
    title, message, fingerprint = season_note(world, date(2026, 10, 17))
    assert "Fall" in title and "Ready For Winter" in message and fingerprint == "season:Fall 2026"
    do(world, "quest.start", starter_id="ready_for_winter")
    assert season_note(world, date(2026, 10, 17)) is None  # nothing seasonal left to offer


def test_child_can_play(world):
    from core.actions import ACTION_TYPES

    assert all(ACTION_TYPES[k].child_ok for k in ("quest.start", "quest.add", "quest.remove"))
