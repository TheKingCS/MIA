# MIA OS: system observability (Prompt 05, deliverable 9)

*Claude (Fable), 2026-11-16. Planning only. How the system's parts report state, health, errors and resource use,
and the interfaces MIA's diagnostics and self-inspection will read. What MIA does with it (self-awareness,
inspection) is Prompt 09's. Decision: DEC-0195 (proposed).*

## 1. The principle

**MIA says what the system reports, never what she intended.** "The update is applied" is true when the update
mechanism says the new deployment is staged, read after the fact; not when she asked for it. Every observation
below is something a Linux service already publishes. No separate monitoring system is built.

## 2. Sources, all existing

| What | Source | Readable by MIA without privilege | Used for |
|---|---|---|---|
| Logs of her own services | the journal (`journalctl --user -u mia-*`) | yes | diagnosis, the recovery page, the Fix-It Log's detail |
| Logs of system services | the journal | only what his user may read (on Fedora, members of the admin group see all) | "why did the network drop" |
| Service states, restarts, failures | systemd over D-Bus | yes | health, app statuses |
| Crashes | systemd-coredump | her own units' | "what crashed, when, how often" |
| OS deployment, pending and previous | the update mechanism's status | yes | "what version am I on, is there an update" |
| Pressure (processor, memory, disk) | the kernel's pressure files | yes | easing off; "why is it slow" |
| Per-service resource use | the control groups' accounting | yes, for her slices | finding the heavy part |
| Hardware: temperatures, fans, battery, disks' health | hwmon, UPower, the drives' SMART data | mostly; SMART through UDisks2 | warnings before failure |
| GPU: memory, load, temperature | the driver's files in `/sys` | yes | model routing, "is the model on the GPU" |
| Network | NetworkManager | yes | connectivity answers |
| Privileged operations | the helper's journal entries; polkit's | yes for her own calls | the audit trail of system changes |
| **MIA's own:** the health record, the scheduler's jobs, the action history, the gate's log, the Fix-It Log, app statuses, the instance lock | the runtime (`/api/runtime/health`, `core/scheduler.py`, `core/actions.py`, `core/failure_log.py`, `core/app_ecosystem.py`) | it is hers | everything about MIA herself |

## 3. What each MIA component reports

| Component | State | Health | Errors | Dependencies | Resources | Recent operations |
|---|---|---|---|---|---|---|
| The runtime | readiness and a status line to systemd (`sd_notify`); the health record | a watchdog ping from the scheduler loop; `/api/runtime/health` (exists) | the journal, structured: which job, which store, which request id | which adapters found their service, which didn't ("not set up" is not an error) | its slice's accounting | the action history; each job's last run and result (exists) |
| The shell | the unit's state | the session supervisor's restart count | the journal | whether the runtime answers | | none (it holds nothing) |
| The capture agent | the unit's state | | the journal | whether the hotkey was granted | | captures sent, by time and kind only |
| The system helper | started on demand | | the journal: every call, the caller, the operation, the parameters, allowed or refused, the verified result | | | the same entries |
| The model server | its own API (what's loaded) and unit state | the runtime's periodic check | its journal | the GPU backend it found | its unit's accounting; VRAM from the driver | |
| An extension | the registry's status (M5) | failures counted | the Fix-It Log, by app | its declared capabilities | its unit's accounting | its calls through the capability contract |

**Logging to the journal:** on Linux the runtime logs to standard output with structured fields and lets the
journal keep, rotate and index it. Today it writes its own log files; those stay the mechanism on Windows and
Android. One sink per host, chosen by an adapter, the same logging calls in the code.

**Never logged, anywhere:** secrets, the contents of his records, what he said in a private turn, a captured
selection's text (REQ-SEC-007). The helper logs parameters because they are fixed choices, never free text.

## 4. Interfaces for diagnostics and self-inspection

| Interface | Gives | Exists |
|---|---|---|
| `/api/runtime/health` | the runtime's own picture: services built, jobs with last result and backoff, model availability, what homeostasis is holding | yes |
| The system-state adapter | a snapshot of the machine: deployment, failed units, pressure, temperatures, disk, GPU, network | new (reads only) |
| App statuses | per app: working, needs attention, failing, and why | yes (M5) |
| The Fix-It Log | failures he could see, grouped | yes |
| **A diagnostic snapshot** | one bundle on request: the health record, the system snapshot, the last hour of her units' journal with secrets and record contents removed, the deployment, hardware summary. For him to read, or to hand to a session helping him | new, small. Never sent anywhere by itself |
| The recovery page | the same essentials with no runtime: unit states and the journal's tail, read by the shell's host | new |

**Performance measurement** uses the same sources: start-up times from systemd's own analysis (answering T-12 once
an image exists), an answer's time from the request log, memory from the slice. No metrics database; a figure worth
keeping over time is written to the store that already keeps such history (`core/progress_history.py`'s pattern)
by a daily check.

**Audit:** MIA's actions are in her action history (who approved, what changed, the result). System changes are
additionally in the journal under the helper's name, written by the helper, which the runtime can't alter. The
kernel's audit subsystem is left as the distribution configures it.

## 5. What this leaves to later prompts

- Prompt 09: how MIA uses these to describe and inspect herself, and to notice regressions.
- Prompt 13: who may read which logs; redaction rules as policy.
- Prompt 14: crash-loop handling, the recovery environment, update health checks.
- Prompt 15: build and test telemetry for the image.
