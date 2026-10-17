"""
core.game_actions
===================

The game layer's changes (DEC-0028, docs/GAME_LAYER.md), on the action
contract in core/actions.py.

- Reward Shop: `shop_reward.add/edit/delete` (the rewards you set) and
  `shop.buy` (spend credits on one). Undo gives the credits back.
- Boss battles: `boss.add` makes a mission a boss fight, `boss.remove`
  turns it back into a plain mission (debts are bosses on their own).
- Questlines (core/questlines.py): `quest.start` a seasonal or any-time
  starter, `quest.add` your own (one chapter per line), `quest.remove`.

A person's own credits and shop: these are child-safe.
"""

from __future__ import annotations

from core.actions import ACTION_TYPES, ActionError, ActionType, _need
from core.record_actions import Field, Record, record_form, record_kinds

ONCE, AGAIN = "Just Once", "Again And Again"

SHOP_REWARD = Record("shop_reward", "reward", "reward_id", "get_reward", "add_reward", "update_reward", "delete_reward",
                     store="reward_shop", fields=(
                         Field("name", "Reward", "text", True),
                         Field("cost", "Cost (credits)", "int", True, say="cost"),
                         Field("icon", "Icon (an emoji)", "text", default="🎁", say="icon", quiet_default=True),
                         Field("buy", "Can you buy it", "choice", options=(AGAIN, ONCE), default=AGAIN,
                               say="buy it", quiet_default=True),
                         Field("note", "Note", "textarea"),
                     ))


def forms() -> dict:
    return {"shop_reward": record_form(SHOP_REWARD)}


def _person(context):
    profiles = getattr(context, "profiles", None)
    profile_id = getattr(context, "profile_id", None)
    try:
        return (profiles.get_profile(profile_id) if profile_id else None) or profiles.get_active_profile()
    except Exception:
        return None


def _reward(context, params):
    reward = _need(context, "reward_shop").get_reward(str(params.get("reward_id") or ""))
    if reward is None:
        raise ActionError("That reward isn't in your shop anymore.")
    return reward


def _describe_buy(context, params) -> str:
    from core.reward_shop import balance

    reward = _reward(context, params)
    shop = context.reward_shop
    left = balance(context, _person(context))["left"]
    if not shop.available(reward):
        raise ActionError(f"You already claimed {reward.name}.")
    if reward.cost > left:
        raise ActionError(f"{reward.name} costs {reward.cost:,} credits; you have {left:,}. {reward.cost - left:,} to go.")
    return f"Spend {reward.cost:,} credits on {reward.icon} {reward.name} ({left:,} → {left - reward.cost:,} left)"


def _buy(context, params) -> str:
    from core.reward_shop import balance

    reward = _reward(context, params)
    try:
        context.reward_shop.buy(reward.reward_id, balance(context, _person(context))["left"])
    except ValueError as problem:
        raise ActionError(str(problem)) from None
    return f"{reward.icon} {reward.name} is yours. Enjoy it."


def _priced(describe):
    """A reward costs at least 1 credit: said when it's proposed."""
    def checked(context, params):
        if "cost" in params:
            try:
                ok = float(str(params.get("cost")).replace(",", "")) >= 1
            except ValueError:
                ok = False
            if not ok:
                raise ActionError("A reward has to cost at least 1 credit.")
        return describe(context, params)
    return checked


def _boss_mission(context, params, want: bool):
    mission = _need(context, "missions").get_mission(str(params.get("mission_id") or ""))
    if mission is None:
        raise ActionError("That mission isn't there anymore.")
    book = _need(context, "boss_book")
    if want and mission.mission_id in book.missions:
        raise ActionError(f"{mission.name} is already a boss fight.")
    if not want and mission.mission_id not in book.missions:
        raise ActionError(f"{mission.name} isn't a boss fight.")
    if want and not mission.objectives:
        raise ActionError("Give it objectives first: they're the boss's HP.")
    return mission


def _boss_add(context, params) -> str:
    mission = _boss_mission(context, params, True)
    context.boss_book.add_mission(mission.mission_id)
    return f"{mission.name} is a boss fight. Every objective is a hit."


def _boss_remove(context, params) -> str:
    mission = _boss_mission(context, params, False)
    context.boss_book.remove_mission(mission.mission_id)
    return f"{mission.name} is a plain mission again."


def _quest(context, params):
    quest = _need(context, "quest_book").get(str(params.get("quest_id") or ""))
    if quest is None:
        raise ActionError("That questline isn't there anymore.")
    return quest


def _starter(params):
    from core.questlines import STARTER_BY_ID

    starter = STARTER_BY_ID.get(str(params.get("starter_id") or ""))
    if starter is None:
        raise ActionError("That questline isn't one MIA knows.")
    return starter


def _describe_quest_start(context, params) -> str:
    _need(context, "quest_book")
    _need(context, "missions")
    starter = _starter(params)
    return f"Start the questline {starter.icon} {starter.name}: " + " → ".join(t for t, _s, _o in starter.chapters)


def _quest_start(context, params) -> str:
    from core.questlines import start

    starter = _starter(params)
    quest = start(context, starter.starter_id)
    first = quest.chapters[0]
    return f"{quest.icon} {quest.name} begins. Chapter 1: {first.title}. {first.story}".strip()


def _own_chapters(params) -> list:
    from core.questlines import parse_chapters

    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("Give the questline a name.")
    chapters = parse_chapters(params.get("chapters"))
    if len(chapters) < 2:
        raise ActionError("A questline needs at least two chapters, one per line.")
    return chapters


def _describe_quest_add(context, params) -> str:
    _need(context, "quest_book")
    chapters = _own_chapters(params)
    return f"Start your own questline {str(params.get('name')).strip()}: " + " → ".join(c["title"] for c in chapters)


def _quest_add(context, params) -> str:
    from core.questlines import open_chapter

    chapters = _own_chapters(params)
    quest = context.quest_book.add(str(params.get("name")).strip(), chapters,
                                   icon=str(params.get("icon") or "").strip() or "🗺️")
    open_chapter(context, quest)
    return f"{quest.icon} {quest.name} begins. Chapter 1: {quest.chapters[0].title}."


def _quest_remove(context, params) -> str:
    quest = _quest(context, params)
    context.quest_book.remove(quest.quest_id)
    return f"{quest.name} is off your questlines. Its missions stay, and what you earned stays earned."


def _where(params) -> tuple[float, float]:
    try:
        lat, lon = float(params.get("lat")), float(params.get("lon"))
    except (TypeError, ValueError):
        raise ActionError("MIA couldn't tell where you are. Let the app use your location and try again.") from None
    if not (-85 <= lat <= 85 and -180 <= lon <= 180):
        raise ActionError("That isn't a place on the map.")
    return lat, lon


def _new_tiles(context, lat, lon) -> int:
    from core.world_map import around, tile_of

    book = _need(context, "world_map")
    x, y = tile_of(lat, lon)
    from core.world_map import explored, points

    known = set(explored(points(context))) | set(book.first_seen)
    return sum(1 for tx, ty in around(x, y) if f"{tx},{ty}" not in known)


def _describe_checkin(context, params) -> str:
    lat, lon = _where(params)
    new = _new_tiles(context, lat, lon)
    label = str(params.get("label") or "").strip()
    return ("Clear the map around here" + (f" ({label})" if label else "")
            + (f": {new} new {'tile' if new == 1 else 'tiles'}" if new else ": you've been here before"))


def _checkin(context, params) -> str:
    from core import life_events
    from core.gamification import grant_xp
    from core.world_map import XP_CAP, XP_PER_TILE

    lat, lon = _where(params)
    new = _new_tiles(context, lat, lon)
    label = str(params.get("label") or "").strip()
    context.world_map.check_in(lat, lon, label)
    if not new:
        return "Checked in. You've explored here before."
    xp = min(XP_CAP, new * XP_PER_TILE)
    grant_xp(context, xp, "🗺️ New ground!", f"{new} new map {'tile' if new == 1 else 'tiles'} cleared.")
    life_events.record(context.world_map, "explored", f"Explored new ground{' at ' + label if label else ''}",
                       [], {"tiles": new})
    return f"New ground! {new} map {'tile' if new == 1 else 'tiles'} cleared, +{xp} XP."


def _crew(context, params) -> list:
    """The people joining a raid: ids from the household (me if none)."""
    from core.party import members
    from core.person_settings import person_id

    household = {p.profile_id: p for p in members(context)}
    raw = params.get("people")
    ids = raw if isinstance(raw, list) else [x.strip() for x in str(raw or "").split(",") if x.strip()]
    if not ids or ids == ["everyone"]:
        ids = list(household) if raw == "everyone" else [person_id(context)]
    crew = [household[i] for i in ids if i in household]
    if not crew:
        raise ActionError("Pick who's in the raid (people in your household).")
    return crew


def _raid_starter(params):
    from core.party import RAID_BY_ID

    raid = RAID_BY_ID.get(str(params.get("raid_id") or ""))
    if raid is None:
        raise ActionError("That raid isn't one MIA knows.")
    return raid


def _own_raid(params) -> list:
    if not str(params.get("name") or "").strip():
        raise ActionError("Give the raid a name.")
    objectives = [o.strip(" -•*") for o in str(params.get("objectives") or "").splitlines() if o.strip(" -•*")]
    if len(objectives) < 2:
        raise ActionError("A raid needs at least two jobs, one per line.")
    return objectives


def _describe_raid(context, params, own: bool) -> str:
    from core.party import share_out

    _need(context, "missions")
    crew = _crew(context, params)
    if own:
        name, objectives = str(params.get("name")).strip(), _own_raid(params)
    else:
        raid = _raid_starter(params)
        name, objectives = f"{raid.icon} {raid.name}", list(raid.objectives)
    shared = share_out(objectives, [p.name for p in crew])
    return f"Start {name} with {', '.join(p.name for p in crew)}: " + "; ".join(f"{who}: {o}" for o, who in shared)


def _raid(context, params, own: bool) -> str:
    from core.party import start_raid

    crew = _crew(context, params)
    if own:
        start_raid(context, str(params.get("name")).strip(), str(params.get("icon") or "").strip() or "⚔️", "",
                   _own_raid(params), [p.profile_id for p in crew])
        name = str(params.get("name")).strip()
    else:
        raid = _raid_starter(params)
        start_raid(context, raid.name, raid.icon, raid.summary, list(raid.objectives), [p.profile_id for p in crew])
        name = raid.name
    return f"{name} is on. Everyone has their jobs; the reward is shared when it's done."


def _board(params) -> bool:
    return str(params.get("on")).strip().lower() in ("true", "1", "yes", "on")


def _describe_board(context, params) -> str:
    return ("Put yourself on the household leaderboard (your wins this week, never money)" if _board(params)
            else "Take yourself off the household leaderboard")


def _set_board(context, params) -> str:
    from core import person_settings

    person_settings.put(context, "party.leaderboard", _board(params))
    return "You're on the leaderboard." if _board(params) else "You're off the leaderboard."


def _place(context, params):
    place = _need(context, "places").get(str(params.get("place_id") or ""))
    if place is None:
        raise ActionError("That place isn't in your places anymore.")
    return place


def _place_fields(context, params) -> dict:
    from core.places import ARRIVALS, DEFAULT_RADIUS_M

    _need(context, "places")
    name = str(params.get("name") or "").strip()
    if not name:
        raise ActionError("Give the place a name, like Gym or Grocery Store.")
    lat, lon = _where(params)
    try:
        radius = int(float(params.get("radius") or DEFAULT_RADIUS_M))
    except (TypeError, ValueError):
        radius = DEFAULT_RADIUS_M
    if not 30 <= radius <= 2000:
        raise ActionError("How close counts as there: between 30 and 2,000 meters.")
    on_arrive = str(params.get("on_arrive") or "Just Remind Me")
    if on_arrive not in ARRIVALS:
        raise ActionError("Pick what happens when you get there.")
    return {"name": name, "lat": lat, "lon": lon, "radius_m": radius, "on_arrive": on_arrive,
            "note": str(params.get("note") or "").strip()}


def _describe_place_add(context, params) -> str:
    f = _place_fields(context, params)
    return f"Add the place {f['name']} (within {f['radius_m']} m): when you get there, {f['on_arrive'].lower()}"


def _place_add(context, params) -> str:
    f = _place_fields(context, params)
    context.places.add(f["name"], f["lat"], f["lon"], f["radius_m"], f["on_arrive"], f["note"])
    return f"{f['name']} is one of your places."


def _place_arrive(context, params) -> str:
    from core.places import arrival

    place = context.places.arrived(_place(context, params).place_id)
    book = getattr(context, "world_map", None)
    if book is not None:  # being there clears the fog too
        book.check_in(place.lat, place.lon, place.name)
    return arrival(place)["say"]


def _register() -> None:
    from dataclasses import replace

    kinds = [replace(k, describe=_priced(k.describe)) if k.kind != "shop_reward.delete" else k
             for k in record_kinds(SHOP_REWARD, child_ok=True)] + [
        ActionType("shop.buy", "Buy", {"reward_id": "the reward"}, _describe_buy, _buy, True),
        ActionType("boss.add", "Make It A Boss Fight", {"mission_id": "the mission"},
                   lambda c, p: f"Make {_boss_mission(c, p, True).name} a boss fight (its objectives are its HP)", _boss_add, True),
        ActionType("boss.remove", "Not A Boss", {"mission_id": "the mission"},
                   lambda c, p: f"Make {_boss_mission(c, p, False).name} a plain mission again", _boss_remove, True),
        ActionType("quest.start", "Start Questline", {"starter_id": "the questline"}, _describe_quest_start, _quest_start, True),
        ActionType("quest.add", "Make A Questline", {"name": "", "icon": "an emoji",
                                                     "chapters": "one chapter per line: Title: objective; objective"},
                   _describe_quest_add, _quest_add, True),
        ActionType("raid.start", "Start Raid", {"raid_id": "the raid", "people": "profile ids, comma-separated, or everyone"},
                   lambda c, p: _describe_raid(c, p, False), lambda c, p: _raid(c, p, False), True),
        ActionType("raid.add", "Make A Raid", {"name": "", "icon": "an emoji", "objectives": "one job per line",
                                               "people": "profile ids, comma-separated, or everyone"},
                   lambda c, p: _describe_raid(c, p, True), lambda c, p: _raid(c, p, True), True),
        ActionType("party.leaderboard", "Leaderboard", {"on": "true or false"}, _describe_board, _set_board, True),
        ActionType("place.add", "Add Place", {"name": "", "lat": "latitude", "lon": "longitude",
                                              "radius": "meters (150 if left out)", "on_arrive": "what happens there",
                                              "note": "optional reminder"}, _describe_place_add, _place_add, True),
        ActionType("place.delete", "Remove", {"place_id": "the place"},
                   lambda c, p: f"Remove {_place(c, p).name} from your places",
                   lambda c, p: (c.places.delete(_place(c, p).place_id), "Removed.")[1], True),
        ActionType("place.arrive", "I'm Here", {"place_id": "the place"},
                   lambda c, p: f"You're at {_place(c, p).name}", _place_arrive, True),
        ActionType("map.checkin", "I'm Here", {"lat": "latitude", "lon": "longitude", "label": "optional name"},
                   _describe_checkin, _checkin, True),
        ActionType("quest.remove", "Remove Questline", {"quest_id": "the questline"},
                   lambda c, p: f"Take {_quest(c, p).name} off your questlines (its missions stay)", _quest_remove, True),
    ]
    for kind in kinds:
        ACTION_TYPES[kind.kind] = kind


_register()
