"""Real character stats (DEC-0028): six attributes, 1 to 20, from skills
(training) and the last 30 days (recent), never falling below training."""

from datetime import date

from core.character_stats import STATS, character_stats, score
from tests.engine_world import build_world


def test_score():
    assert score(0, 0) == 1 and score(50, 50) == 20 and score(3.4, 2.6) == 1 + 3 + 3


def test_stats_from_real_things(tmp_path, monkeypatch):
    world = build_world(tmp_path, monkeypatch)
    me = world.profiles.get_active_profile()
    stats = {s["key"]: s for s in character_stats(world, me.profile_id, date.today())}
    assert set(stats) == {key for key, *_ in STATS}
    assert all(1 <= s["value"] <= 20 for s in stats.values())
    assert stats["vitality"]["watch"] == ["Sleep", "Resting heart rate", "HRV"] and stats["wisdom"]["watch"] == []
    if getattr(world, "skills", None) is not None:
        world.skills.add_skill_xp(me.profile_id, "strength", 5000)
        strong = next(s for s in character_stats(world, me.profile_id) if s["key"] == "strength")
        assert strong["training"] > 0 and strong["value"] > stats["strength"]["value"]
        assert any("Strength Lv" in f for f in strong["from"])
