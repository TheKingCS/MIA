# MIA OS: vision, objectives, principles, scope

*Claude, 2026-11-13, from Zac's "MIA OS Initiative" directive. Planning
only: nothing here is built or approved. Companion documents are listed
in `README.md` in this folder.*

## What MIA is becoming

*The foundational doctrine (prompt 20, proposed as DEC-0173,
[`MIA_OS_LIVING_SYSTEM.md`](MIA_OS_LIVING_SYSTEM.md)): MIA is one Living
System. Her apps, agents, models and operating system are its parts, not the
system itself, and each part joins the shared identity, continuity,
knowledge, initiative, health and feedback rather than keeping its own.*

Today MIA is an application family: a Python engine (`core/`) with one
web front end (`web/`), hosted on the PC by a desktop app (`main.py`),
carried inside an Android app on the phone, and shown on the Meta
Display glasses through a sealed relay. The engine already knows
nothing about the screens (the strict one-way layering in
`docs/ARCHITECTURE.md`), and the same engine already runs headless
(`core_main.py`) and inside Android (Chaquopy). That separation is the
reason an operating environment is reachable without a rewrite.

MIA OS is the next step: **an operating environment built around MIA as
its central presence**, where:

- talking to her is a first-class way to run the machine, alongside
  windows, files and apps that still work the usual way;
- she is aware of what's running, what you're working on and what the
  hardware can do, and can act on it within permissions you grant;
- the same MIA (identity, memory, personality, projects) is present on
  the PC, the phone, the glasses and later the Pi and other devices, each
  presenting her in the way that device allows (DEC-0125);
- she can inspect and explain her own environment (DEC-0056, DEC-0057,
  DEC-0151), and propose improvements to it without ever silently
  changing production (DEC-0058).

**The operating system is the environment. MIA's intelligence is the
central presence, and it stays independent of any one operating
system.** Windows and Android keep running MIA; MIA OS is the
deployment where she is native.

## Objectives

1. **Separate the intelligence from where it runs.** MIA Core (identity,
   memory, reasoning, stores, capabilities) runs the same on Windows,
   Linux, Android and a Pi.
2. **Give MIA a runtime of her own**: a long-running service that owns
   her stores, schedules her work, serves her interfaces and survives a
   closed window. Today that runtime is the desktop app's process.
3. **Boot into MIA on the PC**: a Linux-based image whose session is
   MIA's shell, with conventional desktop apps still available.
4. **Grow her reach in steps**: system awareness first (read-only), then
   permitted actions on apps, processes, files and hardware, always
   through the action contract (propose, approve, execute, record,
   undo; DEC-0009, DEC-0013).
5. **Keep every device in one MIA**: sync, continuity of tasks and
   conversation, and the device fabric (DEC-0128) on a shared model.

## Design principles (Zac's twelve, held as binding)

1. Preserve functioning features; 2. no rewrites without a specific
technical reason; 3. intelligence independent of any OS; 4. logic apart
from presentation; 5. modular, documented interfaces; 6. reusable
services over duplicates; 7. local-first, graceful offline; 8. security
and permissions central; 9. major decisions explicit (DEC entries);
10. automated tests throughout; 11. no broken device integrations;
12. future features without redesigning the foundation.

Three of MIA's own standing rules shape the OS directly and are kept:

- **Facts in code; the model phrases and proposes** (DEC-0004). An OS
  action is decided and checked by code, never by model text alone.
- **No silent actions** (DEC-0009): suggestion, request for
  authorization and execution stay three different things.
- **Everything is documented enough to rebuild** (DEC-0104, DEC-0110):
  the OS image is built from files in the repo, never by hand.

## Scope

**In scope for the initiative:** the runtime extraction, a capability
and permission model that covers system actions, a PC image (Linux base,
MIA session, MIA as a system service), system awareness and management
through a narrow privileged helper, hardware abstraction over what
exists (audio, cameras, serial devices, GPU, network), and keeping
Windows, Android, the glasses and the Pi working throughout.

**Out of scope (now):** writing a kernel or a new Linux distribution
from scratch; replacing Android on phones; unsupervised autonomy over
the system; neural interfaces (an architectural allowance only, as an
input device class in the hardware layer).

## What "done" looks like for the first phase

MIA's runtime runs as its own service on Windows and on Linux, the
desktop window and the phone are clients of it, and a prototype PC image
boots into MIA's shell in a virtual machine, with every existing test
green. The details are in `MIA_OS_INITIAL_IMPLEMENTATION_PLAN.md`.

## A note on who MIA is for

DEC-0119 says MIA is for Zac alone; DEC-0127 (proposed) would make her a
subscription product, and DEC-0050 records that she will eventually be
offered to others. The OS plan is written so it works for one owner now
and does not block a product later (signed images, licensing, multiple
accounts already exist). Which way it goes is Zac's decision
(`MIA_OS_OPEN_QUESTIONS.md`).
