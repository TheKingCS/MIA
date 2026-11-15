# MIA OS target architecture

*Claude, 2026-11-13. A proposal for Zac's review; nothing here is built or
approved. ADRs: DEC-0154 to DEC-0158 in `docs/DECISIONS.md` (proposed).*

## 1. The layers

```
 ┌──────────────────────────────────────────────────────────────┐
 │ Interfaces: MIA shell (web/), classic Qt view, phone app,    │
 │ glasses Web App, voice, Pi kiosk, CLI                        │  clients only
 ├──────────────────────────────────────────────────────────────┤
 │ Interface framework: /api/state, /api/actions, /api/live,    │
 │ /api/shell, voice sessions; one auth (session tokens)        │
 ├──────────────────────────────────────────────────────────────┤
 │ MIA Core (OS-independent Python):                            │
 │ identity · memory/stores · reasoning · tools · actions/undo │
 │ · life events · communication gate · safety floor            │
 ├───────────────────────┬──────────────────────────────────────┤
 │ Capability framework  │ Sync and continuity                  │
 │ (grants per tool and  │ (sync.py, home link, heavy jobs,     │
 │ action, tiers)        │ device fabric)                       │
 ├───────────────────────┴──────────────────────────────────────┤
 │ MIA Runtime (long-running service): store ownership,         │
 │ scheduler, API host, model supervision, health, logs         │
 ├──────────────────────────────────────────────────────────────┤
 │ Platform adapters: keys (DPAPI / Keystore / TPM2), service   │
 │ manager (Windows service / systemd / Android service),       │
 │ notifications, audio, power, files                           │
 ├──────────────────────────────────────────────────────────────┤
 │ System Manager (Linux only, privileged helper over polkit):  │
 │ processes, apps, updates, network, devices; read first      │
 ├──────────────────────────────────────────────────────────────┤
 │ HAL: audio, cameras, serial/USB, GPU, sensors, input classes │
 ├──────────────────────────────────────────────────────────────┤
 │ Host OS: Windows · Fedora bootc image (MIA OS) · Android ·   │
 │ Raspberry Pi OS                                              │
 └──────────────────────────────────────────────────────────────┘
```

**The rule that keeps it portable:** everything above "Platform adapters"
never imports anything OS-specific, as `core/` already doesn't import Qt.
Each adapter is an interface with one implementation per host, the
pattern `core/voice_manager.py` and `core/llm_manager.py` already use.

## 2. Components

**MIA Core.** Today's `core/`, unchanged in substance. It gains no OS
knowledge, only new tools that call capabilities.

**MIA Runtime.** One process per device (per data folder) that:
- owns the stores and the store lock;
- runs the scheduler (today's 10 Qt timers and ~43 daily checks, ported to plain Python
  jobs with the same intervals and the same functions);
- hosts the API server;
- supervises the model server (starts Ollama, checks it, reports);
- writes a health record (`/api/health`) and its own log.

The Qt window, the web shell, voice and the CLI become clients of it.
On Windows it runs as a per-user background process started at sign-in
(Task Scheduler), on Linux as a systemd **user** service (the pattern
`deploy/mia.service` already uses), on Android inside the existing
foreground service, on the Pi as today's kiosk service. Built by growing
`core/core_runtime.py`, not as a new program.

**Capability framework.** Extends `core/capabilities.py` and the action
contract. Every tool and action declares a capability (`files.read`,
`apps.launch`, `system.update`, ...) and a tier:
- **observe**: read-only, allowed by default;
- **suggest**: proposes only;
- **act-with-approval**: runs after a person approves;
- **act-within-grant**: runs inside a standing grant the person gave,
  logged and undoable where possible;
- **never**: sending email, typing secrets, buying.

Grants are per person, revocable and listed on one screen. The tiers come
from the development platform's (DEC-0069), which already work.

**Interface framework.** The existing API is the boundary. Additions:
- `/api/health`;
- a server-sent events stream beside `/api/live`;
- a local socket for same-machine clients (no network port needed on
  the OS image).

**System Manager (MIA OS only).** A small separate helper process run as
root, with a fixed list of D-Bus methods (list processes, launch an app,
stop a process, update the image, change network, mount a drive). Every
call is authorised by polkit and is reached only through the capability
framework. MIA Core never runs as root.

**HAL.** Wraps what exists:
- audio (PipeWire on Linux, WASAPI on Windows, through the voice
  backends);
- cameras;
- serial and USB (`core/device_framework.py`);
- GPU facts (the model registry);
- input classes: keyboard, voice, gesture, glasses, and a slot for
  neural input.

New hardware is a new driver behind an existing class (DEC-0128's
fabric).

**Sync and continuity.** Unchanged: `core/sync.py` plus the home link.
Conversation continuity across devices is a store like any other.

**Security.** In `MIA_OS_SECURITY_MODEL.md`.

## 3. The PC image (MIA OS proper)

- Base: Fedora Atomic (bootc), so the OS is an image built from a
  `Containerfile` in the repo, updated whole and rolled back whole.
- Sessions at the login screen:
  - **MIA**: `cage` (a Wayland kiosk compositor) running a Chromium
    window on the local MIA shell.
  - **Desktop**: KDE Plasma, with MIA as an app and a tray presence.
- MIA Runtime as a systemd user service; Ollama as a system service on
  ROCm (RX 7900 XTX).
- Apps as Flatpaks; agents and untrusted modules in podman or
  bubblewrap sandboxes.
- Disk: LUKS2 unlocked by TPM2 plus a PIN.
- Windows stays on its own drive (dual boot) until Zac retires it.

## 4. Where each device ends up

| Device | Host | MIA's role |
|---|---|---|
| PC | MIA OS image (and Windows during the move) | native session, full runtime |
| Phone | Android, MIA's app | default assistant and optionally launcher; runtime in the app |
| Glasses | Meta platform via the phone | unchanged |
| Pi | Raspberry Pi OS | kiosk runtime, later the same image approach |
| Greenhouse nodes | firmware | unchanged |

## 5. What does not change

- the action contract;
- the stores and their files;
- the web front end;
- the phone app;
- the relay;
- the homestead subproject;
- every test.
