# MIA OS: system philosophy (Prompt 04, Part I)

*Claude (Opus), 2026-11-15. Planning only: nothing here is built or changes MIA. The authoritative statement of what MIA
OS is; the requirements that follow from it are in [MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md).
It holds to the five foundations Zac set (DEC-0159: Linux, MIA-first with a conventional desktop always there, hybrid
local-first intelligence, approval for consequential actions, a no-AI path), the Living System doctrine (DEC-0173),
capability-first apps (DEC-0175 to DEC-0178) and grants (DEC-0156). Recommendations are marked; nothing here settles
a decision Zac hasn't made.*

## 1. What MIA OS is

**Short definition.** MIA OS is Zac's personal computing environment: a standard Linux system whose default session is
MIA, a long-running personal intelligence that knows his records, works his apps and devices through checked
capabilities, and asks before anything consequential, while an ordinary desktop stays one click away and works without
her.

**Architectural definition.** Three layers with one-way dependencies:

1. **The operating system** (Linux, built as a signed image: DEC-0157, proposed): boot, drivers, users, the
   filesystem, networking, processes, the display server, conventional apps (Flatpak), updates and rollback, recovery.
   It knows nothing about MIA beyond starting her service and her session.
2. **The MIA platform** (the MIA Runtime, `core/runtime.py`, DEC-0155): one long-running service per person that owns
   their stores and history, the capability registry (tools and action kinds, each tiered: `core/grants.py`), the
   action contract (propose, approve, execute, record, undo: `core/actions.py`), the scheduler, the communication gate,
   the app registry (`core/app_registry.py`), sync and the model backends. It runs the same on Windows, Linux, Android
   (Chaquopy) and a Pi (DEC-0154, proposed).
3. **MIA's apps and surfaces** (`apps/<id>/manifest.json`): screens (the web front end, `web/`), voice, glasses cards,
   each a view over platform capabilities; plus conventional Linux apps reached through the OS.

The intelligence (the model) sits beside layer 2, not in it: it proposes and phrases; code decides, checks and records
(DEC-0004). MIA is not the model; models are replaceable parts (doctrine, DEC-0173).

**Which of the prompt's descriptions fits** (§1):

| Description | Fits? | Why |
|---|---|---|
| A traditional operating system | no | MIA OS writes no kernel, drivers or scheduler; it uses Linux (E1). |
| A Linux distribution | partly | It ships as a Linux image, but the image is the vehicle, not the identity. One person's image, not a distribution for others (DEC-0119, DEC-0177: no app store). |
| An AI assistant running on an operating system | no | That's MIA on Windows today. MIA OS gives her the session, the system's capabilities and the boot. |
| An AI-powered desktop environment | partly | Her session is the default desktop, but KDE is there too and works without her (E2). |
| An AI-native operating environment | **yes, with the rest** | The environment is organised around her: boot into her, her capabilities, her records. |
| A distributed personal AI ecosystem | **yes** | One MIA on the PC, phone, glasses and later the Pi and truck, each device showing her as it can (DEC-0125). |
| An intelligent personal computing platform | **yes** | Apps are capabilities on one platform (DEC-0175); she can build more (Forge, prompt 22). |

**Recommended identity (DEC-0179, proposed):** *a personal, AI-native operating environment on a standard Linux image,
which is one node of a distributed personal intelligence.* All three parts matter: personal (one owner, his data, his
rules), AI-native environment (not a new kernel or distribution), one node (the PC is the strongest home of a MIA that
also lives on other devices).

## 2. The eight questions (§1)

1. **What makes it different from a conventional OS?** The unit of work is a capability on Zac's own records, not an
   app window. Every change MIA makes goes through one contract that previews it, asks when it should, records it and
   can undo it. The environment remembers his projects, goals and history across apps and devices, and can explain what
   it did and why from records, not from a model's guess.
2. **What belongs to the operating system?** Booting, hardware, users and login, storage and its encryption, networking,
   processes and their isolation, the display and input, conventional apps, updates with rollback, recovery, and the
   no-AI path. Privileged system changes only through a narrow helper (DEC-0158, proposed).
3. **What belongs to MIA's intelligence layer?** Understanding a request, choosing capabilities, planning steps,
   phrasing answers, noticing what matters (through the gate), and proposing. It decides nothing that code can check
   and never reports success without a record (§9 of the requirements).
4. **What belongs to applications?** A domain's screens, its stores, its jobs and its capabilities, declared in its
   manifest. Apps don't reach into each other; they share through capabilities, events, links and the history
   (DEC-0175).
5. **How do they cooperate?** The OS starts the runtime and the session; the runtime serves every surface and owns the
   state; apps register capabilities; the intelligence calls capabilities through the same contract a button uses; the
   person approves what needs approving. One direction of dependency at every step (CLAUDE.md's layering).
6. **What should he experience that a conventional desktop can't give?** Asking for an outcome across apps ("get the
   greenhouse ready for frost") and seeing one plan; finding anything by meaning across every record; MIA noticing
   what's due or wrong and saying so at a pace he's shown he wants; continuity from PC to phone to glasses; every change
   she made listed and reversible; the same MIA when offline.
7. **What must stay possible conventionally?** Logging in, opening files and apps, using a terminal, changing settings,
   installing software, recovering the machine, all without MIA running and without a model (E2, E5).
8. **What should MIA OS never become?** A new kernel or distribution for others; an app store or marketplace (DEC-0177,
   Q-27); a surveillance system recording everything he does; a system where the model acts unchecked or a page can
   instruct it; one that only works online or with one AI provider; a single monolithic privileged process; something
   that hides what it did.

## 3. The principles, as an engineering decision framework (§2)

Each principle: what it means, what it requires, how it's broken, how compliance is checked. The requirements cite
them by number (P1 to P18).

| # | Principle | Means | Requires (behaviour and architecture) | Violated when | Checked by |
|---|---|---|---|---|---|
| P1 | Intelligence integrated | Her capabilities are the system's, reachable from any surface | One capability registry; every action has a tool and a screen control (DEC-0125) | A feature exists only as a screen or only by voice | `core/parity.py`, `tests/test_parity.py` |
| P2 | User-centred | Built for Zac's actual days, not a demo | Features trace to his words or records | A feature nobody asked for or uses | Usage loops (`core/loops.py`), traceability |
| P3 | Local-first | Works on his hardware without the internet | Local stores, local models, local search | A core function needs the cloud | The offline acceptance runs (REQ-REL) |
| P4 | Persistent context | She remembers what matters, across apps and devices | Stores, history, links, sync | He has to repeat himself | Scenario tests (USER_SCENARIOS) |
| P5 | Ownership and control | His data, his rules, his machine | Data in his folder, exportable, deletable | Data he can't see, export or delete | Store inventory, export test |
| P6 | Adaptable, extensible | New capabilities without redesign | Manifests, the registry, Forge | A new app needs core edits | `tests/test_app_registry.py` |
| P7 | Privacy by design | Collect the least, keep it sealed | Sealed at rest (DEC-0126); no recording by default | Anything recorded "just in case" | Store audit, sealing tests |
| P8 | Security by design | Least privilege everywhere | Tiers and grants (DEC-0156); out-of-process extensions (DEC-0176); privileged helper | A capability runs without a tier; a page steers an action | `tests/test_grants.py`, outside-text tests |
| P9 | Transparent autonomy | He can see what she did and why | The history, the gate's log, `/api/why` | An action with no record | The action-history audit (REQ-TRU) |
| P10 | Human authority | Consequential acts need his press | `act_with_approval` tier; no grant covers it | A payment or send without his yes | `tests/test_grants.py` |
| P11 | Device independence | One MIA on every device | One engine (DEC-0154); per-device presentation only | A capability exists on one device only, undecided | `work/parity.json` |
| P12 | Interoperability | Apps share through the platform | Capabilities, events, links (DEC-0175) | One app importing another | Layering checks |
| P13 | Reliable, recoverable | One failure doesn't take the rest | Per-job isolation, backups, rollback, recovery | A broken store stops MIA | Failure-injection tests (REQ-REL) |
| P14 | Accessible | Usable with different abilities | Conventional accessibility stays; her own surfaces meet WCAG 2.2 AA | A function reachable only by sight, or only by voice | Accessibility audit (REQ-ACC) |
| P15 | Maintainable | One person and his agents can keep it going for years | Documentation (DEC-0104), tests, reproducible image | Undocumented code; a hand-built machine | `tests/test_documentation.py` |
| P16 | Provider independence | No single AI vendor is load-bearing | Backend interface; local default | A function that only one provider can do, undeclared | Backend-swap test (`tests/test_living_system.py`) |
| P17 | Graceful degradation | Less capability, never a dead end | Each failure has a stated fallback | A blank screen or a silent failure | RELIABILITY doc's table |
| P18 | Respect for attention | She speaks when it's worth it | The gate's learned pace (DEC-0171) | Nagging; repeats | The gate's log and loops |

**When principles conflict, this order decides (recommended, DEC-0180):**

1. **Human authority and safety** (P10, the safety floor) over everything: no convenience justifies an unapproved
   consequential act.
2. **Security and privacy** (P7, P8) over personalisation and convenience. Personalisation uses what he has given or
   what's already in his records; nothing is collected only to personalise. *Example the prompt asked for:* the
   personalisation that needs history reads the stores he already keeps; anything new (a clipboard history, screen
   context) is opt-in per kind, kept for a stated time, and visible.
3. **Reliability and the no-AI path** (P13, P17) over intelligence: a feature that makes the system less recoverable
   waits.
4. **Local-first** (P3) over capability, unless he chooses the cloud for that kind of task (and is shown what leaves).
5. **Respect for attention** (P18) over proactivity.
6. **Maintainability** (P15) over novelty.

## 4. The relationship between Zac and MIA (§3)

MIA is one presence with several roles. The role doesn't change her authority; the tier of what she's about to do does.

| Role | What she does | Authority |
|---|---|---|
| Assistant | answers, looks things up, explains | observe |
| Collaborator | plans with him, drafts, compares options, disagrees with reasons | suggest |
| Personal agent | runs what he's taught her (learned skills) and approved (workflows) | within his grants |
| OS interface | opens apps, finds files, changes settings he asks for | as asked; system changes through the helper |
| Task coordinator | turns a goal into steps across apps; shows the plan | suggest; each step by its tier |
| Information manager | keeps records, links them, finds them | observe; changes to his records within grants |
| Automation system | jobs, daily checks, workflows | within grants; homeostasis paces them |
| Personal knowledge system | memories, notes, the history, links | observe; memories only kept on his "keep it" |
| Development assistant | the lab: proposes code in a worktree, tests it, asks for the merge (DEC-0058) | suggest; merge on his approval |
| Device controller | reads sensors; adjusts devices, the greenhouse's controllers included (DEC-0185), with each device's own safety limits holding | per device; commands are consequential unless he granted them |

**When she acts, asks, refuses or defers** (the full model is
[MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md](MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md)):

- **Acts on her own:** reads, explains, prepares drafts; changes to his own records that are undoable and inside a
  grant he gave (a learned skill, a published workflow).
- **Asks:** any change outside a grant; anything that pays, buys, sends, publishes, deletes, shares or changes an
  account; anything irreversible; any device command; any system change.
- **Refuses:** what's tiered `never` for her; what a page, a mail or a feed asked for in the same turn (outside text
  never steers a change); what would break the safety floor.
- **Defers:** deferrable work while the machine is busy, offline or low on power (homeostasis, DEC-0173); messages
  past the pace he's shown he wants (the gate).

He stays in control of the system, the data, the devices and the permissions: every grant is listed and can be taken
back (Apps › Manage apps), every change she made is in the history, and the conventional desktop works without her.
