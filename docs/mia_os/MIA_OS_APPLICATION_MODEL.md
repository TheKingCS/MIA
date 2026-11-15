# MIA OS: the application model (Prompt 03 §2, §3)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of the application framework
([MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md)), DEC-0175 proposed.*

## 1. The eleven kinds

Status: **E** exists in the repository, **P** proposed here.

| Kind | What it is | Registered by | Talks through | Managed by | Example | Status |
|---|---|---|---|---|---|---|
| Core OS component | the base system MIA runs on | the OS image | systemd, D-Bus | the OS (bootc updates) | kernel, compositor, NetworkManager | E (outside MIA) |
| Platform service | a shared MIA service any app uses | a field on `AppContext`, built in `core/runtime.build_services` | Python calls in-process; the local API out of process | the MIA Runtime | stores, the gate, the action contract, sync, search, model access | E |
| Background job | work on a schedule or a trigger | `core/background_jobs.JOBS` / `DAILY_CHECKS` | the services | the scheduler and homeostasis | backups, World Intelligence's watches | E |
| **Capability** | **one thing MIA can do: a tool and/or an action kind** | the tool registry, `ACTION_TYPES`, the UAL catalogue | the action contract (propose, approve, execute, record, undo) | the registry; grants (DEC-0156) | `world_watch.add` + `watch_for` | E (fields: P) |
| **Application** | **a person-facing bundle: a manifest over capabilities, with surfaces, stores and jobs** | `core/web_surfaces.APPS` today; one manifest (P) | its surfaces call `/api/*`; never another app's internals | the app manager (P), the module manager (Qt) | World, Smart Closet, Budget | E (manifest: P) |
| Surface | one way an app is shown | its page in `web/`, its Qt module, its glasses card, the phone app's screen | `/api/state`, `/api/actions`, `/api/live` | the web shell (`web/shell.js`) | `web/intel.html` | E |
| Agent | a model-driven worker with a role and a scope | its own module (council, specialists, Game Master, Night School) | capabilities, never stores directly | owner-only gates; the lab | the specialists, the council | E |
| Skill | a learned procedure made of capabilities | `core/taught_skills.py`, browser routines | the capabilities it's made of, each through its gate | practice state, clean runs | "the Friday reset" | E |
| Extension | added code that contributes capabilities or surfaces to an app | "Add Module" today (in-process); the extension host (P) | the capability contract over the local API | the extension host (P) | a lab-built module | E in-process / P sandboxed |
| Connector | brings outside data in, read-only, previewed | `core/connectors.py`, `core/world_sources.py`, Plaid, IMAP | imports as one undoable change | its own store and loop | a bank CSV, a feed | E |
| External application | a program that isn't MIA's: a Linux GUI app, an Android app, a website | nothing in MIA; the OS installs it (Flatpak) | Send to MIA (the UAL), portals; declared capabilities later | the OS; MIA only sees what's sent | Firefox, a CAD program | E (UAL) |

**The rule that keeps these from blurring:** only a **capability** does anything. Apps, agents, skills and
extensions all act by invoking capabilities through the action contract, so permissions, undo, parity and the history
apply the same way whoever asks. That's how "check the greenhouse humidity" works without knowing which app owns it:
MIA resolves the intent to a capability, not to an app.

## 2. What an application is made of

| Part | Mandatory? | Today | Notes |
|---|---|---|---|
| Identity: id, name, icon, tagline, area | yes | `App` in `core/web_surfaces.py` | the id is the module id, stable forever |
| Capabilities: its tool domains and action families | yes (an app with none is a page of reading) | `App.domains`, `ACTION_TYPES` prefixes | parity requires each action to have a tool and a control |
| At least one surface | yes | a web page, or a Qt module, or a glasses card, or voice only | `App.page = None` means not on the web yet |
| Stores | no | `PERSONAL_STORES` / `HOUSEHOLD_STORES` entries | each under the atomic write; new ones under the epistemic contract (DEC-0173) |
| Background jobs | no | `JOBS` / `DAILY_CHECKS` | declared so homeostasis can defer them |
| Loops | yes, or a reason | `core/loops.py` or `work/loop_coverage.json` | `tests/test_loop_coverage.py` |
| Device declarations | yes | implicit: parity rows per device | explicit in the manifest (P) |
| Permissions | yes | implicit: the action contract's approval | explicit per capability (P, DEC-0156) |
| Documentation | yes | file openings, docstrings, `docs/ATLAS.md` | `tests/test_documentation.py` |
| Extensions | no | — | P |

**The capability is reusable without opening the app** (prompt §2's greenhouse example): the Greenhouse page shows
sensor readings, but the readings are a capability any app, the glasses, a skill or MIA herself can call. This is
true today (`core/sensors.py` is read by the life state, the greenhouse page and the daily checks).

## 3. The manifest, assembled from code (proposed)

```
AppManifest
  id, name, icon, tagline, area, description          ← web_surfaces.App
  surfaces: {web: "intel.html", qt: module_id?, glasses: [card ids], phone: bool, voice: bool}
  capabilities: [capability ids]                      ← tools in App.domains + action kinds by family
  stores: [store names]                               ← the stores its capabilities use (declared)
  jobs: [job names]                                   ← background_jobs entries it owns
  devices: {pc, phone, glasses, pi: full | view | voice | none}   ← core/parity rows
  permissions: union of its capabilities' declared needs           ← DEC-0156
  status: installed | available | running | degraded | failed | disabled | missing_dependency  (lifecycle doc)
```

`core/app_manifest.py` (proposed) builds this for every app at start, and a test checks that every part named exists
and that nothing exists unclaimed (every tool domain and action family belongs to an app, or to MIA herself). That test
is the "registration from code" requirement (AF-1) made checkable.

## 4. Application technologies (prompt §3)

| Technology | Supported? | How |
|---|---|---|
| MIA web app (a page in `web/` over `/api/*`) | yes, the main kind | first-party, in the runtime |
| Qt module | classic view only (DEC-0168: fixes only) | discovered by the module manager |
| Native Linux GUI app | yes, as an external app | Flatpak; Send to MIA; later a MIA portal |
| Progressive web app | not needed: the web screens already are MIA's web app | — |
| Android app | on the phone's own Android | the MIA Android app (`android-phone/`) is a surface |
| Container component | for heavy, separate services only (a model server, SearXNG) | podman / systemd, as services MIA calls |
| Embedded device app | the glasses relay, greenhouse firmware, sensors | devices with their own platform, reached through declared capabilities |
| Capability-only (no screen) | yes | an app whose surfaces are voice and other apps' pages |

Not forcing one packaging: MIA's own code is one unit; the rest uses each platform's native packaging (prompt §3).
