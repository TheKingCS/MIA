"""
core.app_registry
===================

The Application Registry (DEC-0175, DEC-0178; `docs/mia_os/MIA_OS_APPLICATION_REGISTRY.md`, migration phase M1):
MIA's authoritative inventory of her own applications, read from one manifest per app (`apps/<id>/manifest.json`),
and checked against the code so the manifests can't drift from what's really there.

**A manifest** says what an app is (id, name, icon, area, version), what it's made of (its surfaces: web pages, the Qt
module, glasses cards; its stores; its engine files, agents, workflows and integrations as they're filled in), what it
can do (its tools and action kinds: its capabilities), what it uses from other apps (`uses`: tool domains it shares),
its permissions and dependencies (empty until DEC-0156's grants and phase M5), and where it runs (`runtime.devices`,
`runtime.background`: its jobs and daily checks). `apps/mia/manifest.json` is MIA herself: the platform's own parts.
The manifest is an index; it holds no code.

**Checking** (`Registry.problems`): every tool, action kind, store, job and daily check in the code is claimed by
exactly one manifest, and every one a manifest claims exists; every web page and Qt module named exists; ids are
unique and match their folders; dependencies name apps that exist; the schema version is known. `tests/test_app_registry.py`
fails on any problem, so adding a capability without claiming it, or removing one a manifest still names, is caught.

**Asking** (the queries MIA's own understanding of her ecosystem is built from, phase M2): the inventory, an app's
capabilities, the app behind a capability, the apps that depend on one, the apps that can run on a device. Answers come
from the manifests and the code, never from a model.

Nothing here changes behaviour yet: the app list still comes from `core/web_surfaces.APPS` until phase M3, and a test
keeps the two in agreement.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.data_root import CODE_ROOT
from core.logger import get_logger

log = get_logger(__name__)

APPS_DIR = CODE_ROOT / "apps"
SCHEMA_VERSIONS = (1,)
REQUIRED = ("manifest_version", "id", "name", "version", "entry", "components", "capabilities", "runtime")


@dataclass
class Registry:
    """Every manifest, by app id, and the problems found loading them."""
    manifests: dict = field(default_factory=dict)
    load_problems: list = field(default_factory=list)

    # ---------------------------------------------------------------- asking

    def apps(self, include_retired: bool = False) -> list[dict]:
        """Every app's manifest (not MIA herself), retired ones only when asked."""
        return [m for i, m in sorted(self.manifests.items())
                if i != "mia" and (include_retired or not m.get("retired"))]

    def get(self, app_id: str) -> Optional[dict]:
        """One app's manifest, or None."""
        return self.manifests.get(app_id)

    def owner_of(self, capability: str) -> Optional[str]:
        """The app that owns a tool or action kind, or None."""
        for app_id, m in self.manifests.items():
            caps = m.get("capabilities", {})
            if capability in caps.get("tools", []) or capability in caps.get("actions", []):
                return app_id
        return None

    def capabilities_of(self, app_id: str) -> dict:
        """An app's tools and action kinds ({tools, actions})."""
        caps = (self.get(app_id) or {}).get("capabilities", {})
        return {"tools": list(caps.get("tools", [])), "actions": list(caps.get("actions", []))}

    def dependents_of(self, app_id: str) -> list[str]:
        """The apps whose manifests depend on this one."""
        return sorted(i for i, m in self.manifests.items()
                      if any(d.get("application_id") == app_id for d in m.get("dependencies", [])))

    def on_device(self, device: str) -> list[str]:
        """The apps usable on a device (pc, phone, glasses) in any way."""
        return sorted(m["id"] for m in self.apps() if m.get("runtime", {}).get("devices", {}).get(device, "none") != "none")

    # ---------------------------------------------------------------- checking

    def problems(self) -> list[str]:
        """What doesn't agree between the manifests and the code (see the module's opening); [] when all is well."""
        import core.actions  # noqa: F401  (the action contract first, as MIA loads it)
        from core.actions import ACTION_TYPES
        from core.background_jobs import DAILY_CHECKS, JOBS
        from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

        out = list(self.load_problems)
        tools = set(_tool_names())
        actions = set(ACTION_TYPES)
        stores = {n for n, _c in list(PERSONAL_STORES) + list(HOUSEHOLD_STORES)}
        jobs = {n for n, _s, _m in JOBS} | {n for n, _m in DAILY_CHECKS}
        out += _claims(self.manifests, lambda m: m["capabilities"].get("tools", []), tools, "tool")
        out += _claims(self.manifests, lambda m: m["capabilities"].get("actions", []), actions, "action kind")
        out += _claims(self.manifests, lambda m: m["components"].get("data", []), stores, "store")
        out += _claims(self.manifests, lambda m: m["runtime"].get("background", []), jobs, "job or daily check")
        for app_id, m in self.manifests.items():
            iface = m["components"].get("interface", {})
            for page in iface.get("web", []):
                if not (CODE_ROOT / "web" / page).is_file():
                    out.append(f"{app_id}: its page web/{page} doesn't exist")
            for folder in iface.get("qt", []):
                if not (CODE_ROOT / folder / "module.py").is_file():
                    out.append(f"{app_id}: its Qt module {folder} doesn't exist")
            for dep in m.get("dependencies", []):
                if dep.get("application_id") not in self.manifests:
                    out.append(f"{app_id}: depends on {dep.get('application_id')}, which isn't an app")
        return out


def _tool_names() -> list[str]:
    """Every tool MIA registers on the PC (core/parity.desktop_registry)."""
    from core import parity

    return list(parity.desktop_registry()._actions)


def _claims(manifests: dict, of, real: set, what: str) -> list[str]:
    """Problems with one kind of part: claimed by two apps, claimed but not in the code, or in the code but unclaimed."""
    seen: dict = {}
    out = []
    for app_id, m in sorted(manifests.items()):
        for name in of(m):
            if name in seen:
                out.append(f"{what} {name} is claimed by both {seen[name]} and {app_id}")
            seen[name] = app_id
            if name not in real:
                out.append(f"{app_id} claims the {what} {name}, which isn't in the code")
    for name in sorted(real - set(seen)):
        out.append(f"the {what} {name} isn't claimed by any app's manifest")
    return out


def load(folder: Path = APPS_DIR) -> Registry:
    """Reads every apps/<id>/manifest.json; a manifest that can't be read, or lacks a required field, is a problem,
    not a crash."""
    reg = Registry()
    for path in sorted(folder.glob("*/manifest.json")):
        try:
            m = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as problem:
            reg.load_problems.append(f"{path.parent.name}: its manifest can't be read ({type(problem).__name__})")
            continue
        missing = [k for k in REQUIRED if k not in m]
        if missing:
            reg.load_problems.append(f"{path.parent.name}: its manifest lacks {', '.join(missing)}")
            continue
        if m["manifest_version"] not in SCHEMA_VERSIONS:
            reg.load_problems.append(f"{path.parent.name}: manifest version {m['manifest_version']} isn't known")
            continue
        if m["id"] != path.parent.name:
            reg.load_problems.append(f"{path.parent.name}: its manifest says id {m['id']}")
            continue
        if m["id"] in reg.manifests:
            reg.load_problems.append(f"{m['id']}: two manifests")
            continue
        reg.manifests[m["id"]] = m
    return reg
