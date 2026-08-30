# MIA Homestead — MIA Home Sync Plan

Scoping doc for README punch-list item #7: "MIA Home sync — pushing
summarized state to the main dashboard." Written 2026-08-30 after
reading both repos' actual current state (not just their docs) —
`~/Projects/MIA`'s `docs/VISION.md`, `core/finance_manager.py`,
`gui/home_dashboard.py`, and this repo's own
`viewer/export_dashboard_state.py`. Planning only — no code changes
made in either repo by this doc.

## What "MIA Home" actually is (worth stating plainly — the name is overloaded)

Per `MIA/docs/VISION.md`'s "Core/Home split" (resolved 2026-07-15) and
"MIA Home's expanded scope" (2026-07-16) sections: **MIA Home is not a
separate codebase or repo** — it's the existing `~/Projects/MIA` repo's
desktop-class half. "Core" (the Pi5 kiosk device) stays voice-first,
lean, offline-always; "Home" is where the rich visual dashboard
(`gui/home_dashboard.py`, real code, already running) and heavier
reasoning live. Home is meant to eventually run on new hardware
("Project 2," a Ryzen 9800X3D + Radeon 7900 XTX machine, hardware being
built as of 2026-07-15 per VISION.md) but **today it's the same
checkout, same machine as Core** — the migration hasn't happened yet.

**A real naming/hardware-class discrepancy between the two repos'
docs, flagged not resolved**: this repo's own `docs/OFFLINE_ASSISTANT_PLAN.md`
describes Homestead's target hardware as "Pi 5 + AI HAT (same class as
MIA Home)" — but MIA's VISION.md defines Home as the Ryzen/Radeon
desktop, not a Pi5. Those are different hardware classes. Worth the
user's own clarification before assuming which machine Homestead's Pi
is actually supposed to sync *to* — don't guess.

## The good news: a working, generic ingestion mechanism already exists on the MIA side

`MIA/core/finance_manager.py` (done 2026-07-16) is a **watched-folder
JSON snapshot importer that has no idea what "finance" even means** —
by its own docstring, it only knows a generic shape:

```json
{ "source": "some_string", "generated_at": "ISO-8601 string", "...": "anything else, opaque" }
```

It polls a folder (`financial_snapshots/` by default, configurable via
`finance.snapshot_import_folder`), parses anything matching that
minimal shape, stores it keyed by `source`, moves the file to
`imported/` or `failed/`, and a widget (`gui/home_dashboard.py`'s
`_build_real_estate_widget`/`_build_kraken_agent_widget`, a
`WidgetDescriptor`-driven card pattern) reads whatever fields it wants
out of `.data` directly. Two existing, separately-built tools (a Kraken
trading agent, a real-estate portfolio dashboard) already produce this
shape and feed it — Homestead would be a third.

**This means Homestead doesn't need a new sync protocol invented from
scratch — it needs the same shape, and a same-pattern sibling on the
MIA side.** Consistent with this MIA repo's own convention (one
manager per external-content domain — `finance_manager.py`,
`reference_library_manager.py` — not one generic abstraction), the
natural shape of the MIA-side work is a new `core/homestead_manager.py`
(near-identical to `finance_manager.py`, different folder/config key)
plus one new widget card, not a change to finance_manager.py itself.

## What's genuinely NOT built yet (on the MIA side — real work, not assumed)

- No `homestead_snapshots/` watched folder, no `core/homestead_manager.py`.
- No Homestead widget card in `gui/home_dashboard.py`.
- VISION.md's own four-project table lists "Smart Environment" ("The
  Senses" — sensor networks, environmental monitoring, smart home
  integration, explicitly overlapping "Agriculture") as **"Not
  started"** — this sync would be the first real piece of it, not a
  small addition to existing work.
- This is cross-repo work. It needs its own session in the `MIA` repo
  with `MIA/CLAUDE.md`'s layering rules in view (`core/` never imports
  `gui/`; new shared state goes on `AppContext`, not a global) — not
  something to bolt on from inside this repo.

## The real open question neither side has solved yet — not new to Homestead

Both existing snapshot sources (Kraken agent, real estate dashboard)
are, per VISION.md, **"manual/user-downloaded"** — a person drops the
exported file into the watched folder by hand. There is no automated
cross-machine transport yet for *any* Home snapshot source. Homestead
inherits this same unsolved problem, not a harder version of it:
Homestead's Pi and Home's machine are physically separate hardware in
real deployment (a greenhouse vs. wherever Home lives), so "watched
folder" alone doesn't get the file there — something has to move it
across that gap. Options, genuinely undecided, matching VISION.md's own
"deliberately left undecided pending an actual architecture call, not
guessed at here" stance on the identical question for finance:

- A timer-driven `rsync`/`scp` push from Homestead's Pi to Home's
  watched folder (needs SSH key provisioning between two devices —
  real setup, not just code).
- Syncthing or a similar folder-sync tool between the two machines.
- A small HTTP endpoint on Home's side Homestead POSTs a snapshot to
  (more moving parts: Home would need to run a listener, which per
  VISION.md's "reliable" list, Core/Homestead's own philosophy
  deliberately avoids depending on for anything core — but this is
  Home receiving, not Homestead depending on Home being reachable, so
  the same objection doesn't apply the same way. Still a real decision.)
- Manual, same as the other two sources today — genuinely fine as a
  first cut, consistent with how Kraken/real-estate started.

**Recommendation: don't over-build this.** Start manual (matches the
existing two sources' actual current state, not a lesser version of
the plan), automate later once it's clear Home is actually being
checked regularly enough for automation to be worth the setup cost.

## What Homestead should actually export — "summarized," per the punch list's own wording

`viewer/export_dashboard_state.py` (built 2026-08-30, see
`viewer/dashboard.html`) already computes everything needed — but its
full output (per-sensor trend arrays, every open alert, every
maintenance task) is built for Homestead's own on-site ops console, not
a glance-level Home widget. Reuse its data-gathering, don't reuse its
shape wholesale. Proposed export (new script,
`viewer/export_home_snapshot.py`, not yet built):

```json
{
  "source": "mia_homestead",
  "generated_at": "2026-08-30T22:15:09Z",
  "data": {
    "summary": {
      "critical_alert_count": 2,
      "warning_alert_count": 1,
      "yield_this_week_kg": 7.4,
      "yield_prior_week_kg": 3.9,
      "revenue_mtd": 246.0,
      "open_maintenance_critical": 1,
      "open_maintenance_total": 3
    },
    "cells": [
      { "name": "Cell A", "status": "warning", "headline_alert": "greenhouse_power: all sensors stale/invalid (x12)" }
    ],
    "top_alert": { "severity": "critical", "message": "...", "source": "..." }
  }
}
```

`summary` mirrors the shared-shape precedent's own `summary` block
(finance's export has one too — same convention, easy for a future
combined "how's everything going" rollup to read both the same way).
Deliberately excludes sensor trend history, full alert lists, full
inventory — that detail stays one click away in Homestead's own
dashboard (which would need its own URL/link Home could open, itself
an open question — is Home ever on the same network as the greenhouse
Pi to load `dashboard.html` directly? Worth asking rather than
assuming yes).

## Hardware target — resolved (2026-08-30)

User confirmed: MIA Home runs on the Ryzen/Radeon desktop (the compute
backend, for resource access), accessed from multiple client
devices/screens through the build — including Pi5s elsewhere in the
system, not the greenhouse Pi itself. So Homestead's Pi is a producer
only; it never needs to run Home's own UI. This resolves the
discrepancy flagged above in Home's favor (Ryzen/Radeon, not Pi5) —
`docs/OFFLINE_ASSISTANT_PLAN.md`'s "same class as MIA Home" phrasing
for Homestead's own target hardware is a separate, unrelated claim
about Hailo-class NPUs and shouldn't be read as saying Homestead's Pi
and MIA Home are the same machine.

## Sequencing

1. ~~Buildable now, this repo, no MIA changes needed~~ — **done
   (2026-08-30)**: `viewer/export_home_snapshot.py`, producing the
   shape above from the same DB queries `export_dashboard_state.py`
   already proves work (alert de-dup, yield/revenue rollups). Wired
   into `main.py` next to the other two exports
   (`--home-snapshot-out`/`--no-home-snapshot-export`), regenerates
   every control cycle. Verified against the real seeded DB —
   `cells[].status` correctly stays `"ok"` for Cell A rather than
   misattributing the genuinely whole-system `greenhouse_power`/
   `greenhouse_self_preservation` critical alerts to it (only an
   alert source matching the `cell_<slug>` naming convention gets
   attributed to that cell); `top_alert` correctly surfaces the real
   critical condition instead. `core/self_audit.py` and
   `scenarios/scenarios.py` both still clean after wiring this in.
   Writes a local file only (`viewer/home_snapshot.json`, gitignored)
   — does not attempt any transport, per the "start manual" call above.
2. **Needs a session in the `MIA` repo**: `core/homestead_manager.py` +
   `homestead_snapshots/` folder (mirroring `finance_manager.py`
   exactly) + a Homestead widget card in `gui/home_dashboard.py`
   (mirroring `_build_real_estate_widget`). Small, well-precedented,
   but real work in a different codebase with its own layering rules —
   don't do this from inside a Homestead session.
3. **Genuinely undecided, needs the user's call, not a default**: the
   cross-machine transport question above, and the Pi5-vs-Ryzen
   hardware-class discrepancy in what "MIA Home" even runs on for this
   project's purposes.

## Open questions

- ~~Confirm what hardware Homestead is actually meant to sync *to*~~ —
  **resolved 2026-08-30**, see "Hardware target" above: the
  Ryzen/Radeon desktop, accessed via multiple client screens/devices
  (including other Pi5s) rather than the greenhouse Pi running Home's
  UI itself.
- Automated transport now, or manual-first like the other two sources
  — recommendation above is manual-first, but this is the user's call.
- Whether Home ever gets a live link into Homestead's own
  `dashboard.html` (same network) or stays snapshot-only (summarized,
  periodic, never live) — changes whether "top_alert" above is even
  the right level of detail, or too much/too little.
