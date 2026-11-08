"""
tests.test_living_worlds
==========================

Living Worlds Phase 1 (core/living_worlds.py, DEC-0134): universes, campaigns, characters and per-universe versions
are created and persisted so a campaign survives sessions; a version's growth is its own and never touches another's;
ids are validated; and a campaign can be paused and resumed. The store is sealed on disk (DEC-0126).
"""

from core import at_rest
import json

import pytest

from core.at_rest import is_sealed
from core.living_worlds import CAMPAIGN_STATUSES, LivingWorldsBook


@pytest.fixture
def book(tmp_path):
    """An empty Living Worlds book in a temporary folder."""
    return LivingWorldsBook(data_dir=tmp_path)


def test_a_world_a_campaign_a_character_and_a_version_persist(tmp_path):
    book = LivingWorldsBook(data_dir=tmp_path)
    u = book.create_universe("Aethelgard", genre="high fantasy", premise="A sundered kingdom of floating isles.")
    c = book.create_campaign(u.universe_id, "The Shattered Crown")
    hero = book.create_character("Kael")
    v = book.create_version(hero.character_id, u.universe_id, c.campaign_id, "Kael the Warden",
                            origin="human ranger", skills=["tracking"])
    # a fresh book on the same folder sees all of it (save/resume by construction)
    again = LivingWorldsBook(data_dir=tmp_path)
    assert [x.name for x in again.universes] == ["Aethelgard"]
    assert again.get_campaign(c.campaign_id).universe_id == u.universe_id
    assert again.get_version(v.version_id).origin == "human ranger"
    assert again.versions_of(hero.character_id)[0].skills == ["tracking"]


def test_each_version_grows_independently(book):
    hero = book.create_character("Kael")
    u1 = book.create_universe("Aethelgard")
    u2 = book.create_universe("New Icarus", genre="hard sci-fi")
    c1 = book.create_campaign(u1.universe_id, "Crown")
    c2 = book.create_campaign(u2.universe_id, "Orbit")
    v1 = book.create_version(hero.character_id, u1.universe_id, c1.campaign_id, "Warden")
    v2 = book.create_version(hero.character_id, u2.universe_id, c2.campaign_id, "Engineer")
    book.update_version(v1.version_id, skills=["swordplay"])
    # v2 is untouched by v1's growth
    assert book.get_version(v2.version_id).skills == []
    assert book.get_version(v1.version_id).skills == ["swordplay"]
    assert len(book.versions_of(hero.character_id)) == 2


def test_a_version_needs_a_real_character_universe_and_campaign(book):
    u = book.create_universe("Aethelgard")
    c = book.create_campaign(u.universe_id, "Crown")
    hero = book.create_character("Kael")
    with pytest.raises(ValueError):
        book.create_version("nope", u.universe_id, c.campaign_id, "Ghost")
    with pytest.raises(ValueError):
        book.create_campaign("nope", "Orphan campaign")


def test_a_campaign_pauses_and_resumes(book):
    u = book.create_universe("Aethelgard")
    c = book.create_campaign(u.universe_id, "Crown")
    hero = book.create_character("Kael")
    book.create_version(hero.character_id, u.universe_id, c.campaign_id, "Warden")
    book.set_campaign_status(c.campaign_id, "paused")
    assert book.get_campaign(c.campaign_id).status == "paused"
    resumed = book.resume(c.campaign_id)
    assert resumed["campaign"]["status"] == "active"
    assert resumed["universe"]["name"] == "Aethelgard"
    assert [v["name"] for v in resumed["versions"]] == ["Warden"]
    with pytest.raises(ValueError):
        book.set_campaign_status(c.campaign_id, "not-a-status")
    assert set(CAMPAIGN_STATUSES) == {"active", "paused", "ended"}


def test_the_store_is_sealed_on_disk(tmp_path):
    book = LivingWorldsBook(data_dir=tmp_path)
    book.create_universe("Secret World", premise="nobody should read this on disk")
    on_disk = (tmp_path / "living_worlds.json").read_text(encoding="utf-8")
    assert is_sealed(on_disk) and "Secret World" not in on_disk


def test_a_quest_mirrors_real_mission_assignment_but_stays_fictional(tmp_path):
    """assign_quest/complete_quest follow the same assign->track shape as a real Mission (assigned_by, status), but
    every event is tagged fictional (DEC-0137), so a real-life view never sees it and no real XP is earned."""
    import json

    book = LivingWorldsBook(data_dir=tmp_path)
    u = book.create_universe("Aethelgard")
    c = book.create_campaign(u.universe_id, "The Shattered Crown")
    q = book.assign_quest(c.campaign_id, "Recover the Sunstone", objective="Reach the drowned temple", assigned_by="dm")
    assert q.assigned_by == "dm" and q.status == "open"
    book.complete_quest(q.quest_id)
    assert book.get_quest(q.quest_id).status == "done"
    assert [x.name for x in book.quests_in(c.campaign_id)] == ["Recover the Sunstone"]
    # persists like everything else
    assert LivingWorldsBook(data_dir=tmp_path).get_quest(q.quest_id).status == "done"
    # every Living Worlds event is fictional — a real timeline (environment == "real") would show none of them
    events = [json.loads(x) for x in at_rest.open_text(tmp_path / "life_events.jsonl").splitlines() if x]
    assert events and all(e.get("environment") == "fictional" for e in events)
    assert not [e for e in events if e.get("environment") == "real"]
