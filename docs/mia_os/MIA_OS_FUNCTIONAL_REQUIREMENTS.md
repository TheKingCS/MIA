# MIA OS: functional requirements (Prompt 04, deliverable 4, with §7 to §12)

> **Prompt 17 (2026-11-18):** REQ-FUN-004's "cage session" reads as MIA's session under KWin, cage the fallback (DEC-0191, DEC-0227).

*Claude (Opus), 2026-11-15. Planning only. Row format and fields: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md)
§1. Status is as of 2026-11-15, with evidence. The application framework is Prompt 03's and isn't redesigned here
(section C only states what the OS must provide it).*

**Where each area's requirements belong** (§7's last instruction, and §25): **OS** = the Linux image and its services;
**Platform** = the MIA Runtime's shared services; **App** = a MIA-native app (its manifest); **AI** = what the
intelligence does through capabilities. Most of Zac's features are apps on the platform; very little is OS.

## A. Core operating environment

*Purpose:* a working Linux desktop that boots into MIA and stays usable without her. *Scenarios:* S-01, S-02, S-13,
S-17. *Inputs/outputs:* logins, settings, files, devices in; sessions, windows, notifications out. *Depends on:* the
image (05, 14). *Security:* login, disk encryption, the helper. *Failure:* MIA's session fails, KDE and recovery stay.
*Devices:* PC (the phone, glasses and Pi keep their own OS).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-001 | The PC shall offer at least two sessions at login, MIA's and a conventional desktop (KDE Plasma), each usable without the other running. | Must | MVP | PC | Planned | D: log into each with the other's services stopped | E2, DEC-0157 → 05, 10 |
| REQ-FUN-002 | Authentication shall use the OS's login (PAM), with the disk unlocked before it; MIA's own sign-in stays a person selector inside her session, never a second password for the machine. | Must | MVP | PC | Planned | D | E5, P8 → 13, 14 |
| REQ-FUN-003 | Settings shall be split: system settings (display, network, users, updates) in the OS's settings app and reachable from MIA's; MIA's settings in her Settings app; each reachable by voice and screen. | Must | MVP | PC | Exists (FW-11: System Settings' pages from MIA's Settings and by voice, `open_system_setting`) | D | P1 → 10 |
| REQ-FUN-004 | Window and workspace management shall be the compositor's (KDE in Plasma; one full-screen surface in MIA's cage session); MIA's surfaces shall open conventional apps in the Plasma session on request. | Must | R1 | PC | Planned | D | DEC-0157 → 10 |
| REQ-FUN-005 | MIA shall list, open and hide her own apps from the registry, and show each app's status with why. | Must | MVP | All | Exists (M3, M5: `core/app_ecosystem.py`) | T: `tests/test_app_ecosystem.py` | DEC-0178 → 10 |
| REQ-FUN-006 | Files shall be the OS's ordinary filesystem; MIA reads and writes only through her file service, inside folders the person granted, and never moves or deletes a file without the person's yes. | Must | R1 | PC | Partial: Files app and myfile store; no file-service grants yet | T: a delete waits for approval | P5, P8, DEC-0156 → 05, 13 |
| REQ-FUN-007 | Attached devices (USB storage, serial boards, cameras, audio) shall be detected and listed with what they are; MIA may read their identity, and use one only through a capability. | Should | R1 | PC, Pi | Partial: `core/device_framework.py` (USB, serial) | T | P1 → 05, 12 |
| REQ-FUN-008 | All of MIA's unprompted messages shall go through the communication gate; OS and conventional-app notifications stay the desktop's own. | Must | MVP | All | Exists (`core/communication_gate.py`) | T: `tests/test_communication_gate.py` | DEC-0171, P18 → 10 |
| REQ-FUN-009 | Each person shall have their own profile, data folder and settings; another profile's personal stores are never readable from a session. | Must | MVP | All | Exists (`core/profile_manager.py`, `core/personal_data.py`) | T: `tests/test_accounts_households.py` | MU-1, P5 → 13 |
| REQ-FUN-010 | Diagnostics shall show the runtime's health, each job's record, each app's status, the Fix-It Log, disk, memory and model status, without the model. | Must | MVP | All | Partial: Diagnostics, `/api/runtime/health`, statuses; no single page with all | D | P9, P13 → 14 |

## B. MIA intelligence

*Purpose:* understand, plan and act through capabilities. *Scenarios:* S-03, S-05, S-11, S-14. *Inputs:* speech,
text, selection, camera. *Outputs:* answers, proposals, results with their records. *Depends on:* model backends,
the capability registry, context assembly. *Security:* outside text never steers a change; tiers. *Failure:* the
model is unavailable: screens and lookups still answer. *Devices:* all.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-020 | MIA shall hold a conversation by text on every device and by voice where the device has a microphone, with the same capabilities either way. | Must | MVP | All | Exists (`core/assistant_turn.py`, `core/voice_manager.py`, parity) | T: `tests/test_parity.py` | DEC-0125 → 07, 10 |
| REQ-FUN-021 | A request shall be matched to capabilities by code first (trigger phrases, domain words, the person's own record names), and only the matching tools are offered to the model. | Must | MVP | All | Exists (`AssistantActionRegistry.matching_actions`) | T: routing corpus | P1 → 07 |
| REQ-FUN-022 | A question a single read-only lookup answers shall be answered by that lookup without the model. | Should | MVP | All | Exists (`direct_lookup`) | T | DEC-0004 → 07 |
| REQ-FUN-023 | A multi-step request shall become a visible plan of capability calls, each step approved by its tier, before anything changes. | Must | R1 | All | Partial: the tool loop chains lookups; changes aren't planned as one approvable plan | T: S-05 | FR-X1 → 08 |
| REQ-FUN-024 | MIA shall describe her own capabilities only from the registry and the capability status, never from the model's memory. | Must | MVP | All | Exists (`core/capabilities.py`, `core/self_knowledge.py`, `list_my_apps`) | T: FR-C1 | DEC-0057 → 09 |
| REQ-FUN-025 | Every tool call shall be recorded with its result; a change's success is reported only from the executed action's record. | Must | MVP | All | Exists for actions (proposal status); lookups logged | T | P9 → 08 |
| REQ-FUN-026 | Speech in and out shall work offline on the PC and the phone (local STT and TTS), with the voice chosen by the person. | Must | R1 | PC, Ph | Partial: Vosk and Piper backends; the PC desktop voice path is lightly used | M: offline round trip | E3 → 07 |
| REQ-FUN-027 | MIA shall identify who is speaking from voice samples each person gave, and treat an unidentified voice as a guest. | Should | Mature | PC, Ph, Gl | New (MU-2, DEC-0163) | M: FR-V1 95% on test clips *(provisional)* | DEC-0163 → 07, 13 |
| REQ-FUN-028 | MIA shall look at an image or the camera on request and say what she sees, with the image never leaving the device unless the person chose a cloud model. | Should | R1 | PC, Ph, Gl | Exists (Look, `core/sight.py`, qwen2.5vl local) | D | P3, P7 → 07 |
| REQ-FUN-029 | When no capability fits, MIA shall say so and note the gap (`core/capability_gaps.py`), never improvise an action. | Must | MVP | All | Exists | T | P2 → 09 |

## C. Application ecosystem (what the OS and platform provide Prompt 03's framework)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-040 | The platform shall load MIA-native apps from their manifests at start, check each, and refuse none silently (a bad one is reported with why). | Must | MVP | All | Exists (M1 to M5) | T: `tests/test_app_registry.py` | DEC-0178 → 08 |
| REQ-FUN-041 | Apps shall share data only through capabilities, events, links and the history; no app reads another's store directly. | Must | MVP | All | Partial: true of the code's layering; not enforced per app until code moves (M6) | T: M6's import check | DEC-0175 → 05 |
| REQ-FUN-042 | A conventional Linux app shall be installable from Flathub on the person's yes, with its Flatpak permissions shown in plain words first. | Should | R1 | PC | Planned | D | DEC-0177 → 05, 10 |
| REQ-FUN-043 | A new MIA-native app shall be built in the lab (Forge), reviewed, and registered only on the person's approval of the merge. | Should | Mature | PC | Planned (prompt 22, M7) | D | DEC-0058, DEC-0175 → 08, 15 |
| REQ-FUN-044 | An app's background jobs shall run on the platform's scheduler, deferrable ones paced by homeostasis. | Must | MVP | All | Exists (`core/scheduler.py`, `core/homeostasis.py`) | T | DEC-0173 → 05 |

## D. Personal information and productivity

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-060 | Notes, journal, calendar, tasks, reminders, alarms, projects, missions and goals shall each be kept in the person's own store, readable and changeable by screen and voice. | Must | MVP | All | Exists (their stores and apps; parity decided) | T: parity | DEC-0125 → 10 |
| REQ-FUN-061 | One search shall find any record by its words across every store the person can see, each result naming its app and opening it. | Must | MVP | All | Exists (Ctrl+K, `core/web_search.py`) | T | P4 → 10 |
| REQ-FUN-062 | Search shall also find records by meaning (related words, not only the same words), each result marked as matched or inferred. | Should | R1 | PC | New (embeddings model present locally: nomic-embed-text) | M: recall on a labelled set *(provisional)* | prompt 23 §2.4 → 07 |
| REQ-FUN-063 | Any project shall open as a workspace that restores its apps and context per device. | Should | R1 | PC, Ph | Planned (WS-1 to WS-7) | D | WS-1 → 10 |
| REQ-FUN-064 | Email shall be drafted by MIA and sent only by the person pressing Send. | Must | MVP | PC, Ph | Exists (`core/email_drafts.py`, `core/mail_send.py`) | T | CLAUDE.md email rule → 13 |
| REQ-FUN-065 | Records shall link to each other by reference (`kind:id`) and every meaningful change shall enter the history, so "what happened with X" is answerable from records. | Must | MVP | All | Exists (`core/links.py`, `core/life_events.py`) | T | DEC-0173 → 07 |

## E. Smart home and physical environment

*OS vs app:* device drivers and buses are OS; each device's capability is an app's; the household automations are
workflows on the platform. A device's own safety logic stays on the device (DEC-0150).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-080 | Each controllable device shall be reached through a capability with a tier; a command to a device is consequential (`act_with_approval`) unless the person granted it for that device. | Must | R1 | PC, Pi | Partial: tiers exist; few device commands exist | T | DEC-0156, DEC-0150 → 08, 12 |
| REQ-FUN-081 | Device readings shall be kept with their source and time, and a stale reading shown as stale. | Must | R1 | All | Partial: the greenhouse snapshot; cameras | T | REQ-ARC-014 → 12 |
| REQ-FUN-082 | Home control on the local network shall work with the internet down. | Must | R1 | PC, Pi | New | M: S-12 | E3 → 12 |
| REQ-FUN-083 | A device that stops answering shall be shown as unreachable with when it was last heard, and its app's status says so. | Must | R1 | All | Partial (app status M5; device-level heartbeat not built) | T | P17 → 12, 14 |

## F. Homestead and agriculture

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-100 | MIA shall watch the greenhouse and aquaponics node's state and alarms. | Must | R1 | PC, Pi | Exists (`core/greenhouse_link.py`, `homestead/`) | T: `homestead/` scenarios | DEC-0145, DEC-0150 → 12 |
| REQ-FUN-103 | MIA shall be able to adjust the greenhouse's controllers (targets, schedules, modes) through capabilities: each adjustment is a device command, asked for unless Zac granted that kind for the greenhouse; the node and its safety microcontroller keep their hard limits and may refuse; she reports a change only once the node confirms it, and every adjustment is in the history with how to put it back. | Must | R1 | PC, Pi | New (today she only watches; provisioning exists) | T: a refused and a confirmed adjustment against the node's simulator | DEC-0185, REQ-FUN-080, REQ-AI-002 → 12, 08 |
| REQ-FUN-101 | Crops, plantings, flock, inventory and homestead projects shall be kept in their apps, linked to the projects and needs they serve. | Should | R1 | All | Exists (Greenhouse, Chickens, inventory, requirements) | T | DEC-0172 → 10 |
| REQ-FUN-102 | Quantities and material lists shall come from calculators in code, ending with the code-and-span-table note. | Must | MVP | All | Exists (`core/build_calcs.py`) | T | DEC-0118 → 07 |

## G. Finance and business

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-120 | Money, bills, debts, budgets, rentals, property, business and insurance records shall be sealed at rest and readable only in their owner's or household's session. | Must | MVP | All | Exists (sealing DEC-0126; household stores) | T: `tests/test_at_rest.py` | P7 → 13 |
| REQ-FUN-121 | Paying, transferring or committing money shall always need the person's yes at the moment, whatever was granted. | Must | MVP | All | Exists (tiers: `bill.pay`, `debt.pay` act_with_approval) | T: `tests/test_grants.py` | E4, DEC-0156 → 08 |
| REQ-FUN-122 | Bank links (Plaid) shall read only; their tokens are secrets kept sealed and never shown to the model. | Must | R1 | PC | Partial (`core/plaid_manager.py`) | I, T | P8 → 13 |
| REQ-FUN-123 | Money shall be shown in the person's currency (`core.region.money`). | Must | MVP | All | Exists | T | CLAUDE.md → 10 |

## H. Health, fitness and personal development

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-140 | Health, fitness and workout records shall be personal stores, never shared with the household or another app without the person's yes. | Must | MVP | All | Exists (PERSONAL_STORES) | T | MU-1, P7 → 13 |
| REQ-FUN-141 | Every learning goal shall be worked as a path: stages, practice logged, homework from the log, verified by evidence. | Should | MVP | All | Exists (`core/paths.py`) | T | DEC-0112 → 10 |
| REQ-FUN-142 | Crisis handling shall never depend on the model and shall use the person's country's numbers. | Must | MVP | All | Exists (`core/safety_floor.py`) | T | CLAUDE.md → 07 |

## I. Entertainment and recreation

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-160 | Music, games, the Dungeon, Living Worlds and recreation shall be apps on the platform, using no privileged capability. | Should | R1 | All | Exists as apps | I: their tiers | DEC-0175 → 10, 11 |
| REQ-FUN-161 | Immersive experiences (Living Worlds, The Convergence) shall start only when asked and leave cleanly to the workspace. | Should | Mature | PC, Gl | Partial | D | §5 → 11 |

## J. Communication and multi-user

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-180 | Household stores shall be shared only among members of a household approved by a member; personal stores never. | Must | MVP | All | Exists (`core/household_manager.py`) | T | MU-1, MU-6 → 13 |
| REQ-FUN-181 | Devices shall reach each other only after being paired by the person, and talk over an authenticated channel (LAN, or Tailscale away from home). | Must | MVP | All | Partial: the phone link and sync; Tailscale used | T, I | DEC-0022 → 12, 13 |
| REQ-FUN-182 | New work shall not design for other people in the house or for children (DEC-0119); existing accounts keep working. | Must | MVP | All | Exists as policy | I | DEC-0119 → all |

## K. Development and system administration

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-200 | MIA shall propose code changes only in an isolated worktree with no real data, run the tests, get another model's review and merge only on Zac's approval. | Must | MVP | PC | Exists (`core/dev_lab.py`, DEC-0058, DEC-0167) | T | DEC-0058 → 09, 15 |
| REQ-FUN-201 | Logs, the Fix-It Log, job records and the history shall be readable by the person and by MIA, with secrets redacted. | Must | MVP | All | Exists (`core/failure_log.py` redacts) | T | P9 → 14 |
| REQ-FUN-202 | A terminal, an editor, git and the Python toolchain shall be available in the conventional session without MIA. | Must | MVP | PC | Planned (in the image) | D | E2 → 15 |
| REQ-FUN-203 | Nightly backups shall be automatic, rotated, sealed and restorable by a documented step. | Must | MVP | PC | Exists (`core/auto_backup.py`); restore tested in the suite | T, D | P13 → 14 |

## 8. Cross-application workflows (§8)

Each scenario names who does what. *AI* proposes and phrases; *code* reads, decides, checks and records.

| Scenario | Intent and context | Apps and services | AI does | Code does | Permissions and approvals | Output | Fails how, recovers how |
|---|---|---|---|---|---|---|---|
| W-1 Greenhouse conditions | "How's the greenhouse? Should I water?" Needs the node's snapshot, history, weather, the plan's step | Greenhouse, Weather, history, relevance | chooses lookups, phrases the summary and recommendation | reads readings with their age, compares to thresholds, computes the recommendation's numbers; sends an approved adjustment and waits for the node's confirmation | observe; adjusting irrigation is a device command (asked for unless granted; the node's limits hold) | a summary with readings' times, a recommendation marked as hers | stale snapshot: says how old; no weather: says so, recommends on readings only |
| W-2 Prepare the week | "Get me ready for the week" | Calendar, tasks, kitchen, budget, missions, alarms | merges into a plan, phrases | assembles due items (`assemble_life_state_v2`), conflicts, totals | observe; each proposed change (grocery adds, reminders) by its tier | one plan; each change approvable | a store unreadable: plan says which part is missing |
| W-3 Property maintenance summary | "Maintenance summary for the rental" | Real Estate, Garage, tasks, budget | phrases the report | open tasks, costs, overdue items, from records | observe; sending the report is the person's | a report with sources | missing records: listed as gaps, not guessed |
| W-4 Learn a skill | "Help me learn welding" | Paths, Classroom, missions, World Intelligence | drafts the stages for approval | logs practice, schedules homework, verifies by evidence | starting a path on his say-so | a path, weekly homework | nothing logged: says so; never claims progress |
| W-5 Investigate a code problem | "Why does the greenhouse page fail?" | the lab, the Fix-It Log, inspection | hypotheses, proposed fix | reproduces in a worktree, runs tests, records evidence | merge on Zac's approval only | a diagnosis with evidence, a branch | can't reproduce: says so with what was tried |

**System requirements these reveal** (not obvious from apps alone):

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-FUN-220 | A plan spanning several apps shall show every step with its tier and let the person approve, change or drop steps one at a time. | Must | R1 | All | Partial: `core/step_plans.py` and the Step By Step page; steps are kinds that reach his records and can be undone (others are listed as "can't", done from their own screens); the only planner yet is the week's, from today's list | T: `tests/test_step_plans.py`; D: W-2 | W-2, FR-X1 → 08 |
| REQ-FUN-221 | An answer built from several stores shall name which parts it couldn't read, rather than leaving them out silently. | Must | MVP | All | Partial | T | P17 → 07 |
| REQ-FUN-222 | Every recommendation shall be marked as MIA's, separately from the facts it rests on. | Must | MVP | All | Partial (Living System invariant; not every surface) | T | DEC-0173 → 07 |

## 9 to 12. Intelligence, context, autonomy, provider independence

**What's AI and what's code (§9).** *Model:* understanding words, choosing among offered tools, decomposing a request,
phrasing, summarising, drafting, suggesting. *Code:* facts, numbers, permissions, scheduling, whether an action
succeeded, what she can do, who's speaking (once built), crisis handling. A model's statement that something happened
is never evidence that it did.

**Kinds of knowledge she must keep apart (§10)**, with how each is marked:

| Kind | Example | Marked as |
|---|---|---|
| Verified fact | a reading from the node, a recorded payment | its source and time |
| Person-given | "my truck gets 17 mpg" | "you told me", with when |
| Retrieved | a feed item, a search result | its source; outside text |
| Model conclusion | "the pump is probably undersized" | "I think", with what it rests on |
| Inference | a pattern from the history | "a pattern", labelled inferred |
| Speculation | — | not offered as an answer |
| Unknown | — | "I don't know" and what would tell her |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AI-001 | A stated number in an answer shall come from a lookup's result in that turn; an answer stating one that doesn't shall be replaced by the results themselves. | Must | MVP | All | Exists (`core.question_plans.invented_numbers`) | T | DEC-0004 → 07 |
| REQ-AI-002 | MIA shall report an action as done only after its executed record exists, and a device change only after the device or its service confirms it. | Must | MVP | All | Exists for actions; device confirmation New | T | §9 → 08, 12 |
| REQ-AI-003 | Each piece of context given to the model shall carry its kind (section above) so the answer can say how it's known. | Should | R1 | All | Partial (epistemic contract on new stores) | T | DEC-0173 → 07 |
| REQ-AI-004 | Context for a turn shall be assembled from stores by code, limited to what's relevant, never the person's whole record. | Must | MVP | All | Exists (`core/context_assembler.py`) | T: `tests/test_living_system.py` | P7 → 07 |
| REQ-AI-005 | A memory shall be kept only when the person says "keep it" (or tells her to remember), and can be seen, corrected and deleted; a deleted memory never returns. | Must | MVP | All | Exists (life notes; FR-M1, FR-M2) | T | DEC-0054 → 07 |
| REQ-AI-006 | Context older than its purpose (a conversation's working context, a workspace's session) shall expire or be summarised by rules the person can see. | Should | R1 | All | Partial (conversation summaries) | I | §10 → 07 |
| REQ-AI-007 | A private or personal turn (journaling, venting) shall never produce stored notes, offers or cross-app context. | Must | MVP | All | Exists (life notes rule; gate busy rule) | T | DEC-0054 → 07 |
| REQ-AI-010 | The model backend shall be chosen per task by rules in code: privacy (personal data stays local unless the person chose otherwise), the device's hardware, and latency; never by the model. | Must | R1 | All | Partial (`core/model_registry.py`, `core/home_link.py`: phone uses the PC's model when reachable) | T | E3 → 07 |
| REQ-AI-011 | Every function in the MVP shall work with no cloud provider configured. | Must | MVP | All | Exists today (local Ollama) | M: S-12 offline run | E3 → 07 |
| REQ-AI-012 | Before personal data is sent to a cloud model, MIA shall say what will leave, to whom, and ask, unless the person set a standing rule for that kind of task. | Must | R1 | All | New (no cloud backend in use) | T | P7 → 07, 13 |
| REQ-AI-013 | When the chosen model fails or times out, MIA shall fall back to the next local one and say which answered. | Must | MVP | All | Exists (FW-12: `llm.fallback_models`, the level names the model that answered) | T | P16, P17 → 07 |
| REQ-AI-014 | Replacing a provider or model shall change no store and no assembled context. | Must | MVP | All | Exists (`tests/test_living_system.py`) | T | DEC-0173 → 07 |
