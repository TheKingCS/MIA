"""
core.appearance
=================

The appearance engine (prompt 24 phase A3, DEC-0183, DEC-0184; `docs/mia_os/MIA_OS_APPEARANCE_ENGINE.md` C): a person's
look is three independent choices, composed into the one cleaned theme every page applies (`web/shell.js`):

- **Theme** (`display.theme`, `core/themes.py`): the environment: field and panel colours, the glass tiers, the
  backdrop, the room's light, sounds.
- **Colour scheme** (`display.scheme`, `SCHEMES`): the accents (primary, second, third), the gradient, the chart
  palette and the orb's colour. "theme" means the theme's own accents (what every look did before). A scheme never
  sets a meaning colour (amber, red, green, gold: DEC-0014, DEC-0136); its accent is refused when it reads as one
  (`themes.accent_problem`) or can't be seen on the theme's panels (under 3:1, `scheme_problem`). On a light theme
  (Daylight, Q-115) its accents show in darker shades of their own hues (`scheme_colours`).
- **Layout** (`display.density`, `display.sidebar`; `LAYOUT`): density (comfortable, compact) and the sidebar (full,
  icons only), each a plain setting of its own so Settings and `setting.set` handle them like any other, set
  on the page as attributes (`data-density`, `data-sidebar`); the experience stays `display.style` (DEC-0135).
  Changing a theme or a scheme never changes the layout, and the reverse.

Two more per-person settings say how much glass the device should draw: **effects** (`display.effects`: full, light
with no blur and no moving backdrop, none with solid surfaces; "auto" lets the page choose light on a phone) and
**reduced transparency** (`display.reduce_transparency`, as the OS's own setting does). Both are attributes the
style sheets read (`web/themes.css`).

**Ambient motion** (`display.ambient`, A7; off unless chosen): a slow drift of the colours' glow behind every page.
The page keeps it still whenever it should cost nothing or might bother: effects light or none, reduced motion (the
OS's), high contrast, the page hidden, the device on battery, or MIA easing off her own work (`easing`, from
`core/homeostasis.easing_now`, so a busy computer isn't asked to animate too).

**Readable glass, checked** (`readability_problems`): for each of the five tiers, the panel as it really shows (the
field, the panel colour at the tier's opacity, the light sheen over it) must keep body text at 4.5:1 (WCAG 2.2 AA).
Every built-in theme and scheme passes (`tests/test_appearance.py`); a preset that doesn't is a bug.

`for_shell(context)` is what `/api/shell` sends; nothing here touches a page or Qt.
"""

from __future__ import annotations

from typing import Optional

from core import themes

SCHEME_KEY = "display.scheme"
DENSITY_KEY = "display.density"
SIDEBAR_KEY = "display.sidebar"
EFFECTS_KEY = "display.effects"
TRANSPARENCY_KEY = "display.reduce_transparency"
AMBIENT_KEY = "display.ambient"
AMBIENT = ("off", "drift")
DEFAULT_SCHEME = "theme"
DENSITY = ("comfortable", "compact")
SIDEBAR = ("full", "icons")  # "hidden" waits for another way to navigate on the PC (A5)
EFFECTS = ("auto", "full", "light", "none")
LAYOUT = {"density": DENSITY, "sidebar": SIDEBAR}
DEFAULT_LAYOUT = {"density": "comfortable", "sidebar": "full"}

# Colour schemes: (name, primary accent, second, third, chart palette). The chart palette is the three accents then
# three quiet greys, so a chart never needs a meaning colour for a series. Cyan's second and third come from Zac's
# reference picture (docs/design/reference/prompt24_glass_dashboard.jpg: cyan, blue, violet).
_GREYS = ("#8ea3b8", "#5f7184", "#c9d6e2")
_LIGHT_GREYS = ("#5f7184", "#3f4f60", "#8597a8")  # the same quiet greys, darker for white panels (Q-115)
SCHEMES: dict[str, tuple] = {
    "cyan": ("Cyan", "#35d4ff", "#3f79e5", "#5955cb"),
    "turquoise": ("Turquoise", "#2fd6c3", "#1f9fb8", "#7fe0f0"),
    "violet": ("Violet", "#a48bff", "#6c5ce7", "#d2b8ff"),
    # A soft gold is allowed since DEC-0186 (Zac, Q-41: "Allow gold"); vivid amber still reads as "needs you".
    "gold": ("Gold", "#e8c27a", "#c08a4a", "#f3dcae"),
    "champagne": ("Champagne", "#efe2c4", "#b8ad98", "#f5ead6"),
    "ice": ("Ice", "#bfe6ff", "#8fb8dd", "#e6f4ff"),
    "rose": ("Rose", "#ff8fc4", "#d16aa8", "#ffc4e0"),
}


def scheme_colours(scheme_id: str, light: bool = False) -> tuple:
    """Pure logic. A scheme's three accents as a theme shows them: as they are, or on a light theme (Q-115) each taken
    darker in its own hue until it reads at 4.5:1 on white."""
    colours = SCHEMES[scheme_id][1:4]
    return tuple(themes.deepen(c) for c in colours) if light else colours


def scheme_tokens(scheme_id: str, light: bool = False) -> dict:
    """Pure logic. The tokens a scheme sets ({} for "theme" or an unknown one): the accent with its soft and deep
    versions as `core/themes.build_theme` makes them, the second and third accents, and the chart palette; on a light
    theme, the accents in their darker shades and quieter greys (`scheme_colours`)."""
    if scheme_id not in SCHEMES:
        return {}
    accent, second, third = scheme_colours(scheme_id, light)
    greys = _LIGHT_GREYS if light else _GREYS
    out = {"--accent": accent, "--rgb-accent": themes.triplet(accent),
           "--accent-soft": themes.mix(accent, "#ffffff", 0.6), "--accent-deep": themes.mix(accent, "#000000", 0.45),
           "--accent-2": second, "--rgb-accent-2": themes.triplet(second),
           "--accent-3": third, "--rgb-accent-3": themes.triplet(third)}
    for i, colour in enumerate((accent, second, third) + greys, start=1):
        out[f"--chart-{i}"] = colour
    return out


def _panel(theme: dict) -> str:
    """The theme's panel colour as #rrggbb (Stark's when it doesn't set one)."""
    rgb = theme.get("tokens", {}).get("--rgb-panel")
    if rgb:
        try:
            return themes._hex(tuple(int(v) for v in str(rgb).split(",")))
        except ValueError:
            pass
    return themes.choices_of(theme).get("panel") or themes.STARK_CHOICES["panel"]


def scheme_problem(scheme_id: str, theme: dict) -> str:
    """Pure logic. Why this scheme can't be used with this theme ("" when it can): one of its three accents reads as a
    meaning colour, or its primary accent, as the theme shows it (darker on a light theme, `scheme_colours`), is under
    3:1 against the theme's panels (WCAG 2.2's minimum for controls and focus)."""
    if scheme_id == DEFAULT_SCHEME:
        return ""
    if scheme_id not in SCHEMES:
        return "I don't have that colour scheme."
    accent = scheme_colours(scheme_id, bool(theme.get("light")))[0]
    for colour in SCHEMES[scheme_id][1:4]:  # charts use all three, so none may read as a meaning colour
        problem = themes.accent_problem(colour)
        if problem:
            return problem
    if themes.contrast(accent, _panel(theme)) < 3:
        return f"{SCHEMES[scheme_id][0]} would be hard to see on {theme.get('name', 'this theme')}'s panels."
    return ""


def _tokens_value(theme: dict, key: str, default: str) -> str:
    """A token's value in the theme, or what web/tokens.css gives it."""
    return str(theme.get("tokens", {}).get(key) or default)


def _number(text: str, default: float) -> float:
    """A token's number ("0.075", "16px"), or the default."""
    try:
        return float(str(text).strip().removesuffix("px"))
    except ValueError:
        return default


TIER_DEFAULTS = {"primary": (0.0, 0.075), "secondary": (0.0, 0.075), "floating": (0.94, 0.06), "deep": (0.0, 0.075),
                 "interactive": (0.0, 0.06)}  # (alpha, tint), as in web/tokens.css


def readability_problems(theme: dict) -> list[str]:
    """Pure logic. The glass tiers on which body text would fall under 4.5:1 for this theme: each tier's surface as it
    really shows (the field, the panel colour over it at the tier's opacity, the light sheen over that). Only for a
    glass theme; [] when every tier reads."""
    if theme.get("material") != "glass":
        return []
    choices = themes.choices_of(theme)
    field = choices.get("background") or themes.STARK_CHOICES["background"]
    text = choices.get("text") or themes.STARK_CHOICES["text"]
    panel = _panel(theme)
    out = []
    for tier, (alpha0, tint0) in TIER_DEFAULTS.items():
        alpha = _number(_tokens_value(theme, f"--surface-{tier}-alpha", str(alpha0)), alpha0)
        tint = _number(_tokens_value(theme, f"--surface-{tier}-tint", str(tint0)), tint0)
        shown = themes.mix(themes.mix(field, panel, alpha), "#ffffff", tint)
        ratio = themes.contrast(text, shown)
        if ratio < 4.5:
            out.append(f"text on the {tier} glass would be {ratio:.1f}:1, under 4.5:1")
    return out


def compose(theme: dict, scheme_id: str) -> dict:
    """Pure logic. The theme with the scheme's tokens over its own (a copy; "theme" leaves it as it is; on a light theme
    the accents' darker shades), and the scheme named on it (`scheme`) for the page and the Studio."""
    out = dict(theme, tokens=dict(theme.get("tokens", {})))
    light = bool(theme.get("light"))
    out["tokens"].update(scheme_tokens(scheme_id, light))
    out["scheme"] = scheme_id if scheme_id in SCHEMES else DEFAULT_SCHEME
    if scheme_id in SCHEMES and out.get("room"):
        out["room"] = dict(out["room"], accent=scheme_colours(scheme_id, light)[0])  # the room's light follows it
    return out


def scheme_of(context, theme: Optional[dict] = None) -> str:
    """The person's colour scheme ("theme" when unset, unknown, or not usable with their theme: the reason is in
    `scheme_problem`)."""
    from core import person_settings

    value = str(person_settings.get(context, SCHEME_KEY, DEFAULT_SCHEME) or DEFAULT_SCHEME)
    theme = theme or themes.for_shell(context)
    return value if value in SCHEMES and not scheme_problem(value, theme) else DEFAULT_SCHEME


def layout_of(context) -> dict:
    """The person's layout ({density, sidebar}) from its two settings, each value one of its choices (the default where
    unset or unknown)."""
    from core import person_settings

    raw = {"density": person_settings.get(context, DENSITY_KEY, None),
           "sidebar": person_settings.get(context, SIDEBAR_KEY, None)}
    return {k: raw[k] if raw[k] in LAYOUT[k] else DEFAULT_LAYOUT[k] for k in LAYOUT}


def effects_of(context) -> dict:
    """How much glass and motion to draw: {effects: auto|full|light|none, reduce_transparency: bool, ambient:
    off|drift}."""
    from core import person_settings

    effects = person_settings.get(context, EFFECTS_KEY, "auto")
    ambient = person_settings.get(context, AMBIENT_KEY, "off")
    return {"effects": effects if effects in EFFECTS else "auto",
            "reduce_transparency": bool(person_settings.get(context, TRANSPARENCY_KEY, False)),
            "ambient": ambient if ambient in AMBIENT else "off"}


def for_shell(context) -> dict:
    """What /api/shell sends as the look: the theme with the person's scheme over it, plus their layout, effects and
    ambient motion (`layout`, `effects`, `ambient`), each independent of the others, and whether MIA is easing off
    right now (`easing`: the page keeps its backdrop still)."""
    from core.homeostasis import easing_now

    theme = themes.for_shell(context)
    out = compose(theme, scheme_of(context, theme))
    out["layout"] = layout_of(context)
    out.update(effects_of(context))
    out["easing"] = easing_now()
    return out


def set_scheme(context, scheme_id: str) -> str:
    """Sets the person's colour scheme and says so; ValueError with the reason when it can't be used with their theme."""
    from core import person_settings

    problem = scheme_problem(scheme_id, themes.for_shell(context))
    if problem:
        raise ValueError(problem)
    person_settings.put(context, SCHEME_KEY, scheme_id)
    return ("Back to your theme's own colours." if scheme_id == DEFAULT_SCHEME
            else f"Colours are now {SCHEMES[scheme_id][0]}; your theme and layout stay as they are.")


def set_layout(context, **changes) -> str:
    """Changes the person's layout (density, sidebar; each its own setting) and says what it is now; ValueError for a
    value it doesn't have. Colours and the theme stay as they are."""
    from core import person_settings

    layout = layout_of(context)
    for key, value in changes.items():
        if value in (None, ""):
            continue
        if key not in LAYOUT or value not in LAYOUT[key]:
            raise ValueError(f"The {key} is one of: {', '.join(LAYOUT.get(key, ()))}.")
        layout[key] = value
        person_settings.put(context, DENSITY_KEY if key == "density" else SIDEBAR_KEY, value)
    return f"Layout: {layout['density']}, sidebar {layout['sidebar']}. Your colours stay as they are."


SCHEME_OPTIONS = ((DEFAULT_SCHEME, "The theme's own"),) + tuple((k, v[0]) for k, v in SCHEMES.items())
EFFECT_NAMES = {"auto": "Auto (lighter on a phone)", "full": "Full glass", "light": "Light (no blur)",
                "none": "None (solid panels)"}
AMBIENT_NAMES = {"off": "Still", "drift": "Slow drift"}


def picker(context) -> dict:
    """The "Your look" picker's data (the Theme Studio, web/studio.js): what's chosen now, each colour scheme with its
    three colours and whether it can be used with the theme in use (and why not), the layout, effect and motion
    choices."""
    theme = themes.for_shell(context)
    look = for_shell(context)
    return {"theme": theme["id"], "scheme": look["scheme"], "layout": look["layout"], "effects": look["effects"],
            "reduce_transparency": look["reduce_transparency"], "ambient": look["ambient"],
            "ambient_choices": [{"id": a, "name": AMBIENT_NAMES[a]} for a in AMBIENT],
            "schemes": [{"id": DEFAULT_SCHEME, "name": "The theme's own", "colours": [], "problem": ""}]
            + [{"id": k, "name": v[0], "colours": list(v[1:4]), "problem": scheme_problem(k, theme)}
               for k, v in SCHEMES.items()],
            "density": [{"id": d, "name": d.capitalize()} for d in DENSITY],
            "sidebar": [{"id": "full", "name": "Full"}, {"id": "icons", "name": "Icons only"}],
            "effects_choices": [{"id": e, "name": EFFECT_NAMES[e]} for e in EFFECTS]}


def wants_scheme(words: str) -> Optional[str]:
    """Pure logic. The colour scheme someone named ("make the colours violet", "theme's own colours"), else None."""
    said = (words or "").lower()
    if "own colour" in said or "own color" in said or "theme's colour" in said or "theme's color" in said:
        return DEFAULT_SCHEME
    found = [s for s, (name, *_rest) in SCHEMES.items() if s in said or name.lower() in said]
    return found[0] if len(found) == 1 else None
