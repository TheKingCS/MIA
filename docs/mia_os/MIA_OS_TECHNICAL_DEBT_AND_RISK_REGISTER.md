# MIA OS: technical debt and risk register (Prompt 01 §14)

*Claude, 2026-11-15. Severity and likelihood are rated H, M or L. Type
is one of:*
- *defect: reproduced;*
- *concern: architectural;*
- *compatibility: a question for a future target.*

*"Before OS work" means it must be dealt with before Linux-based MIA OS
development starts. The central `MIA_OS_RISK_REGISTER.md` carries these
forward.*

| ID | Risk | Type | Sev | Like | Evidence | Consequence | Before OS work |
|---|---|---|---|---|---|---|---|
| R-01 | The runtime (scheduler, API host, store owner) lives in the PC's Qt process | concern | H | H | `core/application.py`: 10 QTimers and ~43 daily checks; `core_runtime` has neither | closing the window stops reminders, backups, the Loop and phone serving; no service to boot into | **Yes** |
| R-02 | No key backend for at-rest sealing on Linux or Android | compatibility | H | H | `core/at_rest.py` docstring; no Keystore in `android-phone/` | MIA's data would be plain on Linux; sealed Windows data needs a re-key path | **Yes** |
| R-03 | Two Android apps (`android/`, `android-phone/`), both built | debt | M | H | two CI workflows and two source trees | confusion, double maintenance, overlapping permissions | No (decide, Prompt 02/12) |
| R-04 | Modules and scripts run unsandboxed | concern | H | M | CLAUDE.md; `core/script_runner.py` | an OS can't run third-party code with full privileges | Before third-party apps |
| R-05 | No capability or grant model for system actions | concern | H | H | `core/actions.py`, child gating only | OS-level actions would have no fine-grained authorisation | **Yes**, before any system action |
| R-06 | Test isolation: the at-rest key reset leaks across tests | defect | M | H | `tests/test_id_wallet.py` `use_key(None)`; 4 failures reproduced | Linux CI goes red; real sealing regressions get masked | **Yes** (needed for Linux CI) |
| R-07 | No Linux CI job | debt | H | H | `.github/workflows/` | Linux-only breakage is invisible | **Yes** |
| R-08 | Builds aren't reproducible: no Python lockfile or hashes; fresh-Linux setup needs undocumented system packages | debt | M | H | `requirements.txt` ranges only; this audit's setup steps | an OS image can't be rebuilt exactly | Yes, for image builds |
| R-09 | No versioned schemas for stores (only the Life State) | concern | M | M | `docs/schema/` | migrations between versions and devices are risky | Before data migration |
| R-10 | Duplicated sources of truth (pay and shifts, training days, chores) | debt | M | M | `docs/BODY_AND_RELATIONSHIP_PLAN.md` | an OS-wide user model drifts | No |
| R-11 | Memory retrieval is keyword-only | concern | M | M | `core/user_memory_manager.py` | weak recall at scale; a Prompt 07 decision | No |
| R-12 | Docs drift: stale KNOWN_ISSUES entries; first-pass audit errors; DEC-0119 vs DEC-0050/0127 on audience | debt | M | H | this audit | planning assumptions conflict | Resolve audience before Prompt 04 |
| R-13 | Tests that need the network or a time zone | defect | L | H | weather test, sunrise test | flaky on CI or offline | Before Linux CI |
| R-14 | Event bus is in-process and synchronous | concern | M | M | `core/event_bus.py` | no cross-process events for a runtime and clients | Prompt 05 |
| R-15 | Windows-specific deployment (PowerShell, Task Scheduler, autologon, DPAPI, Edge) | compatibility | M | H | root `*.ps1`, `core/at_rest.py`, `core/browser*.py` | nothing reproducible exists for a Linux image | Prompt 05/14 |
| R-16 | API server thread has no restart supervision (unverified) | concern | M | L | nothing found restarts it | phone loses MIA until the PC restarts | Prompt 14 |
| R-17 | Live-model answer quality not continuously measured | concern | M | M | manual `live_model_check.py` | repetition and dead ends return unnoticed | No |
| R-18 | External dependencies outside MIA's control: Meta toolkit 1.0.1, Plaid, Cloudflare relay, Tailscale | compatibility | M | M | gradle, requirements, `relay/` | features break with vendor changes | No |
| R-19 | A release-signing weakness (details withheld under the public-repo rule) | defect | M | L | reported to Zac on 2026-11-15 | see the private report | Fix promptly |
| R-20 | Hardware paths unverified by automation (GPU, audio, Pi, glasses, nodes) | concern | M | H | `docs/KNOWN_ISSUES.md` | regressions only seen by hand | Prompt 06/15 |
