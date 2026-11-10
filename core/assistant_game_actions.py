"""
core.assistant_game_actions
=============================

Boss battles and questlines by voice (DEC-0028's game layer, DEC-0125: every feature both ways). The Missions page
draws the bosses (every debt, and the missions made into boss fights) and the questlines (being played, and on offer
this season); until now none of it could be asked about. Four tools, each from the same data the page draws
(core/boss_battles.bosses, core/questlines.quests_section), so voice and screen never disagree:

- get_bosses: each active boss, closest to defeat first, its HP and what a hit does; the defeated ones counted;
- make_boss: makes a mission (by name) a boss fight through the page's own action (`boss.add`);
- get_questlines: the season, each questline being played and its current chapter, and what's on offer;
- start_questline: starts one on offer (by name) through `quest.start`;
- list_places / arrive_place: the person's location-quest places, and "I'm at the gym" as the place's own arrival
  (`place.arrive`: its line, and the map's fog cleared there), never reading where they are;
- set_mission_project / get_project_missions (DEC-0152): "make the coop mission part of the homestead project"
  through `mission.project` ("on its own" takes it out), and a project's missions with its progress, from
  core/mission_projects.py, the same records the Projects and Missions pages show.

Changes run through the action kinds (checked, then run, as the screens do), so "undo that" takes them back. Money is
never said to a child: bosses() already leaves debts out for one.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry
from core.assistant_goods_actions import _run


def _get_bosses(context, arguments: dict) -> str:
    """Tool get_bosses: the active bosses (closest to defeat first), each one's HP, its phase and what one hit
    does, and how many have fallen."""
    from core.boss_battles import bosses

    page = bosses(context)
    active, fallen = page.get("active") or [], page.get("defeated") or []
    if not active:
        return ("No bosses to fight right now" + (f"; {len(fallen)} defeated so far" if fallen else "") +
                ". Any mission can become one: say \"make <the mission> a boss fight\".")
    lines = []
    for b in active[:6]:
        line = f"{b.get('icon', '')} {b['name']}: {b['hp']} of {b['max_hp']} HP left ({b.get('phase', '')})"
        if b.get("hit"):
            line += f", a hit of {b['hit']}"
        if b.get("hits_left"):
            line += f", about {b['hits_left']} hits to go"
        lines.append(line.strip())
    return "Your bosses: " + "; ".join(lines) + (f". Defeated so far: {len(fallen)}." if fallen else ".")


def _find_mission(context, words: str):
    """The active mission the words name, or None."""
    missions = getattr(context, "missions", None)
    said = " ".join(str(words or "").lower().split())
    if missions is None or not said:
        return None
    found = [m for m in missions.all_missions() if m.status != "abandoned"
             and (said in m.name.lower() or m.name.lower() in said)]
    return found[0] if found else None


def _make_boss(context, arguments: dict) -> str:
    """Tool make_boss: turns the mission the person names into a boss fight (boss.add), in its own words when it
    can't."""
    mission = _find_mission(context, arguments.get("mission"))
    if mission is None:
        return "I don't see a mission by that name. Ask me what missions you have."
    return _run(context, "boss.add", {"mission_id": mission.mission_id})


def _get_questlines(context, arguments: dict) -> str:
    """Tool get_questlines: the season, each questline being played with its current chapter, and the ones on
    offer."""
    from core.questlines import quests_section

    page = quests_section(context)
    if not page.get("available"):
        return "Questlines aren't set up here."
    said = [f"It's {page['season']['name']}."] if page.get("season") else []
    for q in page.get("active") or []:
        current = next((c for c in q["chapters"] if c["state"] == "current"), None)
        said.append(f"{q['icon']} {q['name']}: chapter {q['current'] + 1} of {q['count']}"
                    + (f", \"{current['title']}\" ({current['done']} of {current['total']} done)" if current else ""))
    offers = page.get("offers") or []
    if offers:
        said.append("On offer: " + ", ".join(o["name"] for o in offers[:6]) + ". Say \"start <the questline>\".")
    if len(said) <= 1 and not offers:
        said.append("No questlines going or on offer right now.")
    return " ".join(said)


def _start_questline(context, arguments: dict) -> str:
    """Tool start_questline: starts the questline on offer the person names (quest.start)."""
    from core.questlines import quests_section

    said = " ".join(str(arguments.get("name") or "").lower().split())
    offers = quests_section(context).get("offers") or []
    found = [o for o in offers if said and (said in o["name"].lower() or o["name"].lower() in said)]
    if not found:
        return ("I don't see that questline on offer. On offer now: " + ", ".join(o["name"] for o in offers) + "."
                if offers else "There's no questline on offer right now.")
    return _run(context, "quest.start", {"starter_id": found[0]["id"]})


def _list_places(context, arguments: dict) -> str:
    """Tool list_places: the person's places, what happens on arriving at each, and how often they've been."""
    book = getattr(context, "places", None)
    if book is None or not book.places:
        return "You haven't saved any places yet: add one on the World Map's Places."
    return "Your places: " + "; ".join(
        f"{p.name} ({p.on_arrive.lower()}" + (f", {p.arrivals} visit{'s' if p.arrivals != 1 else ''})" if p.arrivals
                                              else ")") for p in book.places) + "."


def _arrive_place(context, arguments: dict) -> str:
    """Tool arrive_place: "I'm at the gym": the place's arrival (place.arrive), by the place's name the person
    said; nothing about where they are is read."""
    book = getattr(context, "places", None)
    said = " ".join(str(arguments.get("name") or "").lower().split())
    found = [p for p in (book.places if book is not None else []) if said and (said in p.name.lower()
                                                                               or p.name.lower() in said)]
    if not found:
        return "I don't have a place by that name. Ask me what places you have."
    return _run(context, "place.arrive", {"place_id": found[0].place_id})


def _project(context, name):
    """The project a name means (links.find over projects), or (None, what to say back)."""
    from core import links

    if not str(name or "").strip():
        return None, "Which project?"
    ref, problem = links.find(context, str(name), ["project"])
    if ref is None:
        return None, problem
    return context.projects.get_project(ref.partition(":")[2]), None


_ALONE = ("none", "no project", "on its own", "its own", "standalone", "nothing")


def _set_mission_project(context, arguments: dict) -> str:
    """Tool set_mission_project: makes the named mission part of the named project (mission.project), or stands it
    on its own for "none"; in its own words when it can't."""
    mission = _find_mission(context, arguments.get("mission"))
    if mission is None:
        return "I don't see a mission by that name. Ask me what missions you have."
    wanted = str(arguments.get("project") or "").strip()
    if wanted.lower() in _ALONE:
        return _run(context, "mission.project", {"mission_id": mission.mission_id, "project_id": ""})
    project, problem = _project(context, wanted)
    if project is None:
        return problem
    return _run(context, "mission.project", {"mission_id": mission.mission_id, "project_id": project.project_id})


def _get_project_missions(context, arguments: dict) -> str:
    """Tool get_project_missions: a project's progress and its missions, each with how far along it is and what's
    next."""
    from core.mission_projects import mission_card, missions_for, progress

    if getattr(context, "projects", None) is None:
        return "Projects aren't set up here."
    project, problem = _project(context, arguments.get("project"))
    if project is None:
        return problem
    p = progress(context, project)
    head = f"{project.name}: {p['percent']}% along" if p["percent"] is not None else f"{project.name}: nothing to count yet"
    cards = [mission_card(context, m) for m in missions_for(context, project.project_id)]
    if not cards:
        return head + ". No missions are part of it yet; say \"make <a mission> part of " + project.name + "\"."
    lines = [f"{c['name']} ({c['status']}, {c['percent']}%" + (f", next: {c['next']}" if c["next"] else "") + ")"
             for c in cards]
    return f"{head}, {p['missions_done']} of {p['missions_total']} missions done. " + "; ".join(lines) + "."


def register_game_actions(registry: AssistantActionRegistry) -> None:
    """Registers the boss, questline and place tools, and a mission's project (DEC-0152)."""
    registry.register(AssistantAction(
        name="set_mission_project", domain="missions",
        description="Make one of the person's missions part of a project (or 'none' to stand it on its own).",
        parameters={"type": "object", "properties": {
            "mission": {"type": "string", "description": "The mission's name, as they said it."},
            "project": {"type": "string", "description": "The project's name, or 'none'."}},
            "required": ["mission", "project"]},
        handler=_set_mission_project,
        trigger_phrases=("part of the", "part of my", "put the mission", "mission part of", "mission to the project",
                         "out of the project"),
    ))
    registry.register(AssistantAction(
        name="get_project_missions", domain="missions",
        description="A project's progress and its missions: how far along each is and what's next.",
        parameters={"type": "object", "properties": {
            "project": {"type": "string", "description": "The project's name, as they said it."}},
            "required": ["project"]},
        handler=_get_project_missions,
        trigger_phrases=("missions for the", "missions in the", "missions on the", "how far along is the",
                         "project's missions", "progress on the"),
    ))
    registry.register(AssistantAction(
        name="get_bosses", domain="missions",
        description="The person's boss battles (debts and missions made into bosses): HP left and what a hit does.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_get_bosses,
        trigger_phrases=("my bosses", "boss fights", "boss battles", "how's the boss", "boss fight"),
    ))
    registry.register(AssistantAction(
        name="make_boss", domain="missions",
        description="Make one of the person's missions a boss fight, by the mission's name.",
        parameters={"type": "object", "properties": {
            "mission": {"type": "string", "description": "The mission's name, as they said it."}},
            "required": ["mission"]},
        handler=_make_boss,
        trigger_phrases=("make it a boss fight", "a boss fight", "make a boss"),
    ))
    registry.register(AssistantAction(
        name="get_questlines", domain="missions",
        description="The season's questlines: the ones being played (their current chapter) and the ones on offer.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_get_questlines,
        trigger_phrases=("my questlines", "questlines", "what quests", "my quests", "questline"),
    ))
    registry.register(AssistantAction(
        name="start_questline", domain="missions",
        description="Start one of the questlines on offer, by its name.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The questline's name, as they said it."}},
            "required": ["name"]},
        handler=_start_questline,
        trigger_phrases=("start the questline", "start questline", "begin the questline"),
    ))
    registry.register(AssistantAction(
        name="list_places", domain="maps",
        description="The person's saved places (location quests) and what happens on arriving at each.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_list_places,
        trigger_phrases=("my places", "what places", "location quests"),
    ))
    registry.register(AssistantAction(
        name="arrive_place", domain="maps",
        description="The person says they've arrived at one of their saved places (\"I'm at the gym\"), by its name.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "The place's name, as they said it."}},
            "required": ["name"]},
        handler=_arrive_place,
        trigger_phrases=("i'm at the", "i am at the", "just got to the", "i'm here at"),
    ))
