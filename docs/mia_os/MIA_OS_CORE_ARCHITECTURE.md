# MIA OS: core architecture (Prompt 05, deliverable 1)

*Claude (Fable), 2026-11-16. Planning only: nothing was installed, built, migrated or changed outside `docs/` to
write this, and no proof of concept was run. The recommended construction of MIA OS as a Linux-based operating
environment: its layers, where Linux ends and MIA begins, the components, how they talk, what fails alone, and the
decisions that need Zac. The other fourteen documents of this prompt go deeper into each part and are linked where
they apply. Inputs: Prompts 00 to 04's documents, the repository as it stands, and current documentation (sources in
[MIA_OS_CORE_TECHNOLOGY_EVALUATION.md](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md) §9).*

## 1. What the earlier work fixes, and what it leaves

**Established (not reopened here):**

| Decision | What it fixes for this architecture |
|---|---|
| DEC-0179 (approved) | MIA OS is a personal, AI-native operating environment on a standard Linux image; one node of a distributed personal intelligence |
| DEC-0155 (approved, part built) | One long-running MIA Runtime per person owns the stores, runs the schedule and serves every surface |
| DEC-0156 (approved, built) | Five tiers on every tool and action kind; grants only from what he does |
| DEC-0168 (approved) | The PC (dual boot) and the Pi 5 first; Fedora on the PC, Raspberry Pi OS on the Pi |
| DEC-0175 to 0178 (approved) | Apps are manifests in a registry; MIA ships in the image; Flatpak for conventional apps; extensions sandboxed |
| DEC-0181, DEC-0185 (approved) | Reversibility and reach per action; the stop; the greenhouse adjustable and never stopped |
| DEC-0182 (approved) | The MVP's scope |
| REQ-ARC-001 to 015 | The constraints this document must satisfy (section 9 and the acceptance document) |

**Proposed earlier and still Zac's to approve, which this architecture rests on:** DEC-0154 (the intelligence stays
OS-independent, behind adapters), DEC-0157 (the PC image), DEC-0158 (system changes only through a narrow helper).
This prompt confirms the first, refines the other two (DEC-0189 to DEC-0195), and names one conflict (section 7).

**Reused as it is:** the runtime and its unit, the scheduler and homeostasis, the action contract and grants, the
application registry, the API and live stream, sealing at rest with the Linux key store, the instance lock, the web
front end. **Needing adaptation:** the Qt host (becomes the shell's host), her browser (Chromium instead of Edge),
power and health readings (adapters onto UPower and pressure information), logging (to the journal). **New:** the
image, MIA's session, the system helper, the capture agent, the adapters' Linux halves.

**Unresolved technical questions carried in:** T-02 (IPC), T-06 (events across processes), T-09 (a portal for
conventional apps), T-10 and T-11 (the base and the GPU), T-12 (boot times), T-13 and T-14 (accessibility and the
shell in MIA's session). Each is answered or turned into a proof of concept in
[MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md](MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md).

## 2. The philosophy, as rules for construction

| Principle | What it makes us do |
|---|---|
| Reuse mature Linux infrastructure | Every OS function has an existing owner (systemd, logind, NetworkManager, PipeWire, polkit, KWin, Flatpak). MIA never reimplements one; she talks to it |
| Modular, with explicit boundaries | Each MIA part is a separate process when it can fail, hang or be attacked separately: the shell, the model server, the helper, the capture agent, each extension. They meet only at named interfaces |
| One owner of the truth | The stores have exactly one writer, the runtime (REQ-REL-010). Modularity never means two processes writing his records |
| Minimal privilege | The runtime is his unprivileged user. Root exists only in a helper with a fixed list of operations, and the operating system, not MIA, asks him to confirm them |
| The OS never depends on MIA | No system unit requires a MIA unit. The login screen, Plasma, the network and his files work with every MIA package broken (REQ-ARC-002) |
| MIA never depends on one host | Everything OS-specific sits behind an adapter with one implementation per host; `core/` imports none of it (DEC-0154, REQ-ARC-003) |
| Local-first, provider-independent | The model server is a replaceable local service behind `core/llm_manager.py`; nothing in the OS layer names a provider (REQ-ARC-008) |
| Fault isolation and graceful degradation | Section 8: for each thing that can fail, what keeps working |
| Observability from the system, not from intentions | A system action reports what the system says happened afterwards, read back, never what was asked |
| Independent upgrades where practical | The OS image, MIA's platform inside it, conventional apps (Flatpak), models and his data each update on their own path |

**The layers, and which are foundational or replaceable:**

| # | Layer | Examples | Foundational or replaceable |
|---|---|---|---|
| 1 | Kernel and hardware abstraction | Linux, drivers, firmware | Foundational; never modified |
| 2 | Core OS infrastructure | systemd, the image and its update mechanism, the filesystem, LUKS | Foundational; the distribution's |
| 3 | System services | logind, NetworkManager, PipeWire, BlueZ, polkit, the firewall, the journal | Foundational; each replaceable by the distribution, never by MIA |
| 4 | Graphical and session environment | the login screen, the compositor, Plasma, the portals | Plasma is required (REQ-FUN-001); MIA's session is replaceable without touching it |
| 5 | MIA platform services | the runtime, the system helper, the capture agent, the shell host | The runtime is foundational *to MIA*; nothing below depends on it |
| 6 | MIA intelligence infrastructure | the model server, speech, the embedding model | Replaceable and optional: MIA works without it (REQ-REL-001) |
| 7 | Applications and extensions | MIA-native apps (manifests), extensions (sandboxed), conventional apps (Flatpak) | Each optional |
| 8 | Device integrations | the phone, the glasses, the Pi, the greenhouse, boards | Each optional |
| 9 | External services | search, bank data, outside models, the relay | Each optional and off by default where they send data |

## 3. Where Linux ends and MIA begins

**The line:** Linux is everything that would be there on a stock Fedora KDE install. MIA is a set of user-level
services and one session on top, plus one small privileged helper. Concretely:

| Belongs to Linux (unchanged) | Belongs to MIA |
|---|---|
| kernel, drivers, firmware | the **MIA Runtime** (a user service) |
| boot, the image, updates, rollback | the **application registry and manager** (inside the runtime) |
| users, login, sessions, the lock screen | **intelligence services** the runtime supervises or reaches (model server, speech) |
| network, audio, Bluetooth, power, storage | **MIA's shell** (a session client) and **MIA's session** (an entry at login) |
| Plasma and every conventional application | the **capture agent** (a session client that only sends captures) |
| Flatpak, the portals | the **system helper** (a root service with a fixed interface) |
| the journal, the firewall, SELinux | MIA's **adapters** (the Linux halves of keys, power, audio, notifications, devices, files) |

**The shape: a modular platform with one coordinator.** The prompt offers four shapes; evaluated:

| Shape | Consequence | Verdict |
|---|---|---|
| Independent services, no centre | Several processes would each need the stores; either they share files (two writers: the bug the instance lock exists to prevent) or they talk through a store service, which is a centre by another name | Rejected |
| One centralised runtime doing everything | Simple and what runs today; but a hung model call, a crashing extension or a leaking browser would take reminders and the API with it | Rejected as the end state |
| **A modular platform with a central coordinator** | The runtime is the single owner of his records and the single place a change is approved and recorded. Everything that can fail or be attacked separately runs outside it, as its client or its child, and reaches his records only through it | **Recommended** |
| A combination | The recommended shape *is* the combination: one coordinator, many separate workers | |

**What runs outside the runtime, and why each is separate:**

| Process | Separate because | If it dies |
|---|---|---|
| MIA's shell | it's the part most likely to crash (a browser engine) and the part he's looking at | the session restarts it; reminders, the phone and voice continue |
| Model server | it holds the GPU and gigabytes of memory; it can hang | answers fall back to lookups; the runtime restarts or reports it |
| System helper | it is the only root code | system actions say they're unavailable; nothing else notices |
| Capture agent | it touches other applications (selection, hotkeys) | the hotkey stops; the palette inside MIA still works |
| Her browser | it reads the open web | the browser task stops at its step and says so |
| Each extension | it isn't MIA's code (DEC-0176) | that extension is marked failing in the registry |
| Heavy jobs (indexing, painting, training) | they would starve the API of the interpreter | the job is recorded as failed and backs off |

**The three guarantees the prompt names, and what gives each:**

- *If MIA's primary interface crashes, the operating system remains accessible:* the shell is one client of the
  compositor; the session's fallback and Plasma don't depend on it
  ([MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md](MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md) §6).
- *If the intelligence service crashes, conventional applications continue:* the model server is an ordinary
  service nothing else requires.
- *If cloud services are unavailable, local functions remain:* no unit, session or MVP function needs the network
  (REQ-REL-002).

## 4. The system integration layer

MIA needs one place where the platform meets the host. It has two halves with very different trust.

**The adapters (unprivileged, inside the runtime).** One interface per concern, one implementation per host, as
`core/voice_manager.py` and `core/llm_manager.py` already do. On Linux each talks to the owning service over D-Bus
or its library, as the person:

| Adapter | Reads | Can ask for | Linux backend |
|---|---|---|---|
| Keys | | seal and unseal | systemd credentials (built: `core/key_unlock.py`) |
| Session and power | battery, lid, idle, sleep about to happen | suspend, lock, an inhibitor while a write finishes | logind, UPower |
| Notifications | which are showing, which were dismissed | show one (after the gate) | the desktop notification service |
| Audio and camera | devices present | a stream, a frame | PipeWire |
| Network | connected, metered, which network | nothing (changes are system actions) | NetworkManager |
| Devices | what is attached | open a known board | udev events, `core/device_framework.py` |
| Applications | installed conventional apps and their permissions | launch one; install one (a proposal) | desktop entries, Flatpak, the session's launcher |
| Files | granted folders | read, write inside them | the filesystem, narrowed (privilege document §5) |
| System state | deployment, pending update, failed units, pressure, temperatures | nothing | bootc status, systemd, the kernel's pressure files, hwmon |
| Service manager | the runtime's own and its children's state | restart a child | systemd's user manager |

Reading system state needs no privilege on Linux: nearly all of it is readable by any signed-in user. So **"MIA
describes the system" needs no helper at all.**

**The helper (privileged, outside the runtime).** Only for changes that stock Linux would ask an administrator's
password for. Every system change is an explicit, typed action that travels the same seven steps:

| Step | Where it happens |
|---|---|
| 1 Received | the action contract in the runtime: a proposal in code-written words (`core/actions.py`) |
| 2 Validated | the action type checks its parameters against fixed choices; the helper validates them again (it trusts no caller) |
| 3 Authorised | twice: his approval of the proposal by its tier (always `act_with_approval` for system reach, REQ-AUT-007), then **polkit asking him through the operating system's own dialog** |
| 4 Executed | the helper calls the owning service (bootc, systemd, the firewall); never a shell, never a generated command |
| 5 Verified | the helper reads the state back from that service and returns what it finds |
| 6 Recorded | the helper writes the call to the journal; the runtime records the action with the verified result |
| 7 Reported | to MIA and to him, from the verified result, with how to undo it or that it can't be undone |

The second authorisation is the important one: it is drawn by the desktop, outside MIA's process. Even a fully
compromised runtime can't press it. Detail and the first operation list:
[MIA_OS_SYSTEM_PRIVILEGE_BOUNDARIES.md](MIA_OS_SYSTEM_PRIVILEGE_BOUNDARIES.md).

## 5. Conventional Linux compatibility

The Plasma session is a full desktop, not a maintenance mode (REQ-UX-011): unmodified Plasma, the distribution's
tools, a terminal, Flatpak, containers (`podman`, `toolbox` or `distrobox` for development tools that expect a
mutable system), AppImages, web apps. MIA changes nothing in it except adding herself as an application, a tray
item and, later, file-manager entries. Standard conventions are followed everywhere MIA touches the system: XDG
directories, systemd units, desktop entries, D-Bus names under her own prefix, polkit actions, journald. A Linux
administrator can inspect all of it with the usual tools, and remove MIA by removing her units.

One honest cost of the image-based base: installing a system package with `dnf` isn't how this system works.
Software comes as a Flatpak, in a container, or as a line in the `Containerfile`. That is documented for Zac in the
MVP's guide, and MIA proposes the right route when asked to install something (REQ-FUN-042).

## 6. Alternative architectures compared (§24)

| | A: stock distribution, MIA as services | B: customised distribution | **C: image-based, MIA as services** | D: highly customised environment |
|---|---|---|---|---|
| What it is | install Fedora or Ubuntu, then install MIA | a distribution remix with MIA's packages and defaults | a bootc image built from the repository: Fedora plus MIA's services, session and configuration | own compositor, own shell stack, deep changes |
| Feasibility | highest | high | high, with one unproven step (bootc desktops) | low |
| Development effort | lowest | medium | low to medium | very high |
| Maintenance | drift; manual rebuild after a failure | a remix to maintain | a `Containerfile`; rebuilds are automatic | everything, forever |
| Security | stock | stock | stock, plus a read-only signed system | depends on us |
| Stability, recovery | an update can break mid-way | same | atomic; previous deployment at boot | unknown |
| Compatibility | full | full | full, except installing system packages by hand | reduced |
| Customisation | enough | more than needed | enough: a session, units, configuration | most, not needed |
| Update complexity | low | medium | low | high |
| Developer experience | best on day one | fine | good: change a file, rebuild, test in a VM | poor |
| Sustainability for one person | weak (drift) | medium | **strong** | none |

**Recommended: C, built the way A would be.** Everything MIA adds is an ordinary service, session or configuration
file, so it would also install on a stock system (that is how the Pi runs it, and how it is developed). The image is
only the reproducible, recoverable way of delivering it to the PC. Not D: more control isn't a requirement, and the
session is the one place a little of B is justified.

## 7. A conflict with a proposed decision, stated

DEC-0157 (proposed) describes MIA's session on the PC as **cage with a browser**: a kiosk compositor that shows one
application, full screen. Three things approved or asked for since need more than that:

- workspaces that restore a project's *applications* (WS-3, REQ-FUN-063);
- Zac's handoffs: ordinary apps taking part in MIA's work, dragging content onto MIA, explaining what's on screen
  (prompt 23); glass surfaces over a desktop (prompt 24);
- reaching "a terminal and the system's troubleshooting tools" from inside MIA's session (REQ-UX-023).

cage can't place an ordinary application's window beside MIA's shell, has no lock screen of its own, and brings a
second portal and accessibility stack to maintain next to Plasma's. **This doesn't break the MVP** (DEC-0182: MIA's
session shows MIA's surfaces; Plasma is one choice away), and cage remains right for the Pi's single screen. It does
mean the PC's compositor should be decided by a proof of concept rather than assumed. The alternatives, the
provisional recommendation (KWin for both sessions) and the test are in the session document §3. Nothing approved
is changed by this; DEC-0157 was never approved, and its other parts stand.

## 8. Failure and degraded operation (§33)

| Failure | Impact | Still working | Detected by | Recovery | He is told | Diagnostics needed |
|---|---|---|---|---|---|---|
| Kernel panic, or a kernel that won't boot | the machine | nothing, until reboot | the boot itself | boot the previous deployment | by the boot menu | the previous boot's journal |
| A driver fails (GPU compute) | local models | the desktop, MIA from records, a CPU or Vulkan fallback | the model server's log; the runtime's health check | switch backend; previous deployment if an update caused it | "the GPU isn't available to the model; using…" | model server journal, `amdgpu` messages |
| A system service fails (NetworkManager, PipeWire) | that function | everything else | systemd; the adapter's read fails | systemd restarts it | what stopped working, in his words | that unit's journal |
| The compositor crashes | the session | the runtime, the model server, reminders to the phone | logind ends the session | back to the login screen; the runtime kept running | at next login: what was open | the compositor's coredump |
| MIA's shell crashes | MIA's screen | the compositor, other windows, the runtime, voice | the session's supervisor | restarted; after three in a row the recovery page | the recovery page (REQ-UX-022) | the shell's journal |
| The runtime crashes | all of MIA's functions | the OS, Plasma, conventional apps, the model server | systemd (and its watchdog for a hang) | restarted, at most three in a row (REQ-REL-004); stores are intact (atomic writes) | the shell's recovery page; the phone says the PC isn't answering | the runtime's journal, the last health record |
| An application or extension fails | that app | every other app (REQ-REL-003) | the registry's status (M5) | disable it; the rest is untouched | its status chip, the Fix-It Log | the app's breakages |
| A store file is unreadable | that store | every other store | on load | starts empty, the bad file kept aside (REQ-REL-006) | a notice naming it | the kept file |
| The disk fails or fills | writes | reads; the OS (image and data are separate volumes) | pressure and free-space readings; write errors | homeostasis pauses heavy work; restore from the nightly backup | "the disk is nearly full" before it is | SMART, usage by folder |
| The network is down | sync away from home, lookups, feeds | everything local (REQ-REL-002) | the network adapter | jobs wait and say so once | which things are waiting | connectivity check |
| The model server is down or slow | conversation beyond lookups | Home, search, records, reminders, actions (REQ-REL-001) | health check; a call's timeout | restart it; a smaller model | Talk says so plainly (REQ-UX-021) | its journal, GPU memory |
| Memory or GPU exhaustion | whatever is largest | the desktop and the runtime, protected by their slices | memory pressure; the out-of-memory daemon | unload the model, stop heavy jobs, then the largest app | what was stopped and why | pressure history, per-slice use |

**Single points of failure accepted on purpose:** the runtime for MIA's functions (one writer is worth it; its
restart is seconds and loses nothing), the disk (answered by backup, not by architecture), the compositor for a
session (as on every desktop).

## 9. Requirements, decisions and the handoff

**Requirements:** every requirement of Prompt 04 is mapped to its component, with what's addressed, partial, waiting
on a technology choice or out of scope, in
[MIA_OS_CORE_ARCHITECTURE_ACCEPTANCE_CRITERIA.md](MIA_OS_CORE_ARCHITECTURE_ACCEPTANCE_CRITERIA.md) §3. None of the
21 this prompt owns is left without a component.

**Decisions proposed by this prompt** (full records in `docs/DECISIONS.md`; none is approved by appearing here):

| ID | Question | Recommended | Kind | Confidence |
|---|---|---|---|---|
| DEC-0189 | The Linux foundation and kernel | Fedora Atomic (KDE) as a bootc image from the repository; the distribution's kernel, no out-of-tree modules; Ubuntu 26.04 LTS the fallback; Raspberry Pi OS on the Pi | New recommendation confirming DEC-0157's base; **needs PoC 1 and 2** | High for the direction, medium until the GPU is measured |
| DEC-0190 | The shape of MIA on the OS | A modular platform with one coordinator: the runtime owns the stores; the shell, model server, helper, capture agent, browser, extensions and heavy jobs are separate processes | New recommendation | High |
| DEC-0191 | The graphical and session foundation | Wayland; two entries at login; on the PC one compositor technology (KWin) for both, MIA's shell as its client; cage on the Pi | **Provisional; needs PoC 3**; final in Prompt 10. Amends DEC-0157's cage for the PC | Medium |
| DEC-0192 | Communication | HTTP and server-sent events between surfaces and the runtime (loopback, always authenticated; a Unix socket for local tools); D-Bus to OS services and the helper; cross-process events are "re-read" signals; no broker | New recommendation (answers T-02, T-06) | High |
| DEC-0193 | Storage | Btrfs on LUKS2 on the PC; XDG directories; MIA's code in the image, his data in his home, models in `/var`; the model server's store and caches never backed up | New recommendation | High |
| DEC-0194 | Privilege | The helper holds only what stock Linux would ask an administrator for; each such change is confirmed in the operating system's own dialog; its rules live in the image; MIA's own file reach narrowed by the kernel (Landlock) | Refines DEC-0158; **needs PoC 5 and 6** | High for the model, medium for Landlock |
| DEC-0195 | Resources and observability | systemd slices for MIA, her background work and extensions; kernel pressure as the "busy" signal; the journal as the one log; readiness and watchdog signals from the runtime | New recommendation | High |

**Handoff to Prompt 06 (§37):**

1. **Foundation:** Fedora Atomic with KDE as a bootc image built from the repository (the PC); Raspberry Pi OS (the
   Pi). Fallback: Ubuntu 26.04 LTS.
2. **Kernel and hardware abstraction:** the distribution's kernel, unmodified, no out-of-tree modules; hardware
   reaches MIA only through the owning OS service and an adapter behind a capability.
3. **Core architecture:** image-based Linux underneath, untouched; MIA as user services and one session on top; one
   coordinator (the runtime) with separate processes around it.
4. **Graphical and session:** Wayland; MIA's session by default and Plasma beside it at login; the PC's compositor
   for MIA's session provisional (KWin, against cage) pending PoC 3.
5. **Core services:** all the distribution's; MIA adds the runtime, the shell, the capture agent (user) and one
   helper (system).
6. **Platform integration:** adapters for reading and ordinary use; the helper, with the OS's own confirmation, for
   system changes.
7. **Storage:** Btrfs on LUKS2; XDG layout; image, his data and models on separate subvolumes.
8. **IPC:** HTTP and SSE for surfaces, D-Bus for the OS, no broker.
9. **Resources:** systemd slices, pressure-based easing off, the out-of-memory daemon protecting the desktop and the
   runtime.
10. **Observability:** the journal, the runtime's health record, read-back verification, a diagnostic snapshot.
11. **Privilege:** unprivileged runtime; fixed-operation helper; polkit; the base's SELinux left on.
12. **Build or reuse:** reuse everything Linux has; build only the session glue, the helper, the capture agent and
    the adapters ([MIA_OS_SYSTEM_BUILD_VS_REUSE.md](MIA_OS_SYSTEM_BUILD_VS_REUSE.md)).
13. **Unresolved:** the compositor for MIA's session; bootc's desktop path; whether Landlock fits the runtime; the
    shell's host; Orca in MIA's session.
14. **For Prompt 06 to investigate:** **GPU compute on Fedora 45 for the RX 7900 XTX** (ROCm from Fedora's
    packages against Vulkan, 3B, 14B and 32B models, against the Windows figures: 220, 73 and 14 tokens a second);
    the motherboard's Wi-Fi, Bluetooth and TPM under Linux; suspend and resume with the GPU loaded; the second drive
    for dual boot; the Pi 5 with the AI HAT on Raspberry Pi OS; the minimum hardware profile; which of Zac's
    Windows-only needs have a Linux answer (REQ-CMP-003).

**How this constrains Prompt 06:** the base is chosen conditionally on one measurement, so Prompt 06's first job is
that measurement. Hardware that needs an out-of-tree kernel module is a cost on this architecture and should be
flagged. Anything MIA uses must be reachable through a standard Linux service, because that is the only way in.

Prompt 05 stops here. Prompt 06 waits for Zac's review and go.
