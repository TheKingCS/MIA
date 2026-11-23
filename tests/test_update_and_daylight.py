"""
tests.test_update_and_daylight
================================

Zac's two answers of 2026-11-23, held in code:

- Q-114 ("Never by itself"): MIA OS never restarts by itself to finish an update; MIA says once when one waits
  (`core/update_notice.py`), and a tool and a Settings button put the restart to him for his yes.
- Q-115 ("Yes, darker shades"): the Daylight theme, light glass whose meaning colours are darker shades of the same
  hues, each checked (`core/themes.py`: `MEANING_TOKENS`, `meaning_problems`: never grey, near-black or another
  meaning's colour); no other theme may touch them, and every colour scheme on it keeps its soft accent readable.
"""

from datetime import datetime
from pathlib import Path

from core import appearance, themes, update_notice


def test_no_staged_file_means_no_update_waiting(tmp_path):
    assert update_notice.waiting(tmp_path / "staged-deployment") is None
    assert update_notice.offer(None, datetime(2026, 11, 23), tmp_path / "staged-deployment") == []


def test_a_staged_update_is_said_once_with_its_own_fingerprint(tmp_path):
    staged = tmp_path / "staged-deployment"
    staged.write_text("{}")
    stamp = update_notice.waiting(staged)
    assert stamp
    [said] = update_notice.offer(None, datetime(2026, 11, 23), staged)
    assert said.topic == "update_waiting"
    assert said.fingerprint == f"update-staged-{stamp}"
    assert "never restart the computer by myself" in said.message


def test_off_linux_the_real_staged_path_is_never_read(monkeypatch):
    monkeypatch.setattr(update_notice.sys, "platform", "win32")
    assert update_notice.waiting() is None


def test_restart_to_update_says_so_when_nothing_waits(monkeypatch):
    from core import assistant_desktop_actions

    monkeypatch.setattr(update_notice, "waiting", lambda path=update_notice.STAGED: None)
    assert "no MIA OS update waiting" in assistant_desktop_actions._update_card(None, {})


def test_restart_to_update_only_puts_a_card_up_for_his_yes(monkeypatch):
    from core import assistant_desktop_actions

    proposed = []

    class Card:
        summary = "Restart into the update"

    class Actions:
        def propose(self, context, kind, params):
            proposed.append(kind)
            return Card()

    class Context:
        actions = Actions()

    monkeypatch.setattr(update_notice, "waiting", lambda path=update_notice.STAGED: "2026-11-23T03:00")
    said = assistant_desktop_actions._update_card(Context(), {})
    assert proposed == ["system.apply_update"]
    assert "waiting for your yes" in said


def test_the_restart_tool_needs_approval_in_its_manifest():
    import json

    data = json.loads(Path("apps/settings/manifest.json").read_text(encoding="utf-8"))
    assert data["capabilities"]["tiers"]["restart_to_update"] == "act_with_approval"


def test_daylight_is_light_readable_and_keeps_its_darker_meaning_shades():
    data = themes.clean_theme(themes.as_data(themes.THEMES["daylight"]))
    assert data["light"] is True
    assert data["tokens"]["--attention"] == "#8a5600"
    assert appearance.readability_problems(data) == []
    assert themes.meaning_problems(themes.THEMES["daylight"].tokens) == []


def test_a_dark_theme_can_never_set_a_meaning_colour():
    data = dict(themes.as_data(themes.THEMES["aquatic"]))
    data["tokens"] = dict(data["tokens"], **{"--bad": "#00ff00"})
    assert "--bad" not in themes.clean_theme(data)["tokens"]


def test_a_light_theme_shade_that_changes_hue_or_reads_faintly_is_dropped():
    data = dict(themes.as_data(themes.THEMES["daylight"]))
    data["tokens"] = dict(data["tokens"], **{"--bad": "#1b7a2a"})  # green for danger
    assert "--bad" not in themes.clean_theme(data)["tokens"]
    assert themes.meaning_problems({"--ok": "#9fe0bf"})  # the right hue, but too pale on white
    assert themes.meaning_problems({"--bad": "#1b7a2a"})


def test_a_meaning_colour_cant_be_emptied_or_turned_into_another_meaning():
    assert themes.meaning_problems({"--bad": "#140000"})  # near-black: would read as body text
    assert themes.meaning_problems({"--attention": "#1c1a12"})
    assert themes.meaning_problems({"--win": "#8a5600"})  # amber's shade: the reward would read as "needs you"
    assert themes.meaning_problems(themes.THEMES["daylight"].tokens) == []


def test_every_scheme_on_daylight_keeps_its_soft_accent_readable():
    from core import appearance

    daylight = themes.clean_theme(themes.as_data(themes.THEMES["daylight"]))
    for scheme in appearance.SCHEMES:
        soft = appearance.compose(daylight, scheme)["tokens"]["--accent-soft"]
        assert themes.contrast(soft, "#ffffff") >= 4.5, scheme
