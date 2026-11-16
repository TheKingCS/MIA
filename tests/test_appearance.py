"""
tests.test_appearance
=======================

The glass design system's foundation (prompt 24 phase A2, DEC-0183, DEC-0184; web/tokens.css, web/themes.css,
core/themes.py, tools/css_colours.py): the five surface tiers exist as tokens with defaults inside their ranges; the
glass material draws every tier from its tokens; a theme can set a tier only within its range, so a dialog can't be made
see-through; status chips keep their meaning colours under glass; the OS's reduced transparency makes glass solid; no
style sheet gains hard-coded colours, and since A6 none but the glasses page has any, and every token a sheet reads
is defined; each app's own colour (DEC-0187) is readable on every theme and never a meaning colour; and (A7) the
background's slow drift is a per-person setting, off unless chosen, held still whenever it should be (page hidden, on
battery, MIA easing off, reduced motion, light glass, high contrast).
"""

import re
from pathlib import Path

from core import themes
from tools import css_colours

WEB = Path(__file__).resolve().parent.parent / "web"
TIERS = ("primary", "secondary", "floating", "deep", "interactive")
PARTS = ("alpha", "tint", "blur", "border", "light", "shadow")


def _defaults() -> dict:
    """The tier tokens' default values in web/tokens.css."""
    text = (WEB / "tokens.css").read_text(encoding="utf-8")
    return dict(re.findall(r"(--surface-[a-z]+-[a-z]+):\s*([0-9.]+(?:px)?);", text))


def test_every_tier_has_all_its_tokens_with_defaults_inside_their_ranges():
    found = _defaults()
    for tier in TIERS:
        for part in PARTS:
            key = f"--surface-{tier}-{part}"
            assert key in found, key
            assert themes.clamp_tier(key, found[key]) == found[key].removesuffix("px") + ("px" if part == "blur" else "") \
                or float(themes.clamp_tier(key, found[key]).removesuffix("px")) == float(found[key].removesuffix("px")), key
            assert key in themes.TOKENS


def test_the_glass_material_draws_every_tier_from_its_tokens():
    css = (WEB / "themes.css").read_text(encoding="utf-8")
    for tier in TIERS:
        for part in PARTS:
            assert f"var(--surface-{tier}-{part})" in css, (tier, part)
    glass = css[css.index('[data-material="glass"]'):css.index('[data-material="chrome"]')]
    assert css_colours.count(glass) == 0  # nothing hard-coded left in the glass material


def test_a_theme_sets_a_tier_only_within_its_range():
    tokens = themes.clean_theme({"id": "t", "name": "T", "tokens": {
        "--surface-floating-alpha": "0.2", "--surface-primary-blur": "90px", "--surface-deep-shadow": "nope",
        "--surface-secondary-tint": "0.05", "--chart-2": "#3f79e5"}})["tokens"]
    assert tokens["--surface-floating-alpha"] == "0.8"  # what he must read now is never see-through
    assert tokens["--surface-primary-blur"] == "24px"
    assert "--surface-deep-shadow" not in tokens and tokens["--surface-secondary-tint"] == "0.05"
    assert tokens["--chart-2"] == "#3f79e5"


def test_status_chips_keep_their_meaning_colours_and_reduced_transparency_makes_glass_solid():
    css = (WEB / "themes.css").read_text(encoding="utf-8")
    assert ":is(.chip, " not in css and ".chip:not(.chip-ok, .chip-soon, .chip-bad)" in css
    reduced = css[css.index("prefers-reduced-transparency"):]
    assert "background: rgb(var(--rgb-panel))" in reduced and "backdrop-filter: none" in reduced


def test_no_style_sheet_gains_hard_coded_colours(tmp_path):
    assert css_colours.problems() == []
    (tmp_path / "new.css").write_text(".x { color: #ff0000; background: rgba(var(--rgb-panel), 0.5); }", encoding="utf-8")
    (tmp_path / "base.json").write_text("{}", encoding="utf-8")
    assert css_colours.problems(tmp_path, tmp_path / "base.json") == [
        "web/new.css: 1 hard-coded colours, more than its 0; use a token from web/tokens.css"]


# ---------------------------------------------------------------- phase A3: theme, colour scheme, layout


import pytest

from core import appearance


@pytest.fixture
def settings(monkeypatch):
    """The person's settings as a plain dict (core/person_settings stand-in)."""
    from core import person_settings

    kept = {}
    monkeypatch.setattr(person_settings, "get", lambda context, key, default=None: kept.get(key, default))
    monkeypatch.setattr(person_settings, "put", lambda context, key, value: kept.__setitem__(key, value))
    return kept


def _built_in():
    """Every built-in theme as the page gets it."""
    return {tid: themes.clean_theme(themes.as_data(t)) for tid, t in themes.THEMES.items()}


def test_every_theme_and_scheme_pairing_is_readable_and_no_scheme_takes_a_meaning_colour():
    for tid, theme in _built_in().items():
        assert appearance.readability_problems(theme) == [], tid
        for scheme in appearance.SCHEMES:
            assert appearance.scheme_problem(scheme, theme) == "", (tid, scheme)
    stark = _built_in()["stark"]
    assert appearance.scheme_problem("gold", stark) == ""  # a soft gold is allowed since DEC-0186 (Zac, Q-41)
    appearance.SCHEMES["amber_test"] = ("Amber", "#f2b33d", "#c99a52", "#f3dcae")
    try:
        assert "amber" in appearance.scheme_problem("amber_test", stark)  # a vivid amber still reads as "needs you"
    finally:
        del appearance.SCHEMES["amber_test"]
    pale = dict(stark, material="glass", tokens={"--bg": "#e0e0e0", "--rgb-bg": "224, 224, 224", "--text": "#f2f6fa",
                                                  "--rgb-panel": "230, 230, 230", "--surface-primary-alpha": "0.5"})
    found = appearance.readability_problems(pale)  # white text on pale glass: every tier is unreadable
    assert found and all("under 4.5:1" in f for f in found) and any("primary" in f for f in found)


def test_a_scheme_changes_only_the_accents_and_a_layout_only_the_layout(settings):
    glass = _built_in()["glass"]
    violet = appearance.compose(glass, "violet")
    changed = {k for k in violet["tokens"] if violet["tokens"][k] != glass["tokens"].get(k)}
    assert changed and all(k.startswith(("--accent", "--rgb-accent", "--chart-")) for k in changed)
    assert violet["material"] == glass["material"] and violet["scheme"] == "violet" and violet["room"]["accent"] == "#a48bff"
    assert appearance.compose(glass, "theme")["tokens"] == glass["tokens"]
    settings[themes.KEY] = "glass"
    before = appearance.for_shell(None)
    appearance.set_layout(None, density="compact", sidebar="icons")
    after = appearance.for_shell(None)
    assert after["layout"] == {"density": "compact", "sidebar": "icons"} and after["tokens"] == before["tokens"]
    appearance.set_scheme(None, "rose")
    assert appearance.for_shell(None)["layout"] == after["layout"]  # colours never move his workspace
    with pytest.raises(ValueError):
        appearance.set_layout(None, sidebar="hidden")  # not until navigation has another home on the PC


def test_the_look_matches_its_published_schema(settings):
    from core import schema_check

    settings[themes.KEY] = "stark"
    settings[appearance.SCHEME_KEY] = "champagne"
    settings[appearance.EFFECTS_KEY] = "light"
    look = appearance.for_shell(None)
    assert schema_check.errors(look, schema_check.load("appearance.schema.json")) == []
    assert look["scheme"] == "champagne" and look["effects"] == "light" and look["reduce_transparency"] is False
    settings[appearance.SCHEME_KEY] = "nonsense"
    assert appearance.for_shell(None)["scheme"] == "theme"


def test_the_voice_tools_set_colours_layout_and_glass_on_their_own(settings):
    from core.assistant_accessibility_actions import _action_set_layout, _action_set_scheme

    assert "Violet" in _action_set_scheme(None, {"scheme": "make the colours violet"})
    assert settings[appearance.SCHEME_KEY] == "violet"
    assert "theme's own" in _action_set_scheme(None, {"scheme": "theme"})
    said = _action_set_layout(None, {"density": "compact", "effects": "none"})
    assert "compact" in said and settings[appearance.EFFECTS_KEY] == "none"
    assert "one of" in _action_set_layout(None, {"effects": "sparkly"})


def test_the_page_sets_layout_and_effects_and_the_sheets_read_them():
    shell = (WEB / "shell.js").read_text(encoding="utf-8")
    assert all(f"root.dataset.{k}" in shell for k in ("density", "sidebar", "effects", "transparency"))
    css = (WEB / "themes.css").read_text(encoding="utf-8") + (WEB / "shell.css").read_text(encoding="utf-8")
    for attr in ('[data-density="compact"]', '[data-sidebar="icons"]', '[data-effects="light"]', '[data-transparency="reduced"]'):
        assert attr in css, attr
    assert ".layout:has(.home-mia)" in css.split('[data-sidebar="icons"]', 1)[1]  # Home keeps its Talk column


# ---------------------------------------------------------------- phase A4: the presets; Q-41's gold


PRESETS = ("aquatic", "nebula", "evergreen", "aurelia", "glacial", "eclipse")


def test_the_six_glass_presets_are_readable_with_every_scheme_and_aquatic_is_the_default():
    assert themes.DEFAULT_THEME == "aquatic"  # DEC-0183, Q-37: from Zac's picture
    for pid in PRESETS:
        data = themes.clean_theme(themes.as_data(themes.THEMES[pid]))
        assert data["material"] == "glass" and appearance.readability_problems(data) == [], pid
        assert themes.accent_problem(data["tokens"]["--accent"]) is None, pid
        assert all(f"--surface-{tier}-alpha" in data["tokens"] for tier in TIERS), pid
        assert all(appearance.scheme_problem(s, data) == "" for s in appearance.SCHEMES), pid
        assert themes.wants_theme(f"switch to {pid}") == pid
    aquatic = themes.clean_theme(themes.as_data(themes.THEMES["aquatic"]))["tokens"]
    assert aquatic["--accent"] == "#35d4ff" and aquatic["--accent-2"] == "#3f79e5" and aquatic["--accent-3"] == "#5955cb"
    assert float(aquatic["--frame-glow"]) > 0  # the picture's bright edge around the whole window


def test_a_soft_gold_accent_is_allowed_and_rewards_are_legendary_orange():
    """DEC-0186 (Zac, Q-41: "Allow gold"; then "a reward can be like borderlands legendary orange"): soft gold,
    champagne and bronze pass; vivid amber and orange still read as "needs you" or a reward."""
    for gold in ("#e8c27a", "#d9b867", "#c08a4a", "#efe2c4"):
        assert themes.accent_problem(gold) is None, gold
    assert "amber" in themes.accent_problem("#f2b33d") and "amber" in themes.accent_problem("#ff9a00")
    assert "reward" in themes.accent_problem("#ff8a1f") and themes.accent_problem("#c3f53c") is None  # lime is free
    tokens = (WEB / "tokens.css").read_text(encoding="utf-8")
    assert "--win: #ff8a1f;" in tokens and "--rgb-win: 255, 138, 31;" in tokens
    studio = (WEB / "studio.js").read_text(encoding="utf-8")
    assert "m.vivid" in studio  # the Studio's live check agrees with core's


# ---------------------------------------------------------------- phase A5: Settings › Appearance, the orb's states


def test_the_look_is_four_plain_settings_each_kept_per_person_and_checked():
    from core import person_settings
    from core.web_account import SETTINGS_BY_KEY

    keys = ("display.scheme", "display.density", "display.sidebar", "display.effects", "display.reduce_transparency")
    for key in keys:
        assert key in SETTINGS_BY_KEY and SETTINGS_BY_KEY[key].group == "Look", key
        assert key in person_settings.PERSONAL_SETTINGS, key  # his, not the device's
    assert [v for v, _ in SETTINGS_BY_KEY["display.scheme"].options] == ["theme", *appearance.SCHEMES]


def test_a_colour_scheme_that_cant_be_read_on_the_theme_is_refused_in_settings(settings, monkeypatch):
    from core.account_actions import _setting
    from core.actions import ActionError

    monkeypatch.setattr(appearance, "scheme_problem", lambda s, t: "Too faint on these panels." if s == "ice" else "")
    monkeypatch.setattr("core.account_actions._me", lambda context: None)
    assert _setting(None, {"key": "display.scheme", "value": "violet"})[1] == "violet"
    with pytest.raises(ActionError, match="Too faint"):
        _setting(None, {"key": "display.scheme", "value": "ice"})


def test_the_appearance_picker_offers_every_choice_and_its_demo_data_matches(settings):
    import json

    look = appearance.picker(None)
    assert look["theme"] == "aquatic" and look["scheme"] == "theme" and look["effects"] == "auto"
    assert [s["id"] for s in look["schemes"]] == ["theme", *appearance.SCHEMES]
    assert all(len(s["colours"]) == 3 for s in look["schemes"][1:])
    assert {d["id"] for d in look["density"]} == set(appearance.DENSITY)
    assert {e["id"] for e in look["effects_choices"]} == set(appearance.EFFECTS)
    example = json.loads((WEB.parent / "docs" / "schema" / "themes.example.json").read_text(encoding="utf-8"))
    assert set(example["look"]) == set(look) and len(example["themes"]) == len(themes.THEMES)
    js = (WEB / "studio.js").read_text(encoding="utf-8")
    assert "lookSection()" in js and '"display.scheme"' in js and "restoreLook" in js


@pytest.fixture
def clock(monkeypatch):
    """core.orb_state with a clock the test moves, starting idle."""
    from core import orb_state

    now = [100.0]
    monkeypatch.setattr(orb_state, "_clock", lambda: now[0])
    orb_state.reset()
    yield now
    orb_state.reset()


def test_the_orb_shows_only_what_is_really_happening(clock):
    from core import orb_state

    assert orb_state.current() == "idle"
    before = orb_state.version()
    with orb_state.active("thinking"):
        assert orb_state.current() == "thinking" and orb_state.version() > before
        with orb_state.active("working"):
            assert orb_state.current() == "working"  # the stronger of the two
        assert orb_state.current() == "thinking"
    assert orb_state.current() == "idle"
    orb_state.flash("success")
    assert orb_state.current() == "success"
    clock[0] += orb_state.FLASH_SECONDS + 0.1
    assert orb_state.current() == "idle"  # a moment passes by itself
    orb_state.flash("sparkles")
    assert orb_state.current() == "idle"  # only real states
    with pytest.raises(ValueError):
        with orb_state.active("dancing"):
            pass


def test_an_approved_action_shows_working_then_success_or_a_warning(clock, monkeypatch):
    from types import SimpleNamespace

    from core import actions, orb_state

    seen = []
    monkeypatch.setitem(actions.ACTION_TYPES, "zz.ok", actions.ActionType(
        "zz.ok", "Ok", {}, lambda c, p: "Do it", lambda c, p: seen.append(orb_state.current()) or "Done."))
    monkeypatch.setitem(actions.ACTION_TYPES, "zz.fail", actions.ActionType(
        "zz.fail", "Fail", {}, lambda c, p: "Do it", lambda c, p: (_ for _ in ()).throw(actions.ActionError("No."))))
    center = actions.ActionCenter()
    context = SimpleNamespace(config=None, undo=None, events=None, failures=None)
    done = center.approve(context, center.propose(context, "zz.ok").proposal_id)
    assert done.status == actions.EXECUTED and seen == ["working"] and orb_state.current() == "success"
    failed = center.approve(context, center.propose(context, "zz.fail").proposal_id)
    assert failed.status == actions.FAILED and orb_state.current() == "warning"


def test_every_real_source_of_activity_marks_the_orb_and_the_page_follows_it():
    root = WEB.parent
    sources = {"core/llm_manager.py": 'orb_state.active("thinking")', "core/actions.py": 'orb_state.active("working")',
               "core/council.py": 'orb_state.active("council")', "core/communication_gate.py": 'orb_state.flash("notification")',
               "core/homeostasis.py": 'orb_state.flash("warning")', "server/app.py": "event: presence"}
    for path, mark in sources.items():
        assert mark in (root / path).read_text(encoding="utf-8"), path
    assert '"mia-presence"' in (WEB / "mia.js").read_text(encoding="utf-8")
    shell = (WEB / "shell.js").read_text(encoding="utf-8")
    assert 'presenceHere("listening")' in shell and "data-presence-orb" in shell
    assert "data-presence-orb" in (WEB / "index.html").read_text(encoding="utf-8")
    css = (WEB / "ui.css").read_text(encoding="utf-8")
    for state in ("working", "council", "notification", "warning", "success"):
        assert f'.mia-orb[data-state="{state}"]' in css, state


SET_BY_SCRIPT = {"--hue", "--tile-rgb"}  # set inline per element by hub.js, glasses.js and apps.js


def test_every_sheet_but_the_glasses_page_draws_all_its_colours_from_tokens():
    counts = css_colours.counts()
    assert {name: n for name, n in counts.items() if n and name != "glasses.css"} == {}
    glasses = (WEB / "glasses.css").read_text(encoding="utf-8")
    assert "--rgb-light:" in glasses and "--rgb-shadow:" in glasses  # its page doesn't load tokens.css
    assert "--on-accent:" in (WEB / "tokens.css").read_text(encoding="utf-8")


def test_every_token_a_sheet_reads_is_defined_in_the_tokens_or_that_sheet():
    defined = set(re.findall(r"(--[\w-]+)\s*:", (WEB / "tokens.css").read_text(encoding="utf-8")))
    for sheet in sorted(WEB.glob("*.css")):
        text = sheet.read_text(encoding="utf-8")
        own = set(re.findall(r"(--[\w-]+)\s*:", text))
        missing = set(re.findall(r"var\((--[\w-]+)\)", text)) - defined - own - SET_BY_SCRIPT
        assert not missing, (sheet.name, sorted(missing))


def test_each_apps_own_colour_is_readable_on_every_theme_and_never_a_meaning_colour():
    tokens = (WEB / "tokens.css").read_text(encoding="utf-8")
    colours = {name: "#" + "".join(f"{int(v):02x}" for v in rgb.split(","))
               for name, rgb in re.findall(r"--rgb-atmo-([a-z]+):\s*([0-9, ]+);", tokens)}
    assert set(colours) >= {"workout", "kitchen", "workshop", "finance", "land", "skills"}  # DEC-0187
    backgrounds = [t["tokens"]["--bg"] for t in _built_in().values() if t["tokens"].get("--bg")] + ["#05070a"]
    for name, colour in colours.items():
        assert themes.accent_problem(colour) is None, name
        assert min(themes.contrast(colour, bg) for bg in backgrounds) >= 4.5, name
        assert f"var(--rgb-atmo-{name})" in tokens, name  # some app uses it


# ---------------------------------------------------------------- phase A7: ambient motion


def test_background_motion_is_a_plain_setting_off_unless_chosen_and_set_by_voice(settings):
    from core import person_settings
    from core.assistant_accessibility_actions import _action_set_layout
    from core.web_account import SETTINGS_BY_KEY

    assert appearance.AMBIENT_KEY in person_settings.PERSONAL_SETTINGS
    assert SETTINGS_BY_KEY[appearance.AMBIENT_KEY].group == "Look"
    assert appearance.for_shell(None)["ambient"] == "off"
    assert "drifts slowly" in _action_set_layout(None, {"motion": "drift"})
    assert settings[appearance.AMBIENT_KEY] == "drift" and appearance.picker(None)["ambient"] == "drift"
    assert "still now" in _action_set_layout(None, {"motion": "still"})
    assert "slow drift, or still" in _action_set_layout(None, {"motion": "sparkly"})
    settings[appearance.AMBIENT_KEY] = "wild"  # anything else reads as off
    assert appearance.for_shell(None)["ambient"] == "off"


def test_the_look_says_when_mia_is_easing_off_and_only_while_the_reading_is_fresh(settings, monkeypatch):
    from core import homeostasis

    monkeypatch.setattr(homeostasis, "_EASED_AT", None)
    assert appearance.for_shell(None)["easing"] is False
    monkeypatch.setattr(homeostasis.time, "monotonic", lambda: 1000.0)
    monkeypatch.setattr(homeostasis, "_EASED_AT", 1000.0 - 60)
    assert appearance.for_shell(None)["easing"] is True
    monkeypatch.setattr(homeostasis, "_EASED_AT", 1000.0 - homeostasis.EASING_FRESH - 1)
    assert homeostasis.easing_now() is False
    reads = iter([{"cpu": 95.0}] * 3 + [{"cpu": 10.0}] * 3)
    ease = homeostasis.Homeostasis(None, read=lambda: next(reads), clock=iter(range(0, 1000, 31)).__next__)
    for _ in range(3):
        ease.refresh()
    assert homeostasis.easing_now() is True  # three busy readings: she eases off, and the pages hear it
    for _ in range(3):
        ease.refresh()
    assert homeostasis.easing_now() is False


def test_the_drifting_backdrop_holds_still_whenever_it_should():
    shell = (WEB / "shell.js").read_text(encoding="utf-8")
    assert "root.dataset.ambient" in shell and "ambientHeld.easing = !!theme.easing" in shell
    assert "visibilitychange" in shell and "getBattery" in shell and "chargingchange" in shell
    css = (WEB / "themes.css").read_text(encoding="utf-8")
    assert ":root[data-ambient-held] .theme-ambient { animation-play-state: paused; }" in css
    assert ':root:is([data-effects="light"], [data-effects="none"]) .theme-ambient { animation: none; }' in css
    assert "@media (prefers-reduced-motion: reduce) { .theme-ambient { animation: none; } }" in css
    assert ':root[data-contrast="high"] .theme-ambient { display: none; }' in css
    block = css[css.index("@keyframes mia-ambient-drift"):]
    block = block[:block.index("\n}\n")]
    assert set(re.findall(r"([a-z-]+):", block)) == {"transform"}  # only the compositor's work moves
    assert '"display.ambient"' in (WEB / "studio.js").read_text(encoding="utf-8")
