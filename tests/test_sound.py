"""
Sound (DEC-0028 #11): the engine says which win it was and MIA's line for
it; the person's settings say whether to play and speak.
"""

from core.actions import VOICE_LINES, reward_for, voice_line


def test_voice_lines_are_steady_and_warm():
    assert voice_line("Objective Complete", None, "Sweep") == voice_line("Objective Complete", None, "Sweep")
    assert voice_line("Mission Complete", 5, "Fence").startswith("Level 5")
    assert "Fence" in voice_line("Mission Complete", None, "Fence")
    assert voice_line("Mission Complete", None, "") in VOICE_LINES["XP Earned"]
    words = " ".join(line for lines in VOICE_LINES.values() for line in lines).lower()
    assert not any(w in words for w in ("should have", "finally", "failed", "lazy", "behind"))


def test_a_reward_carries_its_line():
    r = reward_for({"xp": 0, "status": "active"}, {"xp": 150, "status": "completed", "mission": "Fix the fence"},
                   "mission.complete")
    assert r["level_up"] and r["say"].startswith("Level 2")


def test_settings_and_shell(tmp_path, monkeypatch):
    from core.web_surfaces import shell
    from tests.engine_world import build_world

    world = build_world(tmp_path, monkeypatch)
    assert shell(world)["sound"] == {"on": True, "voice": False}
    from core import person_settings

    person_settings.put(world, "sound.voice", True)
    assert shell(world)["sound"]["voice"] is True
