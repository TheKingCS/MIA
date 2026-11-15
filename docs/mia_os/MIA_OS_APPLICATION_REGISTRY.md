# MIA OS: the runtime-owned application ecosystem and the canonical manifest (prompt 22)

*Claude (Opus), 2026-11-15, answering Zac's handoff (kept verbatim:
[`prompts/22_RUNTIME_OWNED_APPLICATION_ECOSYSTEM.md`](prompts/22_RUNTIME_OWNED_APPLICATION_ECOSYSTEM.md)), his reply to
DEC-0175. DEC-0175 is approved as this handoff's direction; the format and folder choices below are DEC-0178
(proposed). Planning only: nothing is built until the plan's first phase is approved. Fable reviews it (DEC-0174).*

## A. Architecture assessment (the handoff's §11 questions, answered from the repository)

| # | Question | Answer, with evidence |
|---|---|---|
| 1 | Is there an Application Registry? | **Partly, spread over five places that agree by tests:** `core/web_surfaces.APPS` (56 apps: id, name, icon, page, area, tool domains), `core/web_areas.py` (19 areas, the eight destinations), the tool registry (419 tools, 88 domains), `core/actions.ACTION_TYPES` (466 action kinds), `core/capabilities.py` ("what can you do", built from those). No single authoritative inventory. |
| 2 | Manifests or equivalent? | No manifest file. The equivalent is the `App` record plus the domain lists plus the store lists (`core/personal_data.py`), jobs (`core/background_jobs.py`), glasses cards (`core/glasses_cards.CARDS`), loops and parity rows. |
| 3 | How are apps organised? | **By layer, not by app** (CLAUDE.md's rule): engine code in `core/` (an app's store, actions, tools and screen data are separate files, e.g. `core/smart_closet.py`, `core/closet_actions.py`, `core/assistant_closet_actions.py`, `core/web_closet.py`), screens in `web/`, Qt modules in `modules/<id>/`, tests in `tests/`. An app is about fifteen files across those. |
| 4 | Can the runtime support this? | Yes. `core/runtime.build_services` builds every service for the desktop and the headless runtime alike (DEC-0155); a registry is one more service built there. |
| 5 | Navigation and UI registration | `/api/shell` (`core/web_surfaces.shell`) gives the frame (`web/shell.js`) the person's apps, areas, favourites; the Apps page and the destinations read `APPS` and `AREAS`; per-person visibility (`app.visibility`) and child gating (`app_allowed`). |
| 6 | Permissions and services | Services are `AppContext` fields. Permissions are the action contract's approval, `core/browser_safety.py`, UAL tiers, taught-skill gates and child gating; no per-app or per-capability grant (DEC-0156, proposed). |
| 7 | Application data | Stores in `data/` (household) and `data/profiles/<id>/` (personal), listed in `core/personal_data.py`, written through the atomic write, private ones sealed; owned by people, not apps. |
| 8 | Android and desktop | The phone runs its own smaller engine (`android-phone/.../mia_phone.py` builds `core.core_runtime.build_core_context`), links to MIA on the PC once (`core/home_link.py`) to use its bigger model, and two-way syncs stores (`core/sync.py`). The desktop window shows the web screens (DEC-0124). One engine codebase for both. |
| 9 | Reusable | all of the above, plus the module validator, the lab (`core/dev_lab.py`), capability gaps, "Build A Skill", parity, loops, the documentation and Living System tests. |
| 10 | Changes actually necessary | **One manifest per app and a registry that reads it** (new); the registry replacing `APPS` as the source of the app list; capability and permission declarations (DEC-0156); app status from one place; and, later and app by app, moving an app's engine code into its own package. |

**Conflicts found:**
1. **Per-app folders (handoff §4) against the layering rule** (CLAUDE.md: `core/` knows nothing else; modules know
   `core/` only). Today `core/personal_data.py` imports every store, so moving a store into `applications/<id>/`
   would make `core` import an app. Resolution: the registry registers an app's stores, jobs and capabilities from its
   manifest, so `core` stops importing them; only then can an app's code move into its own folder. That's a
   foundation refactor (DEC-0166: Fable), done one app at a time, Greenhouse first.
2. **YAML (handoff §3's example)**: MIA has no YAML dependency; its machine-readable files are JSON (`work/*.json`,
   `docs/schema/*.json`). Resolution: JSON manifests, with a JSON Schema (DEC-0178).
3. **"MIA Forge"** is new; MIA's *model* forge (`core/model_forge.py`, DEC-0106) trains small models. Resolution: MIA
   Forge is the app builder (section E); the model forge keeps its name.
4. **The homestead subproject** (`homestead/`) has its own repository history, database and package. Resolution: it
   stays self-contained (DEC-0145); its MIA-side app (Greenhouse) gets a manifest whose `integrations` names it.

## B. The canonical application manifest

**Where:** `apps/<id>/manifest.json`, one folder per MIA-native app (a new top-level `apps/` folder, which can later
hold the app's own code too). **Format:** JSON, validated against `docs/schema/app_manifest.schema.json`.

| Field | Required | Meaning | Checked against |
|---|---|---|---|
| `manifest_version` | yes | the schema version (1) | the schema |
| `id` | yes | stable forever, snake_case (today's module id) | unique; equals the folder name |
| `name`, `icon`, `tagline`, `description` | yes | as shown | — |
| `version` | yes | the app's own semantic version | bumped when its capabilities or stores change (a test compares) |
| `area` | yes | its destination area | `core/web_areas.AREAS` |
| `entry` | yes | its main surface: `web:intel.html`, or `voice` | the file exists |
| `components.interface` | yes | its surfaces: web pages, the Qt module, glasses cards, phone screens | each exists |
| `components.services` | no | the engine files that implement it (`core/world_intel.py`...) | each exists |
| `components.data` | no | the stores it owns (by `PERSONAL_STORES` / `HOUSEHOLD_STORES` name) | each registered |
| `components.agents` | no | agents it uses (specialists, Game Master) | each exists |
| `components.workflows` | no | built-in skills or routines it ships | each exists |
| `components.integrations` | no | devices, connectors, subprojects it reaches | named in the connector or device lists |
| `capabilities` | yes | the tools and action kinds it exposes (`world_watch.add`, `watch_for`) | each registered; each claimed by exactly one app |
| `permissions` | yes | what its capabilities need (`stores.read:world_intel`, `network:feeds`, `devices.camera`...) | DEC-0156's vocabulary; enforced by grants |
| `dependencies` | no | other apps by id with a version range | each exists and satisfies the range |
| `runtime.devices` | yes | `pc`, `phone`, `glasses`, `pi`: `full`, `view`, `voice` or `none` | parity rows agree |
| `runtime.background` | no | its job and daily-check names | each in `JOBS` / `DAILY_CHECKS` |
| `lifecycle` | no | `health` (a function returning its status), `init`, `shutdown` | each callable |
| `extensions` | no | `x-*` keys for anything not yet in the schema | ignored by the validator, kept |

**Versioning:** `manifest_version` for the schema (old versions read and upgraded in memory); the app's own `version`
for the app. **Compatibility:** a manifest never loses a field within a schema version. **Extension:** `x-*` keys.

**It's an index, not the code** (handoff §3): it names files, stores, tools and jobs; it holds none of their contents.

## C. Runtime services (one registry, no duplicates)

| Service | Built from | Status |
|---|---|---|
| **Application Registry** (`core/app_registry.py`, new) | reads every `apps/*/manifest.json` at start, validates it against the code, and answers: the inventory, an app's capabilities, the app behind a capability, dependents, versions, status | new; replaces `APPS` as the source (phase M3) |
| **Capability registry** | the tool registry + `ACTION_TYPES` + the UAL catalogue, each capability tagged with its app from the manifests | exists; gains the app tag and DEC-0156's fields |
| **Lifecycle manager** | in the registry: activation (today's `app.visibility`), dependency checks at start, health from `lifecycle.health`, the runtime's job status, store load errors, the Fix-It Log | partly exists (separately) |
| **Permission manager** | DEC-0156 grants, checked in the action contract against the manifest's declared permissions | proposed (Fable) |
| **Inter-app communication** | the action contract, the event bus, links, the history (MIA_OS_APPLICATION_INTEROPERABILITY.md) | exists |
| **UI and navigation** | `/api/shell` and the Apps page read the registry; deep links `/web/<page>#tab`, `/desktop-open/<id>` | exists; source moves to the registry |
| **Background execution** | the scheduler, `JOBS`, `DAILY_CHECKS`, homeostasis; each job claimed by an app's manifest | exists |
| **Health monitoring** | the runtime's health, homeostasis, loops, the registry's per-app status | partly exists |

**MIA's understanding of her ecosystem** (handoff §7) is the registry, queried: "what apps do I have", "what can
Greenhouse do", "which apps can monitor energy", "what depends on Home", "which are unhealthy" are registry reads;
"what's duplicated" compares capabilities' summaries and data across apps; "what's missing" is the capability gaps
(`core/capability_gaps.py`); "extend or create" compares a request's needs against existing apps' capabilities. Each
answer says what's implemented versus what she recommends (Living System invariant: recommendations are marked).

## D. The application module standard

**Now (no code moves):** an app's code stays where it is; its manifest names every file. A new app follows today's
pattern (store, actions, tools, screen data, page, script, tests) plus its manifest.

**Later, app by app (phase M6, Fable):** an app's engine code moves into its own package, after the registry
registers stores, jobs and capabilities from manifests so `core` imports no app:

```
apps/greenhouse/
  manifest.json
  store.py            # its data (was core/<x>_manager.py)
  actions.py          # its action kinds
  tools.py            # its voice tools
  screen.py           # its page's data (was core/web_<x>.py)
  jobs.py             # its background work, if any
  web/                # its page and script (served at /web/<page>)
  tests/
```

Rules (exist, restated): business logic inside its app; shared things are runtime services; no app touches another
app's files or stores; cross-app only through capabilities, events, links and the history; each app testable alone
(`tests/run_module.py` today; `pytest apps/<id>` after the move); an app upgradeable without changing unrelated apps.

## E. MIA Forge (the app builder)

Built from what exists, in the lab, never in production:

| Step (handoff §8) | How |
|---|---|
| 1–3 spec, existing apps, new or extend | the registry's queries and capability gaps; "Build A Skill" already decides taught skill vs lab build (DEC-0167) |
| 4–8 design, manifest, components, schemas, permissions | the scaffold (`tools/new_app.py`, proposed) generates the manifest and files in a lab worktree (`core/dev_lab.py`) |
| 9–10 tests, validation, security | the suite, the registry's manifest validation, review by another model (DEC-0174) |
| 11 review | Zac sees the manifest (what it can do, what it may touch) and the diff |
| 12 register and install | merged on Zac's approval; the registry finds it at next start; rollback is the commit or the image |
| Extend an existing app | same path; the manifest's `version` rises; its declared permissions can't widen without approval |
| Right-click hand-off (3D, PCB, blueprints...) | UAL actions on a selection, each a capability; a tool needn't be a full app (handoff §8) |

## F. Migration plan

| Phase | What | Changes behaviour? | Model |
|---|---|---|---|
| M1 | Schema + `core/app_registry.py` + manifests for all 56 apps, generated from today's code; a test that manifests and code agree (every capability, store, job and page claimed exactly once) | no | Opus |
| M2 | Registry queries as tools and a page section: "what apps do I have", "what can X do", "what depends on Y", "which are unhealthy", duplicates, gaps | adds | Opus |
| M3 | `APPS` and `/api/shell` read from the registry; `core/web_surfaces.APPS` becomes a thin view | no (same data) | Opus |
| M4 | Declared permissions enforced (DEC-0156 grants) | yes, gated | **Fable** |
| M5 | Lifecycle: per-app status, dependency checks at start, activation | adds | Opus |
| M6 | Per-app packages, Greenhouse first, registry-driven registration; others as they're touched | no (same behaviour) | **Fable** |
| M7 | MIA Forge: the scaffold, then generation in the lab | adds | Opus, Fable review |
| M8 | The extension host for out-of-process code (DEC-0176) | adds | Fable |

Compatibility: every phase keeps today's ids, routes, store files and tests; the Qt classic view keeps working
(fixes only); the phone engine reads the same registry (it builds the same core). Risks: churn in shared lists during
M1–M3 (kept low by generating manifests from code), the layering inversion in M6 (one app at a time, Fable).

## G. MIA-native apps and the conventional Linux underneath (Zac's DEC-0177 reply)

| Layer | Who manages it | MIA's relation to it |
|---|---|---|
| **The OS image** (Fedora Atomic, bootc): kernel, systemd, drivers, KDE, the cage MIA session | the image build; atomic updates and rollback | MIA ships *in* it as a first-class part, not an installed app |
| **MIA and her native apps** | the MIA Runtime and its Application Registry | her own; managed by manifests, never by Flatpak |
| **Conventional GUI apps** (Firefox, LibreOffice, GIMP, Blender, VS Code) | Flatpak (Flathub) | discovered from Flatpak's metadata; reached through Send to MIA, portals, AT-SPI and, later, declared automation capabilities with grants |
| **Command-line and developer tools** | Toolbx / Distrobox containers (Fedora Atomic's way), or built into the image | MIA can run them only through declared capabilities and the System Manager helper (DEC-0158) |
| **System services** (network, printing, Bluetooth, updates) | systemd and the OS | MIA reads their state; changes go through the System Manager helper with approval |
| **Files** | MIA's code read-only in the image; MIA's data in `MIA_HOME` (`~/.local/share/mia`); the person's ordinary files in `~/Documents` and the rest | MIA reaches ordinary files through her file service with grants, and through the document portal for sandboxed apps |
| **The desktop** | KDE Plasma, selectable at login beside the MIA session (DEC-0157) | the conventional desktop is always one login away (E2) |

No app store; the only marketplaces are the ones Zac shops from (Q-27).
