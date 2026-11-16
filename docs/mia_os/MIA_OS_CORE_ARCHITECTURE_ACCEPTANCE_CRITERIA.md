# MIA OS: core architecture acceptance criteria (Prompt 05, deliverable 14)

*Claude (Fable), 2026-11-16. Planning only. How to tell whether the proposed core architecture satisfies the system
vision: the tests it must pass once built, Prompt 05's own completion list, and every requirement of Prompt 04 mapped
to the component that answers it.*

## 1. The architecture is accepted when, on a built image

Each line is a check someone can run. Together they are the claims
[MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md) makes.

| # | Check | Shows |
|---|---|---|
| A1 | Mask every MIA unit and reboot: the machine reaches the login screen and a working Plasma | the OS doesn't depend on MIA (REQ-ARC-002) |
| A2 | Kill MIA's shell repeatedly: the compositor and other windows stay; the shell returns; after three the recovery page shows | the interface fails alone |
| A3 | Kill the runtime: Plasma and conventional apps are unaffected; it restarts; no record is damaged; a fourth crash in a row leaves it down and said | the platform fails alone; one writer, atomic writes |
| A4 | Stop the model server: Home, search, records, reminders and approvals work; Talk says the model is unavailable | intelligence is optional (REQ-REL-001) |
| A5 | Unplug the network at boot and in use: everything local works; nothing waits for it | local-first (REQ-REL-002) |
| A6 | List processes: nothing of MIA's runs as root except the helper while a call is in progress | minimal privilege (REQ-ARC-010) |
| A7 | Ask MIA for a system change: it happens only after her approval card **and** the operating system's dialog; refusing the dialog changes nothing; the journal has the helper's entry | controlled AI-to-system operations |
| A8 | Call every helper method with hostile arguments, from a process that isn't the runtime: refused or harmless | the helper trusts no caller |
| A9 | From an extension's sandbox, try to open a store file and reach the network: both fail | isolation of code that isn't MIA's (REQ-ARC-009) |
| A10 | From a worker narrowed to granted folders, open a file outside them: refused by the kernel | least reach for his files (REQ-FUN-006) |
| A11 | Send an unauthenticated request to the API on loopback from another user and from a sandboxed app: refused | nothing is trusted for being local (REQ-SEC-004) |
| A12 | Apply an update, then roll back at boot: the previous system runs with his data intact | atomic updates (REQ-ARC-011, REQ-REL-009) |
| A13 | Rebuild the image from a clean checkout: the same system | reproducible from the repository |
| A14 | Fill memory with a test load: background work and then the test die; the desktop and the runtime survive | resource boundaries |
| A15 | Suspend and resume with jobs due and a model loaded: nothing blocks sleep; due work runs in order after | power handling |
| A16 | Run the engine's whole suite on the image and on Windows: both pass | one platform, several hosts (REQ-ARC-003) |
| A17 | With the Plasma session only, never starting MIA's: MIA is reachable as a window, and removable | conventional computing stays whole (REQ-UX-011) |
| A18 | Ask "what's the state of this machine?": the answer matches `systemctl`, the update status and the kernel's readings at that moment | she reports the system, not her intentions |

## 2. Prompt 05's completion list (§34)

| Required | Where |
|---|---|
| A Linux foundation selected, or a justified short list | [Linux foundation](MIA_OS_LINUX_FOUNDATION.md) §1: Fedora Atomic as a bootc image; Ubuntu 26.04 LTS and Aurora as alternatives; conditional on PoC 1 and 2 |
| Kernel and hardware abstraction strategy | Linux foundation §2; [hardware abstraction](MIA_OS_HARDWARE_ABSTRACTION_ARCHITECTURE.md) |
| System layers and responsibilities | [Core architecture](MIA_OS_CORE_ARCHITECTURE.md) §2 |
| The Linux-to-MIA boundary | Core architecture §3 |
| Core system services; supervision and dependencies | [System services](MIA_OS_SYSTEM_SERVICE_ARCHITECTURE.md) §1 to §3; diagram 4 |
| The graphical foundation evaluated; the session architecture | [Graphical and session](MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md) |
| Filesystem and storage strategy | [Storage](MIA_OS_STORAGE_AND_FILESYSTEM_ARCHITECTURE.md) |
| IPC and service communication | [IPC](MIA_OS_IPC_AND_COMMUNICATION_ARCHITECTURE.md) |
| Hardware integration boundaries; networking foundations | Hardware abstraction §1 to §5 |
| Resource management | [Resources](MIA_OS_SYSTEM_RESOURCE_MANAGEMENT.md) |
| Observability | [Observability](MIA_OS_SYSTEM_OBSERVABILITY_ARCHITECTURE.md) |
| Privilege boundaries | [Privilege](MIA_OS_SYSTEM_PRIVILEGE_BOUNDARIES.md) |
| Build-versus-reuse decisions explicit | [Build versus reuse](MIA_OS_SYSTEM_BUILD_VS_REUSE.md) |
| Alternative architectures compared | Core architecture §6 |
| The twelve diagrams | [Diagrams](MIA_OS_CORE_ARCHITECTURE_DIAGRAMS.md) |
| Recommendations supported by current evidence | [Technology evaluation](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md), sources read 2026-11-16; claims not read today are marked "to verify" |
| Requirements traceable to components | section 3 below |
| Failure boundaries and degraded operation | Core architecture §8 |
| Unresolved decisions and risks | [Open questions](MIA_OS_CORE_ARCHITECTURE_OPEN_QUESTIONS.md); the central risk register |
| All deliverables created or updated | fifteen documents; the central records updated |
| No implementation or migration performed | nothing outside `docs/` was changed for this prompt; no proof of concept was run |

## 3. Every requirement of Prompt 04, mapped

**195 requirements.** Addressed: 31. Partly: 10. Waiting on a choice: 8. Belonging to a later prompt, with their component named: 146. Not addressed: 0. Of the 21 requirements Prompt 05 owns and the 15 architectural constraints, none is left without a component.

How to read the last column: **Addressed**: this architecture provides it (built already, or fully placed in the
design). **Partly**: placed, with a named piece still to build or measure. **Waits on a choice**: depends on a
proof of concept named in the open questions. **Later prompt**: the requirement belongs to the prompt in brackets;
its component is named so that prompt knows where it lands, and nothing in this architecture stands in its way.
**Not addressed**: none.

**Gaps, stated plainly:**

- The base and the image (REQ-ARC-001, 011; REQ-REL-009; REQ-OPS-001; REQ-SEC-008; REQ-HW-002) rest on two
  unproven steps: GPU compute on Fedora and the bootc desktop path.
- The session (REQ-FUN-001, REQ-UX-023) rests on the compositor's proof of concept.
- Kernel narrowing of file reach (REQ-FUN-006) is unproven for MIA's workers.
- Per-process isolation between MIA's *own* apps doesn't exist and isn't proposed: they are one codebase in one
  runtime, separated by layering and review. Isolation by process starts where the code stops being MIA's
  (extensions). REQ-FUN-041 is "partly" for that reason, and stays so by design.
- The requirements file's `Verify` column was written before this architecture; four checks need the image to
  exist (A1, A12, A13 and the boot timings of REQ-PER-001).

The table is generated from the requirement documents (2026-11-16); the hand-mapped rows are the ones this prompt
owns or directly shapes.

| ID | Owner | Responsible component | Supporting | Interface | Validated by | In this architecture |
|---|---|---|---|---|---|---|
| REQ-ACC-001 | 10, 11 | MIA's shell and the desktop's accessibility stack | compositor | — | I: an automated check plus a manual pass | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-002 | 10 | MIA's shell and the desktop's accessibility stack | compositor | — | T: keyboard walk of each page | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-003 | 10 | MIA's shell and the desktop's accessibility stack | compositor | — | I: Orca pass | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-004 | 10, 11 | MIA's shell and the desktop's accessibility stack | compositor | — | T | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-005 | 10 | MIA's shell and the desktop's accessibility stack | compositor | — | D | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-006 | 10 | MIA's shell and the desktop's accessibility stack | compositor | — | D | Later prompt (10); T-13 in PoC 3 |
| REQ-ACC-007 | 10 | MIA's shell and the desktop's accessibility stack | compositor | — | I | Later prompt (10); T-13 in PoC 3 |
| REQ-AI-001 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-002 | 08, 12 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-003 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-004 | 07 | Runtime (engine) | model server as a separate service | model interface | T: `tests/test_living_system.py` | Later prompt (07) |
| REQ-AI-005 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-006 | 07 | Runtime (engine) | model server as a separate service | model interface | I | Later prompt (07) |
| REQ-AI-007 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-010 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-011 | 07 | Runtime (engine) | model server as a separate service | model interface | M: S-12 offline run | Later prompt (07) |
| REQ-AI-012 | 07, 13 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-013 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-AI-014 | 07 | Runtime (engine) | model server as a separate service | model interface | T | Later prompt (07) |
| REQ-ARC-001 | 05, 06 | The image (Fedora base, distribution kernel) | none of MIA's | Containerfile | inspect the image's build files | Waits on a choice (PoC 1, 2) |
| REQ-ARC-002 | 05, 14 | systemd unit ordering | login screen, Plasma | no system unit requires a MIA unit | mask the runtime, reboot, reach Plasma | Addressed |
| REQ-ARC-003 | 05, 12 | Adapters | runtime | one interface per concern, one backend per host | the suite on Windows and Linux; the phone build | Partly: Linux halves to build |
| REQ-ARC-004 | 05, 14 | MIA Runtime | shell, capture agent as clients | API; user service | a surface's data only from the API | Partly: the window as a client is DEC-0155's remaining step |
| REQ-ARC-005 | 08, 13 | Action contract | system helper for system reach | typed actions; D-Bus with polkit | every action kind registered; helper methods tested | Partly: system and device actions to build |
| REQ-ARC-006 | 08 | Application registry | runtime | manifests | existing tests | Addressed |
| REQ-ARC-007 | 07 | Runtime (engine) | model server only phrases | model interface | review; existing tests | Later prompt (07); nothing here conflicts |
| REQ-ARC-008 | 07 | Model interface | model server as a separate replaceable service | loopback HTTP | existing model-switch test | Addressed |
| REQ-ARC-009 | 13 | Extension sandbox | systemd transient units, bubblewrap | capability contract over a socket | an extension can't open a store file | Partly: boundary placed; profile is Prompt 13's |
| REQ-ARC-010 | 05, 13 | System helper | polkit, the owning OS services | org.mia.System1 | the runtime's process has no root; inspect the operation list | Addressed in design; needs PoC 5 |
| REQ-ARC-011 | 14, 15 | The image | update mechanism, signing | Containerfile; staged deployments | update, then roll back | Waits on a choice (PoC 2) |
| REQ-ARC-012 | 05 | Layering | adapters keep OS code out of the engine | the OS knows only the runtime's unit and the session entry | layering checks | Addressed |
| REQ-ARC-013 | 05, 10 | Flatpak and the image | applications adapter | MIA's registry never installs a conventional app | inspect | Addressed |
| REQ-ARC-014 | 07 | Runtime (stores) | — | existing | existing test | Later prompt (07) |
| REQ-ARC-015 | 15 | Repository | image built from it | — | existing test | Addressed |
| REQ-AUT-001 | 08 | Runtime: action contract and grants | — | — | T: `tests/test_grants.py` | Later prompt (08) |
| REQ-AUT-002 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-003 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-004 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-005 | 13 | Runtime: action contract and grants | — | — | T: `tests/test_grants.py` | Later prompt (08) |
| REQ-AUT-006 | 08 | Runtime: action contract and grants | — | — | T: a test fails on an undeclared kind | Later prompt (08) |
| REQ-AUT-007 | 08, 13 | Action contract tiers | helper and polkit enforce it again at the OS | — | — | Addressed in design; rule itself is 08's |
| REQ-AUT-008 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-009 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-010 | 08 | Runtime (the stop) | run record | — | — | Later prompt (08); nothing here prevents it |
| REQ-AUT-011 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-AUT-012 | 08, 14 | Runtime: action contract and grants | — | — | D | Later prompt (08) |
| REQ-AUT-013 | 08 | Runtime: action contract and grants | — | — | T | Later prompt (08) |
| REQ-CMP-001 | 16 | Adapters (Windows backends kept) | — | — | the Windows suite | Addressed |
| REQ-CMP-002 | 16 | MIA_HOME move and re-seal | storage layout | — | — | Later prompt (16); layout fixed here |
| REQ-CMP-003 | 06, 16 | Plasma session, Flatpak, dual boot | — | — | the list of his Windows-only needs | Later prompt (06, 16) |
| REQ-CMP-004 | 12 | Runtime API unchanged across hosts | — | — | phone and glasses against the Linux PC | Addressed in design |
| REQ-DEV-001 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | T: `tests/test_sync.py` | Later prompt (12) |
| REQ-DEV-002 | 12, 13 | Runtime's server and device links | network foundation | HTTPS, pairing | T | Later prompt (12) |
| REQ-DEV-003 | 12, 13 | Runtime's server and device links | network foundation | HTTPS, pairing | I | Later prompt (12) |
| REQ-DEV-004 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | T | Later prompt (12) |
| REQ-DEV-005 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | T | Later prompt (12) |
| REQ-DEV-006 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | D: S-15 | Later prompt (12) |
| REQ-DEV-007 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | M: S-12 | Later prompt (12) |
| REQ-DEV-008 | 12, 14 | Runtime's server and device links | network foundation | HTTPS, pairing | D | Later prompt (12) |
| REQ-DEV-009 | 12 | Runtime's server and device links | network foundation | HTTPS, pairing | T | Later prompt (12) |
| REQ-DX-001 | 08, 15 | Repository, image build | — | — | T | Later prompt (15) |
| REQ-DX-002 | 15 | Repository, image build | — | — | T | Later prompt (15) |
| REQ-DX-003 | 15 | Repository, image build | — | — | D | Later prompt (15) |
| REQ-FUN-001 | 05, 10 | Login screen with two session entries | compositor, shell, Plasma | wayland-sessions entries | each session used with the other never started | Waits on a choice (PoC 3: the compositor) |
| REQ-FUN-002 | 13, 14 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-003 | 10 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-004 | 10 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-005 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_app_ecosystem.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-006 | 05, 13 | Files adapter | kernel narrowing of workers (Landlock), grants | granted folders only | a worker can't open a path outside a grant | Partly: needs PoC 6 |
| REQ-FUN-007 | 05, 12 | Devices adapter | udev, device framework | device identity read; use through a capability | plug a board: listed, not usable until granted | Partly |
| REQ-FUN-008 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_communication_gate.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-009 | 13 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_accounts_households.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-010 | 14 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-020 | 07, 10 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_parity.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-021 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T: routing corpus | Later prompt; runs on this architecture unchanged |
| REQ-FUN-022 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-023 | 08 | Runtime: the owning app (registry) | stores, action contract | API | T: S-05 | Later prompt; runs on this architecture unchanged |
| REQ-FUN-024 | 09 | Runtime: the owning app (registry) | stores, action contract | API | T: FR-C1 | Later prompt; runs on this architecture unchanged |
| REQ-FUN-025 | 08 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-026 | 07 | Runtime: the owning app (registry) | stores, action contract | API | M: offline round trip | Later prompt; runs on this architecture unchanged |
| REQ-FUN-027 | 07, 13 | Runtime: the owning app (registry) | stores, action contract | API | M: FR-V1 95% on test clips *(provisional)* | Later prompt; runs on this architecture unchanged |
| REQ-FUN-028 | 07 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-029 | 09 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-040 | 08 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_app_registry.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-041 | 05 | Runtime as the only writer | extension sandbox | capabilities, events, links, history | an extension can't read another's store | Partly: per-process enforcement arrives with the sandbox |
| REQ-FUN-042 | 05, 10 | Applications adapter | Flatpak, portals | install as a proposal; permissions shown | install from Flathub on his yes | Addressed in design |
| REQ-FUN-043 | 08, 15 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-044 | 05 | Scheduler and homeostasis | mia-background.slice | existing | existing tests | Addressed |
| REQ-FUN-060 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T: parity | Later prompt; runs on this architecture unchanged |
| REQ-FUN-061 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-062 | 07 | Runtime: the owning app (registry) | stores, action contract | API | M: recall on a labelled set *(provisional)* | Later prompt; runs on this architecture unchanged |
| REQ-FUN-063 | 10 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-064 | 13 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-065 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-080 | 08, 12 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-081 | 12 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-082 | 12 | Runtime: the owning app (registry) | stores, action contract | API | M: S-12 | Later prompt; runs on this architecture unchanged |
| REQ-FUN-083 | 12, 14 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-100 | 12 | Runtime: the owning app (registry) | stores, action contract | API | T: `homestead/` scenarios | Later prompt; runs on this architecture unchanged |
| REQ-FUN-101 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-102 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-103 | 12, 08 | Runtime: the owning app (registry) | stores, action contract | API | T: a refused and a confirmed adjustment against the node's simulator | Later prompt; runs on this architecture unchanged |
| REQ-FUN-120 | 13 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_at_rest.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-121 | 08 | Runtime: the owning app (registry) | stores, action contract | API | T: `tests/test_grants.py` | Later prompt; runs on this architecture unchanged |
| REQ-FUN-122 | 13 | Runtime: the owning app (registry) | stores, action contract | API | I, T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-123 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-140 | 13 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-141 | 10 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-142 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-160 | 10, 11 | Runtime: the owning app (registry) | stores, action contract | API | I: their tiers | Later prompt; runs on this architecture unchanged |
| REQ-FUN-161 | 11 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-180 | 13 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-181 | 12, 13 | Runtime: the owning app (registry) | stores, action contract | API | T, I | Later prompt; runs on this architecture unchanged |
| REQ-FUN-182 | all | Runtime: the owning app (registry) | stores, action contract | API | I | Later prompt; runs on this architecture unchanged |
| REQ-FUN-200 | 09, 15 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-201 | 14 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-202 | 15 | Runtime: the owning app (registry) | stores, action contract | API | D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-203 | 14 | Runtime: the owning app (registry) | stores, action contract | API | T, D | Later prompt; runs on this architecture unchanged |
| REQ-FUN-220 | 08 | Runtime: the owning app (registry) | stores, action contract | API | D: W-2 | Later prompt; runs on this architecture unchanged |
| REQ-FUN-221 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-FUN-222 | 07 | Runtime: the owning app (registry) | stores, action contract | API | T | Later prompt; runs on this architecture unchanged |
| REQ-HW-001 | 06 | The image on the reference PC | model server | — | the MVP list on the PC | Later prompt (06) |
| REQ-HW-002 | 06 | Model server on the chosen base | ROCm or Vulkan | loopback HTTP | PoC 1: tokens a second against Windows | Waits on a choice (PoC 1; handed to 06) |
| REQ-HW-003 | 07 | Model routing by measured hardware | system-state adapter | — | T | Later prompt (06, 07) |
| REQ-HW-004 | 07, 12 | Model routing by measured hardware | system-state adapter | — | T | Later prompt (06, 07) |
| REQ-HW-005 | 06 | Model routing by measured hardware | system-state adapter | — | M: a VM with that profile | Later prompt (06, 07) |
| REQ-HW-006 | 05 | Audio and camera adapters | PipeWire, portals | capabilities | microphone and camera through PipeWire only | Addressed in design |
| REQ-MNT-001 | 15 | Repository and tests | the image built from it | — | T | Later prompt (15) |
| REQ-MNT-002 | 09 | Repository and tests | the image built from it | — | T | Later prompt (15) |
| REQ-MNT-003 | 15 | Repository and tests | the image built from it | — | I | Later prompt (15) |
| REQ-MNT-004 | 17 | Repository and tests | the image built from it | — | I | Later prompt (15) |
| REQ-OPS-001 | 14 | Update mechanism through the helper | polkit | check, stage, apply, roll back | PoC 2 and 5 | Waits on a choice (PoC 2) |
| REQ-OPS-002 | 14 | Recovery path | Plasma, a text console, the previous deployment | — | — | Later prompt (14); the structure allows it |
| REQ-OPS-003 | 14 | Runtime health record | systemd unit states | /api/runtime/health | existing | Addressed |
| REQ-PER-001 | 14 | Boot chain, session start | — | — | systemd's own timing on the image | Later prompt (14); measurable once PoC 2 exists (T-12) |
| REQ-PER-002 | 10, 14 | Plasma session, independent of MIA | — | — | time to Plasma with the runtime masked | Addressed in design |
| REQ-PER-003 | 10 | Runtime and model server | slices | — | M: browser timing, 95th percentile | Later prompt (07, 10) |
| REQ-PER-004 | 07 | Runtime and model server | slices | — | M: a 100k-record synthetic set | Later prompt (07, 10) |
| REQ-PER-005 | 07 | Runtime and model server | slices | — | M: turn timing in the Fix-It Log's `slow` records | Later prompt (07, 10) |
| REQ-PER-006 | 07 | Runtime and model server | slices | — | M | Later prompt (07, 10) |
| REQ-PER-007 | 07 | Runtime and model server | slices | — | T: routing rules | Later prompt (07, 10) |
| REQ-PER-008 | 05 | mia.slice | runtime | soft memory ceiling | the slice's accounting, idle | Partly: to measure |
| REQ-PER-009 | 05 | Homeostasis | kernel pressure through the system-state adapter | — | existing tests; pressure reading to add | Addressed |
| REQ-PER-010 | 07, 12 | Runtime and model server | slices | — | M | Later prompt (07, 10) |
| REQ-PRV-001 | 13 | Runtime (stores, gate) | sealing, storage layout | — | I, T | Later prompt (13) |
| REQ-PRV-002 | 13 | Runtime (stores, gate) | sealing, storage layout | — | D | Later prompt (13) |
| REQ-PRV-003 | 13 | Runtime (stores, gate) | sealing, storage layout | — | I: network audit | Later prompt (13) |
| REQ-PRV-004 | 13 | Runtime (stores, gate) | sealing, storage layout | — | T | Later prompt (13) |
| REQ-PRV-005 | 13 | Runtime (stores, gate) | sealing, storage layout | — | T | Later prompt (13) |
| REQ-REL-001 | 07, 14 | Runtime without the model server | — | — | existing | Addressed |
| REQ-REL-002 | 14 | No unit or session needs the network | — | wants, never requires | boot and use offline | Addressed |
| REQ-REL-003 | 05 | Process and slice separation | scheduler isolation, registry statuses | — | kill each child; the rest run | Addressed |
| REQ-REL-004 | 14 | systemd restart policy and watchdog | runtime readiness signal | sd_notify | kill the runtime four times | Partly: watchdog and the ceiling of three to add |
| REQ-REL-005 | 05 | Runtime (atomic writes) | — | existing | existing | Addressed |
| REQ-REL-006 | 14 | Runtime (store recovery) | — | existing | existing | Later prompt (14) |
| REQ-REL-007 | 14 | Runtime (backup) | storage layout: what is and isn't backed up | — | restore rehearsal | Later prompt (14); layout fixed here |
| REQ-REL-008 | 14 | Runtime start option | shell's recovery page | — | — | Later prompt (14) |
| REQ-REL-009 | 14 | Update mechanism | boot loader | previous deployment | PoC 2 | Waits on a choice (PoC 2) |
| REQ-REL-010 | 05 | Runtime (instance lock) | one user service per person | existing | existing | Addressed |
| REQ-REL-011 | 05 | Homeostasis | adapters: power, network, disk | — | existing | Addressed |
| REQ-REL-012 | 05 | Scheduler | — | existing | existing | Addressed |
| REQ-REL-013 | 14 | Runtime (records of runs) | — | — | — | Later prompt (14, 08) |
| REQ-REL-014 | 14 | Fix-It Log | journal for detail | — | existing | Addressed |
| REQ-SEC-001 | 13, 14 | LUKS2 with TPM2 and a PIN | boot chain | — | boot with and without the PIN | Addressed in design; detail in 13, 14 |
| REQ-SEC-002 | 13 | Sealing with the systemd credential | runtime unit | existing | existing tests; first run on Linux | Addressed |
| REQ-SEC-003 | 13 | Privilege boundaries | helper, sandbox, unprivileged runtime | — | the runtime has no root; helper list inspected | Addressed in design |
| REQ-SEC-004 | 12, 13 | API authentication | loopback default, socket by user id, firewall zone | token on every request | an unauthenticated local request is refused | Addressed in design |
| REQ-SEC-005 | 13 | Runtime and the privilege boundaries | — | — | T: `tests/test_grants.py` sweep | Later prompt (13) |
| REQ-SEC-006 | 08, 13 | Runtime and the privilege boundaries | — | — | T: `tests/test_grants.py` | Later prompt (13) |
| REQ-SEC-007 | 13 | Runtime and the privilege boundaries | — | — | T, I | Later prompt (13) |
| REQ-SEC-008 | 13, 15 | Image signing and verification | update mechanism | — | an unsigned image is refused | Waits on a choice (PoC 2); policy in 13, 15 |
| REQ-SEC-009 | 15 | Runtime and the privilege boundaries | — | — | T | Later prompt (13) |
| REQ-SEC-010 | 13 | Runtime and the privilege boundaries | — | — | T | Later prompt (13) |
| REQ-TRU-001 | 08 | Runtime: history, gate, logs | journal | — | T | Later prompt (08, 09) |
| REQ-TRU-002 | 08 | Runtime: history, gate, logs | journal | — | T | Later prompt (08, 09) |
| REQ-TRU-003 | 08 | Runtime: history, gate, logs | journal | — | T | Later prompt (08, 09) |
| REQ-TRU-004 | 07, 13 | Runtime: history, gate, logs | journal | — | T | Later prompt (08, 09) |
| REQ-TRU-005 | 14 | Verified results from the helper | journal | read-back | — | Partly: system actions; the rest is 14's |
| REQ-TRU-006 | 07, 09 | Runtime: history, gate, logs | journal | — | T: FR-C1, REQ-AI-002 | Later prompt (08, 09) |
| REQ-TRU-007 | 08 | Runtime: history, gate, logs | journal | — | D | Later prompt (08, 09) |
| REQ-UX-001 | 10 | MIA's shell | compositor, runtime | API; the session | T: `tests/test_parity.py` | Later prompt (10) |
| REQ-UX-002 | 10 | MIA's shell | compositor, runtime | API; the session | D | Later prompt (10) |
| REQ-UX-003 | 10 | MIA's shell | compositor, runtime | API; the session | T | Later prompt (10) |
| REQ-UX-004 | 10, 12 | MIA's shell | compositor, runtime | API; the session | D: S-15 | Later prompt (10) |
| REQ-UX-005 | 10 | MIA's shell | compositor, runtime | API; the session | I | Later prompt (10) |
| REQ-UX-006 | 10 | MIA's shell | compositor, runtime | API; the session | T | Later prompt (10) |
| REQ-UX-010 | 10 | MIA's shell | compositor, runtime | API; the session | T | Later prompt (10) |
| REQ-UX-011 | 10 | Unmodified Plasma session | — | — | use Plasma with MIA stopped | Addressed |
| REQ-UX-012 | 11 | MIA's shell | compositor, runtime | API; the session | D | Later prompt (10) |
| REQ-UX-013 | 10, 12 | MIA's shell | compositor, runtime | API; the session | D | Later prompt (10) |
| REQ-UX-020 | 10, 14 | Login screen default entry | — | — | MIA's entry selected by default | Addressed in design |
| REQ-UX-021 | 10 | MIA's shell | compositor, runtime | API; the session | T | Later prompt (10) |
| REQ-UX-022 | 14 | Shell's local recovery page | session supervisor | needs nothing from the runtime | stop the runtime; the page appears in 30 s | Addressed in design |
| REQ-UX-023 | 10 | Compositor-owned recovery menu | Plasma entry | — | reach a terminal with the runtime stopped | Waits on a choice (PoC 3) |
| REQ-UX-024 | 10 | MIA's shell | compositor, runtime | API; the session | D | Later prompt (10) |
