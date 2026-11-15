"""
core.relevance
================

The Personal Relevance Engine (World Intelligence W2, DEC-0170; the proposal's section 4): how much a find matters
to this person, worked out in code from their own records, never guessed by a model. Every point comes with a reason
that names the record it came from, so "why is this here?" always has an answer.

**Anchors** (`anchors(context)`): the records a find can matter to, each with its words, a weight and how it's named:
- an open goal (intent): weight 3, the main one 4;
- a project not finished: weight 3;
- an active mission: weight 2;
- the homestead plan's next step and the goal it leads to (`core/development_engine.plan`): weight 4, the strongest
  reason there is ("this provides what your next step needs");
- a learning path being followed: weight 2;
- a machine or piece of equipment owned (maker, model, name): weight 1 ("fits something you own").
They're read fresh each time, so a finished project stops pulling finds and a new goal starts.

**Matching** (`relevance(text, anchors)`): an anchor counts when the find's title and summary hold its significant
words: all of them for a one- or two-word anchor, at least two for a longer one (so "garden" alone doesn't tie every
garden story to "Garden beds for the south field"). A find that fits several records counts each (the doctrine's
"relevant to multiple areas at once"). Points are the anchors' weights times the words matched.

Nothing is stored here; `core/world_intel.py` keeps the points, reasons and refs on the find.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from core.logger import get_logger

log = get_logger(__name__)

_WORD = re.compile(r"[a-z0-9][a-z0-9+.#-]*")
STOP = frozenset("""
a an and or the of for to in on at by with from into over under about your my our their this that these those it its
is are be was were will can could should would have has had do does did not no new more most less very just also
how what when where why who which get got make made use using used own one two three plan plans project projects
goal goals mission missions build building learn learning path my week day month year start started first next
""".split())


@dataclass(frozen=True)
class Anchor:
    """One record a find can matter to: its `kind:id` ref, how it's named in a reason, its significant words, its
    weight, and the record's own name."""
    ref: str
    label: str
    words: frozenset
    weight: float
    name: str = ""  # the record's own name, as the person wrote it (what a watch MIA makes looks for)


def words_of(text: str) -> frozenset:
    """Pure logic. The significant words of some text: lowercase, three letters or more, no common words, plurals
    folded ("Panels" -> "panel")."""
    out = set()
    for w in _WORD.findall(str(text or "").lower()):
        if len(w) < 3 or w in STOP:
            continue
        out.add(w[:-1] if len(w) > 4 and w.endswith("s") and not w.endswith("ss") else w)
    return frozenset(out)


def _needed(anchor: Anchor) -> int:
    """How many of an anchor's words a find must hold: all of a one- or two-word anchor, two of a longer one."""
    return min(2, len(anchor.words))


def relevance(text: str, anchors: list[Anchor]) -> tuple[float, list[str], list[str]]:
    """Pure logic. (points, reasons, refs) for a find's text against the anchors: each anchor it fits adds its weight
    times the words matched, with a reason naming the record."""
    found = words_of(text)
    points, reasons, refs = 0.0, [], []
    for a in anchors:
        hit = a.words & found
        if a.words and len(hit) >= _needed(a):
            points += a.weight * len(hit)
            reasons.append(f"fits {a.label} ({', '.join(sorted(hit))})")
            refs.append(a.ref)
    return points, reasons, refs


def _safe(read, what: str) -> list:
    """A store's records, or [] when it isn't here or can't be read (relevance never stops a run)."""
    try:
        return list(read() or [])
    except Exception:  # noqa: BLE001 - one unreadable store leaves its anchors out
        log.exception("Relevance: couldn't read %s", what)
        return []


def anchors(context) -> list[Anchor]:
    """The person's anchors now (see the module's opening), read from their own view of the stores."""
    out: list[Anchor] = []

    def add(ref: str, label: str, text: str, weight: float, name: str = "") -> None:
        """One anchor, when its text has significant words."""
        w = words_of(text)
        if w:
            out.append(Anchor(ref, label, w, weight, name))

    intents = getattr(context, "intents", None)
    for i in _safe(lambda: intents.all_intents(), "goals") if intents is not None else []:
        if str(getattr(i, "status", "Active")).lower() == "active":
            add(f"intent:{i.intent_id}", f"your goal “{i.name}”", f"{i.name} {i.description}", 4 if i.primary else 3,
                i.name)
    projects = getattr(context, "projects", None)
    for p in _safe(lambda: projects.all_projects(), "projects") if projects is not None else []:
        if str(getattr(p, "status", "")).lower() not in ("complete", "completed", "cancelled", "abandoned"):
            add(f"project:{p.project_id}", f"your project “{p.name}”", f"{p.name} {p.description}", 3, p.name)
    missions = getattr(context, "missions", None)
    for m in _safe(lambda: missions.all_missions(), "missions") if missions is not None else []:
        if getattr(m, "status", "") == "active":
            add(f"mission:{m.mission_id}", f"your mission “{m.name}”", m.name, 2, m.name)
    maintenance = getattr(context, "maintenance", None)
    for a in _safe(lambda: maintenance.all_assets(), "equipment") if maintenance is not None else []:
        add(f"asset:{a.asset_id}", f"your {a.name}", f"{a.name} {a.manufacturer} {a.model}", 1,
            " ".join(x for x in (a.manufacturer, a.model) if x) or a.name)
    paths = getattr(context, "paths", None)
    for path_id in _safe(lambda: paths.started(), "learning paths") if paths is not None else []:
        add(f"path:{path_id}", f"what you're learning ({str(path_id).replace('_', ' ')})", str(path_id).replace("_", " "), 2)
    out.extend(_plan_anchors(context))
    return out


def _plan_anchors(context) -> list[Anchor]:
    """The homestead plan's next step and its goal (core/development_engine.plan), the strongest anchors there are."""
    try:
        from core import development_engine

        nxt = (development_engine.plan(context) or {}).get("next")
    except Exception:  # noqa: BLE001 - no plan, no plan anchors
        log.exception("Relevance: couldn't read the homestead plan")
        return []
    if not nxt:
        return []
    out = []
    step = words_of(nxt.get("name", ""))
    if step:
        out.append(Anchor(f"plan:{nxt.get('id', '')}", f"the homestead plan's next step, {nxt['name'].lower()}", step, 4,
                          nxt["name"]))
    goal = nxt.get("goal") or {}
    name = goal.get("name") if isinstance(goal, dict) else (goal if isinstance(goal, str) else "")
    if name and words_of(name) and words_of(name) != step:
        out.append(Anchor(f"plan_goal:{nxt.get('id', '')}", f"the homestead goal it leads to, {name.lower()}",
                          words_of(name), 3, name))
    return out


def describe(points: float, reasons: list[str]) -> Optional[str]:
    """Pure logic. The class a find earns from its relevance: None when it only matched a watch's words, else a short
    phrase for the page."""
    if not reasons:
        return None
    return "fits your plans" if points >= 6 else "may fit your plans"
