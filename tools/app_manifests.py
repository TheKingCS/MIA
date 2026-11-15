"""
tools.app_manifests
=====================

Writes the first canonical manifest of every MIA-native app (DEC-0178, migration phase M1;
`docs/mia_os/MIA_OS_APPLICATION_REGISTRY.md`), generated from today's code so nothing changes behaviour:

    python -m tools.app_manifests write     # apps/<id>/manifest.json for every app, and apps/mia/ for MIA herself
    python -m tools.app_manifests check     # what core/app_registry.py would refuse, without writing

**After this first run the manifests are the source** (DEC-0175: one authoritative manifest per app): a new tool,
action kind, store or job is added to its app's manifest by hand (or by the scaffold), and
`tests/test_app_registry.py` fails until it is. `write` refuses to overwrite manifests that exist, unless given
`--force`, so it can't silently undo a hand edit.

**Who owns what** comes from the code where the code says it and from tables here where it doesn't:
- tools: by tool domain, from each app's `domains` in `core/web_surfaces.APPS` (a domain listed by two apps goes to
  the first in `SHARED_DOMAIN_OWNER`, the other lists it under `uses`);
- action kinds: by family (the part before the dot), from `FAMILY_OWNER`, checked by hand against what each family
  does, because a family's name often isn't an app's (only 24 of 140 match);
- stores: from `STORE_OWNER`, else a family or app of the same name, else MIA herself (platform stores);
- jobs and daily checks: from `JOB_OWNER`, else MIA herself;
- devices: from `core/parity.matrix` (what each app can actually do on each device);
- surfaces: its web page, its Qt module (if `modules/<id>/module.py` exists), its glasses cards.

`apps/mia/manifest.json` is MIA herself: the platform's own tools, actions, stores and jobs (the gate, the history,
links, the scheduler's daily tick, the communication log...), so that everything is claimed exactly once.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
APPS_DIR = ROOT / "apps"
SCHEMA_VERSION = 1

SHARED_DOMAIN_OWNER = {"maintenance": "garage", "ledger": "business", "expeditions": "expeditions"}

# Action family -> the app that owns it (checked by hand, 2026-11-15). "mia" is MIA herself.
FAMILY_OWNER = {
    "alarm": "toolbox", "answer": "assistant", "app": "settings", "art": "assistant", "asset": "garage",
    "batch": "greenhouse", "bill": "budget", "boss": "character", "budget_target": "budget", "camera": "security",
    "capture": "assistant", "character": "character", "closet": "closet", "closet_piece": "closet",
    "comms": "assistant", "communication": "assistant", "component": "workshop", "connect": "settings",
    "connection": "relationships", "conversation": "assistant", "cooking": "kitchen", "course": "classroom",
    "craft": "workshop", "craft_recipe": "workshop", "creation": "assistant", "customer": "business",
    "debt": "budget", "direction": "dashboard", "dungeon": "dungeon", "energy": "power", "energy_source": "power",
    "event": "calendar", "exercise": "workout", "expedition": "expeditions", "expense": "budget",
    "experiment": "greenhouse", "failures": "issues", "firstboot": "web_home", "fitness": "workout",
    "flock": "flock", "freedom": "freedom", "gap": "assistant", "gear": "expeditions", "goods": "workshop",
    "gps_track": "maps", "grocery": "kitchen", "grow": "greenhouse", "inbox": "inbox", "income": "budget",
    "income_source": "budget", "insurance": "insurance", "insurance_policy": "insurance",
    "insurance_quote": "insurance", "inventory": "real_estate", "job": "workshop", "journal": "notes",
    "lab": "lab", "lab_reading": "lab", "lesson": "classroom", "life_note": "life_notes", "listing": "workshop",
    "loop": "dungeon", "maintenance": "garage", "maintenance_task": "garage", "map": "maps", "market": "workshop",
    "material": "workshop", "meal": "kitchen", "med": "workout", "memory": "assistant", "mission": "missions",
    "mission_idea": "missions", "music": "music", "myfile": "files", "news": "good_news",
    "notification": "assistant", "objective": "missions", "obligation": "compliance", "online": "assistant",
    "operating": "operating_journal", "order": "business", "pantry": "kitchen", "party": "play",
    "path": "classroom", "pathway": "missions", "person": "relationships", "pet": "relationships",
    "place": "play", "plan": "knowledge", "play": "play", "playlist": "music", "portal": "web_home",
    "portfolio": "business", "price": "world_intel", "product": "workshop", "profile": "settings",
    "project": "dashboard", "property": "real_estate", "quest": "play", "quote": "business", "raid": "play",
    "recipe": "kitchen", "record": "workout", "records": "assistant", "requirement": "world_intel",
    "routine": "household", "saga": "character", "sale": "workshop", "security": "security",
    "sensor": "field_kit", "setting": "settings", "shop": "play", "shop_expense": "reward_shop",
    "shop_reward": "reward_shop", "sleep": "workout", "starter": "settings", "style": "settings",
    "subject": "classroom", "task": "dashboard", "taught_skill": "taught_skills", "textbook": "classroom",
    "theme": "settings", "track": "music", "trade": "classroom", "trail_map": "maps", "training": "workout",
    "trip": "expeditions", "undo": "assistant", "visit": "workout", "wallet": "assistant",
    "waypoint": "navigation", "weather": "web_home", "why": "dashboard", "world": "play",
    "world_find": "world_intel", "world_intel": "world_intel", "world_source": "world_intel",
    "world_watch": "world_intel", "browser": "browser", "workout": "workout",
}

# Store (its personal_data name) -> owning app, where the name doesn't say. The rest: same-named app or family, else MIA.
STORE_OWNER = {
    "journal": "notes", "private_journal": "notes", "intents": "dashboard", "user_memories": "assistant",
    "conversations": "assistant", "traces": "assistant", "ratings": "assistant", "response_style": "assistant",
    "creations": "assistant", "art": "assistant", "taught_skills": "taught_skills", "browser_routines": "browser",
    "finance": "budget", "net_worth": "budget", "plaid": "budget", "ledger": "business", "business_use": "budget",
    "health": "workout", "fitness": "workout", "training": "workout", "cooking": "kitchen",
    "gps_tracks": "maps", "places": "maps", "waypoints": "navigation", "trips": "expeditions",
    "lite_captures": "field_kit", "data_logger": "field_kit", "scripts": "field_kit", "energy": "power",
    "grow_lab": "greenhouse", "homestead": "greenhouse", "materials": "workshop", "components": "workshop",
    "products": "workshop", "craft_recipes": "workshop", "jobs": "workshop", "boss_book": "character",
    "quest_book": "play", "living_worlds": "play", "world_map": "play", "saga_moments": "character",
    "recreation": "play", "obligations": "compliance", "paths": "classroom", "textbooks": "classroom",
    "id_wallet": "assistant", "online_reminders": "assistant", "notifications": "assistant",
    "connections": "relationships", "direction": "dashboard", "loop": "dungeon", "failures": "issues",
    "freedom_log": "freedom", "operating_journal": "operating_journal", "life_notes": "life_notes",
    "memory_vault": "vault", "record_sets": "assistant", "my_record_sets": "assistant", "plans": "knowledge",
    "trade_session": "classroom", "requirements": "world_intel", "prices": "world_intel",
    "world_intel": "world_intel", "projects": "dashboard", "tasks": "dashboard", "insights": "dashboard",
    "alarms": "toolbox", "email_drafts": "inbox",
}

# Scheduler jobs and daily checks -> owning app; the rest are MIA's own.
JOB_OWNER = {
    "alarms": "toolbox", "power": "power", "finance_snapshots": "budget", "homestead_snapshots": "greenhouse",
    "lite_captures": "field_kit", "inbox": "inbox", "inbox_mail": "inbox", "online": "assistant",
    "mission_auto_assignment": "missions", "world_intel": "world_intel", "birthday": "relationships",
    "calendar_digest": "calendar", "budget_nudge": "budget", "maintenance_insight": "garage",
    "mission_insight": "missions", "recurring_mission": "missions", "rewards": "reward_shop",
    "journal_reflection": "notes", "warranty": "garage", "chronicle": "dashboard", "grow_alert": "greenhouse",
    "insurance_renewal": "insurance", "obligation_reminders": "compliance", "loop": "dungeon",
    "fix_report": "issues", "operating_journal": "operating_journal", "good_news": "good_news",
    "vault_captions": "vault", "greenhouse": "greenhouse", "chronicle_issue": "dashboard",
    "skill_pattern_insight": "skills", "skill_decline_insight": "skills", "skill_momentum_insight": "skills",
    "seasons_of_memory": "memories",
}

PLATFORM = {"id": "mia", "name": "MIA", "icon": "✦", "tagline": "Herself: the platform every app stands on.",
            "description": "MIA's own platform: the communication gate, the history, links, the scheduler's daily "
                           "tick, model access, sync and the other shared services (DEC-0173, DEC-0175)."}


def _safe_name(path: Path) -> str:
    """A path relative to the repository, with forward slashes."""
    return path.relative_to(ROOT).as_posix()


def build() -> dict[str, dict]:
    """Every manifest, from today's code: {app id: manifest}. Pure apart from reading the code's registries."""
    import core.actions  # noqa: F401  (the action contract first, as MIA loads it)
    from core import parity
    from core.actions import ACTION_TYPES
    from core.background_jobs import DAILY_CHECKS, JOBS
    from core.glasses_cards import EXTRA, PANELS
    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES
    from core.web_areas import AREAS
    from core.web_surfaces import APPS, RETIRED

    registry = parity.desktop_registry()
    devices = {r["id"]: r for r in parity.matrix(registry)}
    area_of = {}
    for area in AREAS:
        for member in area.members:
            if isinstance(member, str):
                area_of.setdefault(member, area.id)
    domain_owner = {}
    for app in APPS:
        for d in app.domains:
            domain_owner.setdefault(d, SHARED_DOMAIN_OWNER.get(d, app.module_id))
    ids = {a.module_id for a in APPS}
    out = {}
    for app in APPS:
        qt = ROOT / "modules" / app.module_id / "module.py"
        row = devices.get(app.module_id, {})
        out[app.module_id] = {
            "manifest_version": SCHEMA_VERSION, "id": app.module_id, "name": app.name, "icon": app.icon,
            "tagline": app.tagline, "description": app.description, "version": "1.0.0",
            "group": app.group, "area": area_of.get(app.module_id, ""),
            "retired": app.module_id in RETIRED,
            "entry": f"web:{app.page}" if app.page else ("qt" if qt.exists() else "voice"),
            "components": {"interface": {"web": [app.page] if app.page else [],
                                         "qt": [_safe_name(qt.parent)] if qt.exists() else [],
                                         "glasses": sorted(c[0] for c in PANELS.get(app.module_id, ())
                                                           + EXTRA.get(app.module_id, ()))},
                           "services": [], "data": [], "agents": [], "workflows": [], "integrations": []},
            "capabilities": {"tools": [], "actions": []},
            "uses": sorted(d for d in app.domains if domain_owner.get(d) != app.module_id),
            "permissions": [], "dependencies": [],
            "runtime": {"devices": {"pc": "full" if row.get("pc", True) else "none",
                                    "phone": "full" if row.get("phone") else "none",
                                    "glasses": "view" if row.get("glasses") else "none",
                                    "voice": bool(row.get("voice"))},
                        "background": []},
        }
    out["mia"] = {"manifest_version": SCHEMA_VERSION, **PLATFORM, "version": "1.0.0", "group": "", "area": "",
                  "retired": False, "entry": "voice",
                  "components": {"interface": {"web": [], "qt": [], "glasses": []}, "services": [], "data": [],
                                 "agents": [], "workflows": [], "integrations": []},
                  "capabilities": {"tools": [], "actions": []}, "uses": [], "permissions": [], "dependencies": [],
                  "runtime": {"devices": {"pc": "full", "phone": "full", "glasses": "view", "voice": True},
                              "background": []}}
    for tool in sorted(registry._actions.values(), key=lambda t: t.name):
        out[domain_owner.get(tool.domain, "mia")]["capabilities"]["tools"].append(tool.name)
    for kind in sorted(ACTION_TYPES):
        owner = FAMILY_OWNER.get(kind.split(".")[0], "mia")
        out[owner if owner in out else "mia"]["capabilities"]["actions"].append(kind)
    for name, _cls in list(PERSONAL_STORES) + list(HOUSEHOLD_STORES):
        owner = STORE_OWNER.get(name) or (name if name in ids else FAMILY_OWNER.get(name, "mia"))
        out[owner if owner in out else "mia"]["components"]["data"].append(name)
    for name in [n for n, _s, _m in JOBS] + [n for n, _m in DAILY_CHECKS]:
        owner = JOB_OWNER.get(name, "mia")
        out[owner if owner in out else "mia"]["runtime"]["background"].append(name)
    for manifest in out.values():
        manifest["components"]["data"] = sorted(set(manifest["components"]["data"]))
        manifest["runtime"]["background"] = sorted(set(manifest["runtime"]["background"]))
    return out


def write(force: bool = False, folder: Path = APPS_DIR) -> list[str]:
    """Writes apps/<id>/manifest.json for each app (and MIA herself); refuses when manifests exist unless forced.
    Returns the ids written."""
    if any(folder.glob("*/manifest.json")) and not force:
        raise SystemExit("Manifests already exist: they're the source now. Edit them, or pass --force to regenerate.")
    written = []
    for app_id, manifest in build().items():
        target = folder / app_id / "manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        written.append(app_id)
    return written


def main(argv: Optional[list] = None) -> int:
    """`write [--force]` or `check`; 0 when it worked."""
    args = argv if argv is not None else sys.argv[1:]
    if args[:1] == ["write"]:
        print(f"Wrote {len(write('--force' in args))} manifests to apps/.")
        return 0
    if args[:1] == ["check"]:
        from core import app_registry

        problems = app_registry.load().problems()
        print("\n".join(problems) or "Every manifest agrees with the code.")
        return 1 if problems else 0
    print(__doc__)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
