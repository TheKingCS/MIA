# MIA OS: system resource management (Prompt 05, deliverable 8)

*Claude (Fable), 2026-11-16. Planning only. How processor, memory, disk, the GPU, power and heat are shared between
the OS, MIA, local models, applications and background work, so that no one part can take the machine down. Model
routing and the inference scheduler are Prompt 07's. Decision: DEC-0195 (proposed).*

## 1. The mechanism: systemd's control groups, nothing of our own

Linux already accounts for and limits every service through control groups (cgroups v2), and systemd arranges them
in slices. MIA adds three slices of her own inside the person's and sets weights; she builds no resource manager.

```
system.slice
  ├─ (the OS's services)
  └─ ollama.service              the model server: system-wide, its own memory ceiling
user.slice / user-<him>.slice / user@<him>.service
  ├─ session.slice               the compositor, the shell: highest weight, never killed first
  ├─ app.slice                   conventional applications (the desktop puts them here)
  ├─ mia.slice                   the runtime, the capture agent: protected, small
  ├─ mia-background.slice        heavy jobs, her browser: low weight, killed first
  └─ mia-ext.slice               each extension: hard ceilings
```

| Slice | CPU weight | IO weight | Memory | Under memory pressure |
|---|---|---|---|---|
| `session.slice` | high | high | no limit | protected |
| `mia.slice` | normal | normal | a soft ceiling near 1 GB (REQ-PER-008's target), so a leak shows before it hurts | protected (`ManagedOOMPreference=avoid`) |
| `app.slice` | normal | normal | no limit: it's his computer | the largest goes when nothing lesser is left |
| `mia-background.slice` | low | low | a soft and a hard ceiling | **killed first** |
| `mia-ext.slice`, per extension | low | low | a hard ceiling, a task limit | killed at its ceiling |
| `ollama.service` | normal | normal | a soft ceiling leaving the desktop room | restarted; models reload on demand |

The figures are set in unit files in the image and measured on the PC before they are trusted (REQ-PER-008 is
marked provisional for the same reason).

## 2. Who decides what

| Decision | Made by | MIA's part |
|---|---|---|
| Sharing the processor between runnable things | the kernel's scheduler, steered by the weights | none |
| What dies when memory runs out | `systemd-oomd` on pressure, before the kernel's last resort | she marks her own units' preferences |
| Whether background work runs *now* | **MIA's homeostasis** (`core/homeostasis.py`, built): deferrable jobs wait while the machine is busy, on battery, offline or nearly out of disk | all of it, for her own work only |
| Which model is loaded and whether one fits | the model server and MIA's routing (Prompt 07) | chooses by measured memory and VRAM (REQ-HW-003) |
| GPU memory | the model server; nothing in Linux can limit VRAM per process on this hardware | unload before loading; one large model at a time |
| The power profile | the desktop's power-profile service and his choice | reads it; eases off in power-saver |

**A better "busy" signal on Linux.** Homeostasis today reads processor percentage and free memory. Linux publishes
*pressure stall information*: how much time work actually spent waiting for processor, memory or disk. A machine at
90% processor with nothing waiting is fine; one at 40% with memory pressure is not. The system-state adapter should
read pressure on Linux and keep percentages elsewhere; the decision code doesn't change.

**May MIA change resource allocations?** Her own, yes: she starts her heavy work in the low slice and may stop it.
Anyone else's, no: she doesn't renice or freeze his applications. Stopping a runaway *conventional* application is
something she may *propose* ("Blender is using 28 GB; close it?"), which he approves, and which runs as his user
like any window close. A system-wide change (a service's limits) is a system action through the helper.

## 3. By device class

| Class | Models | Background work | Notes |
|---|---|---|---|
| AI-capable workstation (the PC) | 3B and 14B kept warm; a 30B class on request (REQ-PER-006, 007) | runs freely when idle | the desktop always wins contention |
| Laptop | smaller by measured memory; none on battery below a threshold unless asked | deferred on battery | power-saver profile respected |
| Low-power device (the Pi) | the HAT's small models, or the PC's over the home link | minimal, at night | lingering on; no desktop to protect |
| Embedded (greenhouse nodes) | none | none | firmware; outside this document |
| Phone | its own small model (existing) | Android's own rules | not MIA OS |

## 4. Power and heat

| Event | Linux tells MIA through | MIA does |
|---|---|---|
| About to sleep | logind's signal; the runtime holds a short delay lock | finishes the write in progress, pauses the scheduler, releases the lock. Never blocks sleep for work |
| Woke up | logind's signal | re-reads the clock, runs what came due, in order, without a burst; re-checks the model server |
| On battery, battery low | UPower | deferrable work waits (built); below the threshold says so once |
| Power-saver chosen | the power-profile service | as on battery |
| Running hot | the kernel throttles by itself; hwmon readings | heavy jobs wait; she says so once if it lasts |
| Lid closed, screen locked | logind | nothing stops: reminders, the phone and jobs continue |
| Alarms and reminders he set | | **always fire**, whatever the power state allows; a missed one on wake is said at once |

**Suspend with a model loaded in the GPU** is a known place for trouble on any system; it is on Prompt 06's list to
measure, with the fallback of unloading before sleep.

**What is essential, in order, when something must give:** the desktop and his applications; the runtime's API and
alarms; voice; the everyday model; background jobs; indexing and training. Each step down is deferrable before the
one above it.

## 5. Storage as a resource

- Free space is read by homeostasis; heavy writers wait under 5% free (built).
- The model store is the largest consumer and the easiest to trim: MIA lists models by size and last use and
  proposes removals; she never deletes one unasked.
- Caches have ceilings and are safe to delete at any time (they are rebuilt).
- The journal is capped by the distribution's own setting.
- Old OS deployments: the current and the previous are kept; older ones are removed by the update mechanism.
