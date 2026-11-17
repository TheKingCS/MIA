# MIA OS: system service architecture (Prompt 05, deliverable 3)

*Claude (Fable), 2026-11-16. Planning only. Which services make up MIA OS, who owns each responsibility, how they're
supervised, and how configuration is organised. The overall shape is in
[MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md); background app lifecycles are Prompt 03's and aren't
repeated.*

## 1. Every responsibility has one owner

"Essential for boot" means the machine can't reach a login without it. "Plasma needs it" means the conventional
desktop does. Nothing MIA-specific is in either column: that is the design (REQ-ARC-002).

| Responsibility | Owner | Kind | Boot | Plasma | MIA-specific | Privilege | MIA's way in |
|---|---|---|---|---|---|---|---|
| Service supervision, timers, sockets | systemd | Linux | yes | yes | no | root (system), user (user manager) | the service-manager adapter, for her own units only |
| Users, sessions, seats, sleep, lock | systemd-logind | Linux | yes | yes | no | root | session and power adapter (D-Bus, read; lock and suspend as the active user) |
| Authentication | PAM, the login screen | Linux | yes | yes | no | root | none: MIA never handles his login password |
| Authorisation of privileged actions | polkit, with KDE's dialog | Linux | no | yes | no | root | she is a *subject* of it, never an authority |
| Device discovery | udev, the kernel | Linux | yes | yes | no | root | devices adapter (events, read) |
| Network | NetworkManager, systemd-resolved, firewalld | Linux | no | yes | no | root | network adapter (read); changes are system actions |
| Audio, camera streams | PipeWire, WirePlumber | Linux | no | yes | no | user | audio and camera adapters |
| Bluetooth | BlueZ | Linux | no | no | no | root | adapter (D-Bus) |
| Display, input, windows | the compositor | Linux | no | yes | no | user | none directly; her shell is a client |
| Storage, removable media | the kernel, UDisks2 | Linux | yes | yes | no | root | files adapter (granted folders); mounts are system actions |
| Time | systemd-timesyncd or chrony | Linux | no | no | no | root | read only |
| Notifications | the session's notification service (Plasma's, or MIA's shell in her session) | Linux | no | yes | no | user | notifications adapter, after the gate |
| Logging | systemd-journald | Linux | yes | yes | no | root | she writes to it; reads her own units' entries |
| Crash capture | systemd-coredump | Linux | no | no | no | root | read, for her own units |
| Memory pressure handling | systemd-oomd | Linux | no | no | no | root | she sets preferences on her own units |
| Firmware | fwupd | Linux | no | no | no | root | read; updates are system actions |
| OS updates and rollback | bootc | Linux | no | no | no | root | read status; changes through the helper |
| Conventional app lifecycle | Flatpak, the desktop's launcher | Linux | no | yes | no | user (per-user installs) | applications adapter |
| Remote reach | tailscaled (optional; verified in use: `core/phone_server.py`) | Linux, optional | no | no | no | root | read status; she says the command he'd run |
| Local models | the model server (Ollama) | Existing, external | no | no | used by MIA | its own system user, in the `render` and `video` groups | loopback HTTP, behind `core/llm_manager.py` |
| **His records, the schedule, approvals, the API** | **the MIA Runtime** | **Existing MIA** | no | no | yes | his user | it *is* the platform |
| **MIA's screen** | **MIA's shell** | **Modified existing** (the Qt web host) | no | no | yes | his user | the runtime's API |
| **Sending captures from other apps** | **the capture agent** | **New** | no | no | yes | his user | a socket to the runtime |
| **System changes** | **the system helper** | **New** | no | no | yes | root, fixed operations | D-Bus with polkit |
| **Extensions** | one sandbox per extension | **New** (DEC-0176) | no | no | yes | his user, narrowed | the capability contract |

## 2. MIA's own services

For each: purpose, what goes in and out, what it depends on, how it fails and restarts, how it's watched.

### 2.1 The MIA Runtime (`mia-runtime.service`, user) — exists

| | |
|---|---|
| Purpose | The one MIA for this person: stores, schedule, tools, actions, registry, API (`core/runtime.py`, DEC-0155) |
| Inputs | requests from surfaces and devices; the schedule; device and system events through adapters |
| Outputs | his records (the only writer); answers; proposals; her messages through the gate; the health record |
| Depends on | his home directory and the unlock credential. **Wants, never requires:** the network, the model server, audio |
| API | HTTP and SSE (`server/app.py`); a Unix socket for local tools ([IPC document](MIA_OS_IPC_AND_COMMUNICATION_ARCHITECTURE.md)) |
| Privilege | his user; `NoNewPrivileges`; no capabilities; its file reach narrowed (privilege document) |
| Data owned | everything under `MIA_HOME` |
| Start | with his user manager (`default.target`), before any session; with lingering, without a login at all (the Pi) |
| Failure | exit 1: another MIA holds the folder (not restarted). Exit 3: sealed files can't be opened here (not restarted; the recovery key is asked for). Anything else: restarted |
| Restart | `on-failure`, at most three in a row before it stays down and the shell shows the recovery page (REQ-REL-004; today's unit allows ten: to be tightened) |
| Hang | **to add:** `Type=notify` and `WatchdogSec`: the runtime reports ready when its API answers and pings while its scheduler loop turns; a hang becomes a restart |
| Monitoring | `/api/runtime/health`, the unit's state, the journal |
| Stop | SIGTERM: finishes the write in progress, stops jobs, exits within 45 s (as today) |

### 2.2 MIA's shell (`mia-shell.service`, user, part of the graphical session) — the Qt host, modified

Shows `web/` from the runtime, full screen in MIA's session and as a window with a tray item in Plasma. Holds no
records and no logic (REQ-ARC-004). Depends on the compositor; *wants* the runtime: with none answering in 30 s it
shows a local recovery page that needs nothing from the runtime (REQ-UX-022): restart MIA, open the desktop, show
what failed. Restarted on crash; three crashes in a row leave the recovery fallback in place.

### 2.3 The capture agent (`mia-capture.service`, user, part of the graphical session) — new

The front door of the Universal Action Layer on the desktop: owns the hotkey (through the portal in Plasma, directly
in MIA's session), reads the selection or the clipboard *when he presses it*, and sends a capture to the runtime. It
can only send; it executes nothing (UAL plan §6). Separate from the shell so that it works in Plasma with MIA's
window closed, and from the runtime so that code touching other applications holds no access to his records.

### 2.4 The system helper (`mia-system-helper.service`, system, D-Bus activated) — new

Started on demand by the system bus when called, exits when idle. A fixed interface, each method a polkit action.
Runs as root inside a tight unit sandbox. Detail: privilege document §3.

### 2.5 Children the runtime supervises

| Child | Started how | Limits |
|---|---|---|
| Her browser (Chromium under Playwright) | a transient user scope under the runtime | its own memory ceiling; its own profile directory |
| Heavy jobs (indexing, painting, training, long imports) | a transient unit in `mia-background.slice` | low CPU and IO weight; killed first under pressure |
| An extension | a transient unit in `mia-ext.slice`, inside a bubblewrap sandbox | memory and task ceilings; no network unless granted |
| Speech (recognition, voices) | in the runtime today; **split into a child only if measurement shows it starving the API** | |

The model server is *not* a child: it is a system service of its own, so that one model server can serve the
runtime, development tools and, later, other people's runtimes on the same machine.

## 3. Supervision rules

| Class | Examples | Rule |
|---|---|---|
| Critical OS services | systemd, logind, the journal | the distribution's; never touched by MIA |
| MIA platform services | the runtime, the helper | restart on failure with a ceiling; a failure is said once, by something that isn't the failed service |
| Session clients | the shell, the capture agent | bound to the graphical session (`PartOf=graphical-session.target`); end with it |
| Background work | jobs, heavy children | on the platform's scheduler, deferrable ones paced by homeostasis (REQ-FUN-044); never their own timers |
| Per-user services | everything of MIA's except the helper and the model server | one set per person, under their own user manager |
| Optional integrations | Tailscale, the bank, feeds | absent is normal: an adapter that finds nothing reports "not set up", never an error |
| AI inference | the model server | restartable at any time without losing anything; the runtime re-checks what's loaded |

**What keeps running when he switches between MIA's session and Plasma:** everything that isn't a session client.
The runtime, the model server, reminders, the phone's server, jobs, sync. Only the shell and the capture agent stop
and start with the session. This is why the runtime belongs to the user manager and not to the session.

**Timers:** MIA's schedule stays in her own scheduler (`core/scheduler.py`), not in systemd timers: the jobs need
the stores, the gate and homeostasis, and the same code must run on Windows and Android. systemd timers are used
only for things that must work with MIA down (the image build's check for updates is the distribution's own).

**Health, exposed three ways:** the unit state (for systemd and any administrator), the health record at
`/api/runtime/health` (for MIA's surfaces and her self-inspection, Prompt 09), and the journal (for diagnosis).

## 4. System configuration

**No central MIA configuration service.** Linux configuration stays where Linux keeps it; MIA's stays where MIA
keeps it; the image is the declaration of the first.

| Kind | Lives in | Changed by | Rolled back by |
|---|---|---|---|
| The system's shape (packages, units, defaults, policies) | the `Containerfile` and the files it copies, in the repository | a commit, a rebuild | the previous deployment |
| This machine's differences (hostname, networks, users, keys) | `/etc` (kept across updates, merged) | the OS's own tools, or a system action through the helper | the change's own undo, recorded with the action |
| System-wide MIA policy (the helper's allowed operations, polkit rules) | the image (`/usr/share/polkit-1`, `/usr/lib/mia`) | a commit only. **Never at run time, and never by MIA** | the previous deployment |
| MIA's device settings | `MIA_HOME/config` (flat JSON over versioned defaults, as today) | Settings, a voice tool, `setting.set` | undo |
| A person's settings | their profile folder (`core/person_settings.py`) | the same | undo |
| An app's settings | `modules.<id>.*` in MIA's config; a conventional app's own files | that app | that app |
| Device-specific configuration | a drop-in directory per device class in the image (`/usr/lib/mia/devices/`), selected at start | a commit | the previous deployment |

**How MIA inspects and proposes without administrative power:** she reads (bootc status, unit states, `/etc` files
that are world-readable, the journal for her own units). For a change she prepares a system action with fixed
parameters; he sees the exact change; the helper applies it; the result is read back. She never edits a system file
herself, and there is no "run this command" path.

**Kept understandable for a Linux administrator:** no MIA daemon rewrites system files behind the tools' backs.
Anything MIA changed in `/etc` went through a named helper operation and is in the journal with what it was before.
Validation, migration and backup of MIA's own configuration are the existing mechanisms (defaults merged on load;
`config.json` in the nightly backup).

## Reliability (Prompt 14, 2026-11-18)

Each unit's order, restart limits, watchdog and slice: `MIA_OS_SERVICE_STARTUP_AND_DEPENDENCY_MODEL.md` (DEC-0256).
