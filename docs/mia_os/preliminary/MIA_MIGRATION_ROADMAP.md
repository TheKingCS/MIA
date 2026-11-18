# MIA OS migration roadmap

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Seven stages. Each leaves MIA fully working on
Windows, the phone and the glasses; each ends on a gate Zac approves.
Timing depends on Zac's pace; the order is what matters.*

## Stage 1: MIA Runtime (on Windows first)

- **Objective:** MIA runs without the desktop window.
- **Work:**
  - grow `core/core_runtime.py` into the runtime (store lock, the API
    server, the scheduler ported from the 10 Qt timers and their ~43 daily checks, model
    supervision, `/api/health`);
  - the Qt app connects to a running runtime or starts one;
  - a Task Scheduler entry on Windows;
  - a systemd user unit for Linux and the Pi.
- **Dependencies:** none.
- **Deliverables:** `python -m core.runtime`; the scheduler module; the
  unit files; docs.
- **Tests:** each job fires on its interval with a fake clock; the window
  can close while the phone keeps working; one writer per folder still
  enforced; all existing tests green.
- **Risks:** a job behaving differently outside Qt's event loop; two
  processes both writing.
- **Done when:** a week of daily use with the window closed most of the
  time, and nothing missed (reminders, backups, Loop).
- **In parallel:** Zac's D features (Smart Closet, Life Enrichment)
  continue on the current engine.

## Stage 2: Platform adapters

- **Objective:** nothing above the adapters is Windows-only.
- **Work:**
  - a key-backend interface in `core/at_rest.py`, with DPAPI, Keystore,
    systemd-creds (TPM2) and a file-key test backend;
  - adapters for notifications, power and autostart;
  - run the full suite on Linux CI.
- **Dependencies:** stage 1.
- **Deliverables:** adapters; a Linux CI job.
- **Tests:** sealed stores open after moving between backends through an
  explicit re-key; the full suite on Linux.
- **Risks:** a re-key mistake making data unreadable. Mitigation: backup
  first and a tested restore.
- **Done when:** a copy of real data opens on a Linux machine through the
  re-key path.

## Stage 3: Capability framework

- **Objective:** every tool and action has a capability and a tier.
- **Work:**
  - tag the ~378 tools (mostly in code, by domain);
  - a grants store per person;
  - a Grants screen;
  - the contract checks grants;
  - system capabilities exist but are all **observe** or **never**.
- **Dependencies:** none (can run alongside stage 2).
- **Tests:** a test fails on an untagged tool (like the parity and
  loop-coverage tests); grants are revocable; child gating is unchanged.
- **Done when:** the Grants screen lists everything, and nothing changes
  behaviour by default.

## Stage 4: The image prototype (in a VM)

- **Objective:** a bootable MIA OS in a virtual machine.
- **Work:**
  - `os/Containerfile` (Fedora bootc);
  - the MIA session (cage + Chromium on the local shell);
  - the KDE session;
  - the runtime unit;
  - Ollama (CPU in the VM);
  - LUKS2 in the installer;
  - built in CI.
- **Dependencies:** stages 1–2.
- **Tests:** CI builds the image; a boot test reaches `/api/health`; the
  page check runs against it.
- **Risks:** time; VM GPU limits (expected; the GPU comes in stage 5).
- **Done when:** Zac boots the VM, signs in, talks to MIA and opens a
  normal desktop app.

## Stage 5: On the PC (dual boot)

- **Objective:** MIA OS on real hardware beside Windows.
- **Work:**
  - install to a separate drive;
  - Ollama on ROCm with the 7900 XTX;
  - TPM2 unlock;
  - Kokoro, Vosk and Piper on PipeWire;
  - the phone pairs with the Linux runtime (Tailscale);
  - move data via backup and restore.
- **Dependencies:** stage 4.
- **Tests:** the capability checklist on the device; latency and model
  speed against Windows; sync from the phone.
- **Risks:** driver problems; two machines' data diverging (only one runs
  MIA's data at a time: the store lock and a documented hand-over).
- **Done when:** Zac uses MIA OS as his daily PC for two weeks.

## Stage 6: System awareness, then system management

- **Objective:** MIA sees and then, with grants, manages the machine.
- **Work:**
  - the System Manager helper (D-Bus + polkit) with read methods first
    (processes, apps, disk, updates, devices);
  - system context in presence;
  - then actions one at a time (launch an app, stop a process, apply an
    update), each through the contract and a grant.
- **Dependencies:** stages 3 and 5.
- **Tests:** each method has a polkit rule and a test; nothing runs as
  root inside MIA Core; undo where possible, and an honest "can't undo"
  where not.
- **Done when:** Zac approves each action family on its own.

## Stage 7: Every device on one model

- **Objective:** phone, glasses and Pi share the same runtime contract.
- **Work:**
  - the phone becomes the default assistant (role);
  - the Pi on the same runtime;
  - the device fabric (DEC-0128) on the HAL;
  - continuity of conversation and tasks.
- **Dependencies:** stage 1; the rest can start any time.
- **Done when:** a task started on one device continues on another.

## Order of operations

1 → (2 and 3 in parallel) → 4 → 5 → 6, with 7 alongside from stage 2.
Stages 1–3 help MIA on Windows today, so the work pays off even if the
OS image never ships.
