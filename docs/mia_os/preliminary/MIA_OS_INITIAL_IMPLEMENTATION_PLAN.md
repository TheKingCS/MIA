# MIA OS: initial implementation plan (stage 1, for approval)

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Nothing here is started. Stage 1 of
`MIA_MIGRATION_ROADMAP.md` in concrete steps, sized so each is one
commit with tests. Waiting for Zac's architectural approval.*

## Goal

The MIA Runtime: MIA keeps serving the phone, reminding, backing up and
running the Loop with the desktop window closed, on Windows first, with
the same code ready for a systemd user service.

## Steps

1. **Inventory the timers.** List each of the 10 `QTimer`s (and the ~43 daily checks one of them runs) in
   `core/application.py`: the function it calls, its interval, what it
   needs from Qt. A test pins the list so none is lost in the port.
   *No behaviour change.*
2. **`core/scheduler.py`.** A plain-Python scheduler with an injectable
   clock (a thread with a stop event, or a `sched` loop) that runs named
   jobs on intervals. It never overlaps one job, and logs and survives a
   job's exception. Tests with a fake clock.
3. **Move the jobs.** Each timer's body becomes a function in core that
   is free of Qt. `MIAApplication` registers the same jobs on the new
   scheduler instead of QTimers; behaviour is identical with the window
   open. Tests: each job fires; the suite stays green.
4. **`core/runtime.py`.** Grows `core/core_runtime.py`:
   - takes the store lock;
   - starts the scheduler;
   - hosts the API server (moved from `core/phone_server.py`'s
     Qt-thread wiring);
   - checks the model server;
   - serves `/api/health` (uptime, jobs' last runs, model state, lock
     holder).

   Run with `python -m core.runtime`.
5. **The window as a client.** On start, `MIAApplication` looks for a
   running runtime (the lock and health). If there is one, it uses it; if
   not, it starts one in the background. Closing the window leaves the
   runtime running when a setting says so (default off until Zac says,
   question 2).
6. **Autostart.**
   - Windows: a Task Scheduler entry at sign-in, added by
     `setup_home_pc.ps1` behind a flag.
   - Linux: `deploy/mia-runtime.service` (systemd user unit), reusing the
     kiosk installer's pattern.
7. **A tray presence** on Windows to see that MIA is running and stop her.
8. **Docs and knowledge.**
   - `docs/ARCHITECTURE.md` gains the runtime;
   - an atlas regeneration;
   - a knowledge entry;
   - an improvement loop for the scheduler (job misses);
   - `docs/MIA_MAP.md` and the service map list the runtime.

## Tests that must pass at the end

- All ~4,600 existing tests.
- New ones: scheduler with a fake clock; the timer inventory; health
  endpoint; one writer per folder with two runtimes; the window
  attaching to a running runtime.
- Manual on the PC: a week with the window mostly closed; reminders,
  the Loop, backups and the phone all keep working.

## What it does not do

- no Linux image;
- no system actions;
- no new dependencies;
- no change to stores, the web front end, the phone or the glasses;
- nothing removed.

## Size

Eight commits, roughly two or three working sessions, reviewed step by
step.
