# MIA OS: the application lifecycle (Prompt 03 §4, §5, §14)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

## 1. The sixteen stages, per kind of app

| Stage | First-party app (in the runtime) | Extension (proposed host) | External app (Flatpak) |
|---|---|---|---|
| 1 Development | the lab's worktree (`core/dev_lab.py`), `tests/run_module.py` | a template + the capability contract | its own project |
| 2 Packaging | part of MIA's version (git) | a signed bundle (DEC-0177) | Flatpak |
| 3 Validation | the test suite: documentation, parity, loops, layering, `core/module_validator.py` | the validator + contract tests + sandbox profile check | Flathub's review |
| 4 Signing | the OS image signature (bootc, cosign); git history | Zac's signing key | Flathub's repository key (GPG) |
| 5 Installation | an image update, or a merged lab branch | the extension host, on Zac's approval | Flatpak, on Zac's approval |
| 6 Registration | from code at start (the manifest, AF-1) | its manifest, checked against granted capabilities | none in MIA; the OS knows it |
| 7 Discovery | Apps, Search, destinations, voice, the UAL | same, marked as an extension | the OS launcher; Send to MIA |
| 8 Launch | open its page, or call its capability | started by the host when first needed | the OS launches it |
| 9 Active | in the runtime | its own process | its own process |
| 10 Background | its jobs on the scheduler | jobs registered through the host | the OS's (systemd user units, portals' background permission) |
| 11 Throttling | homeostasis defers deferrable jobs (`core/homeostasis.py`) | the host's resource limits (cgroups) | the OS |
| 12 Shutdown | with the runtime (SIGTERM, `run_until_stopped`) | the host stops it | the OS |
| 13 Update | the next image or merge; stores migrate on load | a new signed bundle; contract version checked | Flatpak update |
| 14 Rollback | the image's previous deployment (bootc), store undo and backups | the previous bundle kept | Flatpak's previous commit |
| 15 Uninstall | not separately: an app is hidden (`app.visibility`), its code stays | the host removes it | Flatpak |
| 16 Data | **never deleted by removal**: stores belong to the person (AF-8); deleting data is its own approved action | its data stays in its store, offered for export or deletion | the app's own `~/.var/app/...` |

## 2. Who manages what

- **The OS:** core components, Flatpak apps, systemd units, the image and its rollback.
- **The app manager (proposed, inside the runtime):** manifests, status, hiding, the extension host.
- **MIA's intelligence:** only invokes capabilities, explains status, proposes installs and updates for approval. It
  never runs a package manager by generated shell commands (prompt §11).

## 3. Status, from one place (proposed)

| Status | Meaning | From |
|---|---|---|
| installed | its code is present | the manifest |
| available | its required services and stores loaded | `ModuleManager` load results, store load errors (`core/data_recovery.py`) |
| running | a surface is open, or a job ran in its interval | the scheduler's status, the shell's open pages |
| degraded | it works with a part missing (a store that came up empty, a job backing off) | homeostasis, `data_recovery`, `scheduler.status()` |
| failed | its surface or capability errored on its last use | the Fix-It Log (`core/failure_log.py`), the job's `last_error` |
| disabled | hidden by the person | `app.visibility` |
| missing_dependency | a device, a service or a key it needs isn't there | its declared needs vs what's present |

"Open Finance" failing then reads: "Finance is installed, but its bank link failed to load an hour ago (the Plaid
token expired). Want to reconnect it?" built from these, not guessed. Today the pieces exist separately
(`core/capabilities.LIMITS`, the runtime's health, the Fix-It Log); the app manager joins them.

## 4. State after a restart

Stores are the state (written atomically, reloaded at start). Pages are stateless over `/api/*`; the web shell keeps
a page's tab in its address. Long-running work keeps its state in a store (taught skills' practice state, a watch's
last run, a dungeon session). **Gap:** a long multi-step task interrupted mid-way (a browser skill run) restarts from
its beginning; resumable runs belong to the taught-skills engine's phase 2.

## 5. Discovery, navigation and launching (prompt §5)

Exists: the Apps page (by area), Ctrl+K search over every record kind (`core/web_search.py`), the eight destinations
(DEC-0153, `core/web_areas.py`), recently and frequently used (`core/usage_tracker`), favourites and pinned (the
shell), contextual offers through the gate, voice (`ask` examples per app), the UAL on any selection, deep links
(`/web/<page>#tab`, `/desktop-open/<id>`). Missing: **intent-to-capability resolution exposed as discovery** ("who can
check greenhouse humidity?" answered from the registry). The tool router already does it for the model; the
proposal is to show it to the person too ("can you…?" already answers from `core/capabilities.py`).

Presentation models: the web frame (full page), panels and widgets (Dashboard cards), embedded views (the desktop's
web mode), conversational (chat and voice), glasses cards, and later spatial. One app's capabilities feed all of them.

## 6. Background applications (prompt §14)

Declared jobs on the runtime's scheduler (the runtime runs without a window, DEC-0155); per-job failure isolation and
backoff, homeostasis's deferral under load, battery or no network, with a notice (DEC-0173). Behaviour on: sign-out
(the user service keeps running with lingering, `deploy/install_runtime.sh`), sleep (no catching up, `scheduler`),
no network (online jobs wait), crash (systemd restarts the runtime; the job's error is kept), missing hardware (the
job reports `missing_dependency`), no model (every app works without it, AF-11). **Installed vs running vs actually
working** is the status table above: a job that runs but finds nothing for weeks is the loops' business.
