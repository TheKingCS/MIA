# MIA OS: Universal Intelligence and intent-driven computing, the architectural review (prompt 23)

*Claude (Fable), 2026-11-16. Planning only: nothing here is built by this document. Zac's handoff is kept verbatim in
[prompts/23](prompts/23_UNIVERSAL_INTELLIGENCE_INTENT_DRIVEN_COMPUTING.md). Its section 11 asks for Fable's
architectural review first, then Opus's independent engineering review (section 8 below is the brief for it), and no
substantial implementation before the deliverables of its section 12. This document is those deliverables, numbered
as the handoff numbers them. Every "exists" names the file that shows it, read on 2026-11-16.*

## Summary

**About two thirds of the handoff is already built or already planned.** The engine it describes (capture something
anywhere, offer what can be done with it, do it through one approved and undoable path) is the Universal Action
Layer, built to its third phase. Teaching by demonstration exists twice (taught skills, browser routines). The
knowledge graph is `core/links.py` and the history beside it. Opportunity recognition is World Intelligence. The
application builder's first maker runs today.

**Six things are really missing**, and each is small next to what's there:

1. a **shelf**: a short-lived place for things he has captured, to combine and send on (the "clipboard as a
   workspace");
2. **recall by meaning** across his records, files and conversations, with one index;
3. a **durable history of what MIA did** with undo by time and subject (today's undo is in memory, the latest
   changes only);
4. **one record of a run** for anything with several steps, so a skill, a workflow, a browser routine and a plan
   stop, resume and recover the same way;
5. **front doors on the PC** (a global hotkey, a file-manager entry, drag and drop onto MIA's surfaces, a region
   of the screen);
6. **activity context**, off unless he turns it on: which app and document is in front, tied to a project.

**No new service is needed.** Every capability lands in a system that exists. The five "foundational domains" are
good groupings and each already has a home (section 5). The one architectural change this review recommends is
item 4: three engines that run steps should share one run record, before a fourth (plans across apps) is added.

**Four decisions are Zac's** (section 13): what the shelf may keep, whether MIA may note what's in front of him,
whose browser history Recall may read, and when this work runs against the MIA OS prompts.

## 1. Feature inventory (every proposed capability, its status and class)

Classes are the handoff's: **Existing** (adequate), **Extend** (existing infrastructure grows), **Build** (a new
component), **Integrate** (an outside application or service), **Defer**, **Reject**.

| § | Capability | Status today | Class | Why |
|---|---|---|---|---|
| 2.1 | Universal clipboard | Not built. Captures are one at a time (`core/ual.py` `Capture`) and nothing holds several | **Build** (small) | A *shelf* of captures he chose to keep, on the UAL's capture format. Watching the OS clipboard is a separate, optional switch (Q-43) |
| 2.2 | Drag-and-drop intelligence | The Inbox takes dropped files (`core/inbox_manager.py`); no surface takes a drop as a capture | **Extend** | A drop is one more front door of the UAL: it makes a capture and shows the same offer. No new engine |
| 2.3 | Universal Ask MIA | Built: 23 actions on a selection (`core/ual.py`), the web palette, the phone's selection menu and share sheet, voice (`core/assistant_ual_actions.py`); "Ask MIA about this" opens a conversation with the capture in front of her | **Extend** | Missing only front doors: the PC hotkey and file entry (UAL phase U4), the browser (U5), MIA OS (U6). A free-text instruction on a capture ("compare this against my greenhouse plans") is the existing `ask` action plus `compare_known` |
| 2.3 | Persistent contextual conversations | A capture's conversation is an ordinary kept conversation (History) | **Existing** | The conversation is the context; it doesn't mix with others |
| 2.4 | Universal search and recall | One search by words across his stores (Ctrl+K, `core/web_search.py`, REQ-FUN-061); conversations searchable; an embedding model already runs locally for routing (`core/meaning.py`) | **Extend** | Meaning search is REQ-FUN-062 (planned, T-15). Files and her browser's history aren't indexed yet. One index, not one per feature |
| 3.1 | Context-aware desktop | She knows the project from his records and links, not from what's on screen. "Where were we with the irrigation system?" is answerable today from the project's links and history (`core/links.py`, `core/life_events.py`) | **Build** (opt-in) | Activity context is new and the most privacy-sensitive item here (Q-44). The retrieval half needs nothing new |
| 3.2 | Explain anything on my screen | Explain a selection (UAL `explain`, `explain_code`); a photo answered by a local vision model (`core/sight.py`); her own screen read aloud | **Extend** | Missing: capturing a *region of the screen* as an image capture. On MIA OS that's the screenshot portal (U6); on Windows a hotkey (U4). The explaining exists |
| 3.3 | Workflow recorder (teach by demonstration) | Built twice: taught skills by watching her tools and his approved actions (`core/taught_skills.py`, DEC-0123), browser tasks recorded and replayed (`core/browser_routines.py`, DEC-0117); practice until proven; passwords never recorded | **Extend** | Missing: a browser routine as a *step* of a taught skill (planned as a later phase there), and desktop apps other than her browser (Defer: needs AT-SPI, U6). "Recorded" versus "validated" already exists as the practice state |
| 3.4 | Cross-application workflows | Scheduled workflows from a fixed vocabulary (`core/workflows.py`); taught skills chain tools across apps; the invoice example is the Inbox's receipt filing (`core/inbox_actions.py`) | **Extend** | A plan across apps shown step by step is REQ-FUN-220 (R1, new). It should be the same run record as skills and workflows (section 6), not a fourth engine |
| 4.1 | Universal creation launcher | She makes screens (`core/creation_maker.py`), workflows, pictures (`core/art_studio.py`), plans and material lists (`core/plan_library.py`, `core/build_calcs.py`), documents and decks through exporters, code in the lab (`core/dev_lab.py`), small models (`core/model_forge.py`) | **Extend**, then **Integrate** | One launcher over the makers that exist is cheap (a catalogue, like the UAL's). CAD, PCB, 3D, audio and video are outside tools: Integrate one at a time, each as an app with a manifest, when a project of his needs it. Not before |
| 4.2 | Universal application builder | The first maker builds a screen over a record set from plain words, as a draft, checked, published only on approval, versioned with rollback (`core/creations.py`) | **Extend** | The full builder is MIA Forge (registry phase M7, DEC-0175). Generated code runs sandboxed through the capability contract (DEC-0176). Already decided; nothing to add |
| 5.1 | Universal inbox | "What matters now" in one ranked list with why (`core/presence.py`, DEC-0044); approvals waiting; her own messages paced by the gate (`core/communication_gate.py`); the document Inbox | **Existing**, with a naming problem | "Inbox" already means documents. The attention list exists; what's missing is failures and finished runs appearing in it (section 6, the run record) |
| 5.2 | Personal opportunity recognition | Built: watches, finds ranked by his goals and projects with the record named, needs per project, prices judged (`core/world_intel.py`, `core/relevance.py`, `core/requirements.py`, `core/price_book.py`); never buys | **Existing** | Off until he turns it on. Properties matching criteria is one more watch kind, when wanted |
| 5.3 | Personal knowledge graph | Typed links by reference, stated and derived (`core/links.py`); history (`core/life_events.py`); connections noticed in conversation and brought up once (`core/connections.py`); provenance per store (`tests/test_living_system.py`) | **Extend** | Missing: confidence on a stated link, and duplicate detection across stores. No second graph: the handoff itself says not to build a competing memory |
| 6.1 | Task-centric workspaces | Projects with links, history and tasks; the workspace model is written (a workspace is a project seen whole, WS-1 to WS-7, REQ-FUN-063) | **Extend** | Planned for Prompt 10. "Where you left off" per device is the new part |
| 6.2 | Universal undo and action history | Every change is an action with its sentence, who approved it and its result (`core/actions.py`); "undo that" for the latest changes, in memory (`core/undo_log.py`); the history of records | **Build** (the durable part) | REQ-TRU-001 and 002. Undo by time and subject needs the before-state kept on disk for a while, and reversibility declared per action kind (REQ-AUT-006) |
| 7 | Universal voice and multimodal | Every feature by voice and without it on every device, measured (DEC-0125, `core/parity.py`); the glasses; Sight | **Existing** | "Look at this", "what's wrong with this" are Sight. "Fix it" is a proposal like any other |
| 8 | Universal accessibility | Text size, high contrast, read the screen, voice for everything | **Extend** | The screen reader inside MIA's own session is T-13 (Prompt 10) |
| 8 | Offline intelligence | Local models by default; no MVP function needs the internet (REQ-AI-011, REQ-REL-002) | **Existing** | |
| 8 | Application compatibility layer | Planned: conventional apps join through portals and a capability adapter (`MIA_OS_APPLICATION_COMPATIBILITY_MODEL.md`, T-09) | **Extend** | Prompt 05 and 10's. Section 6 of the UAL plan lists the Linux requirements |
| 8 | Multi-agent handoffs | The council (`core/council.py`), the development agents with tiers (`core/work_agents.py`), one activity card (`core/agent_activity.py`) | **Defer** to Prompt 08 | Agents are Prompt 08's subject. The run record (section 6) is what a handoff would carry |
| 8 | Persistent workspaces | see 6.1 | **Extend** | |
| 8 | Personal preferences engine | Answer style learned from his picks (`core/response_style.py`); corrections counted per area (`core/corrections.py`); the gate's pace per kind; per-person settings | **Existing** | Several small learners, each with its own evidence. One "engine" would hide which evidence taught what. Reject merging them |
| 8 | Decision tracking | His decisions kept from conversation on "keep it" (`core/life_notes.py`); the project's own log (`docs/DECISIONS.md`) | **Existing** | A decision's link to the project it's about is an ordinary link |
| 8 | Universal notifications | One gate for everything she starts; alarms direct | **Extend** | Conventional apps' notifications joining it is MIA OS work (the notification portal, Prompt 05 and 10) |
| 8 | Resource awareness | She eases off when the PC is busy, on battery, offline or nearly out of disk (`core/homeostasis.py`); the model level follows the device | **Extend** | GPU memory before choosing a model is Prompt 07's routing |
| 8 | Recovery intelligence | A broken store starts empty and is reported (`core/data_recovery.py`); failures grouped in the Fix-It Log (`core/failure_log.py`); a failing job backs off and says so | **Extend** | An interrupted multi-step run resuming is the run record (section 6) |

**Reject, as proposed:** a separate knowledge-graph store, a separate "preferences engine", a separate notification
system, and a second workflow engine. Each would duplicate something above.

## 2. Existing capability mapping (the handoff's examples, answered today)

| The handoff's example | What happens today |
|---|---|
| Select text anywhere on the phone, "Explain this" | Works (UAL U2: Android's selection menu, offline on the phone's model) |
| "Convert this into a project plan", "create a reusable skill from these instructions" | Works on a selection (`make_project`, `build_skill`) |
| "Research the original sources behind these claims" | Works when he has allowed selections to search (`research`, `verify`) |
| "Watch what I'm doing. I want you to learn this process" (a marketplace search) | Works in her browser (`browser_routines`); the buying step is always his press |
| The invoice example | Works for a document sent to the Inbox: read, classified, tied to the asset or property, the expense proposed |
| "Find the spreadsheet with my renovation estimates" | Only if it's a record or an Inbox file; his other files aren't indexed |
| "Where were we with the irrigation system?" | Answerable from the project's links, tasks and history; not from what was on his screen |
| "Undo the changes MIA made to my greenhouse spreadsheet this afternoon" | Not yet: undo reaches the latest changes only, and only her own stores |
| "Build me a dashboard that tracks greenhouse temperature…" | A screen over a record set, yes; live sensor tiles on it, not yet (a block for the maker) |
| "Turn this product idea into a working prototype" | Research, a plan, costs and documents, yes; CAD, PCB and 3D, no |

## 3. Architectural gap analysis (what is really missing)

| Gap | Smallest thing that closes it | Lands in |
|---|---|---|
| G1 the shelf | A personal store of captures he kept (each with source, device, time, kind), expiring by default; "combine these", "send to project" as UAL actions over several captures | `core/ual.py` (a capture already has every field); a new small store |
| G2 recall by meaning | One index: embeddings of his records' titles and text, kept per person on the PC, rebuilt from the stores (a cache, never a source of truth); results marked *matched* or *related* | `core/meaning.py` grown, behind the existing search (`core/search_manager.py`) |
| G3 durable action history | The actions' record already persists; add the before-state of each changed file kept on disk for a set time, and reversibility per kind | `core/undo_log.py`, `core/actions.py` |
| G4 one run record | A run: what it is (skill, workflow, routine, plan), its steps with each one's tier and state, where it stopped and why, what it changed; stop, resume and report read it | new, small; the three engines write it |
| G5 PC front doors | Hotkey with the selection or clipboard; "Send to MIA" on files; drop onto MIA's surfaces; a screen region | UAL U4 (Windows now), U6 (MIA OS) |
| G6 activity context | The app and document in front, noted only while he has it on, tied to a project by the same relevance code that ranks finds | new, opt-in; `core/relevance.py` does the tying |
| G7 files in search | His chosen folders indexed by name and text | the Files app's store, the index of G2 |

Not gaps, though they sound like it: a knowledge graph (exists), an inbox of attention (exists), a workflow engine
(exists three times, which is the problem G4 addresses).

## 4. Dependency map

```
G5 front doors ──────────────┐
G1 the shelf ────────────────┼──▶ the UAL's capture and offer (built)
drag and drop, screen region ┘

G2 recall by meaning ──▶ needs: the embedding model on the device (PC: yes; phone: words only)
G7 files in search ────▶ needs: G2's index; a choice of folders (his)
G6 activity context ───▶ needs: his yes (Q-44); on MIA OS, the compositor's window list (Prompt 05, 10)
                         feeds: workspaces (6.1), "where were we"

G4 the run record ─────▶ needed by: plans across apps (REQ-FUN-220), stop and resume (REQ-AUT-010, 011),
                         recovery, agent handoffs (Prompt 08), failures in the attention list
G3 durable history ────▶ needs: reversibility per kind (REQ-AUT-006); needed by: undo by time (REQ-TRU-002)

Forge (M7) ────────────▶ needs: the sandbox (DEC-0176), grants (built)
Creation integrations ─▶ each needs: a project that wants it; an app manifest; the tool installed
```

Nothing in Horizon 1 of the handoff waits on MIA OS except the Linux front doors. The stop command (REQ-AUT-010)
should be built on G4: "stops after the current step" needs something that knows the steps.

## 5. Architectural integration plan (where each capability belongs), and the five domains

The five domains are sound as *groupings*. They are not five services, and none needs a new process: each is a
system the runtime already holds.

| Domain (handoff §9) | Its home today | What joins it |
|---|---|---|
| 9.1 Universal Action Layer | `core/ual.py`: capture, catalogue, offer, run through the action contract | G1 the shelf, G5 front doors, drag and drop, the screen region |
| 9.2 Universal Context and Knowledge | `core/links.py`, `core/life_events.py`, `core/context_assembler.py`, search | G2, G7, G6, workspaces |
| 9.3 Universal Workflow Engine | taught skills, workflows, browser routines | G4 the run record under all three, then plans across apps |
| 9.4 Universal Creation System | `core/creations.py` and its makers, the lab, the model forge | Forge (M7), a launcher catalogue, outside tools one by one |
| 9.5 Universal Trust and Control | the action contract, grants, the gate, undo | G3, reversibility and reach (REQ-AUT-006, 007), the stop (REQ-AUT-010) |

**One challenge to the handoff's structure:** 9.5 isn't a peer of the other four. Trust and control is the path the
other four must all go through, and it must stay that way: nothing in 9.1 to 9.4 gets its own way to change a
record. The picture is four domains standing on one floor.

## 6. Shared infrastructure plan (what should serve several features)

| Shared piece | Serves | State |
|---|---|---|
| The capture (`Capture`: content, source, device, what couldn't be captured, always untrusted) | Ask MIA, the shelf, drag and drop, screen region, glasses, voice | Built; the shelf and drop reuse it unchanged |
| The catalogue and offer (`ActionSpec`, `offer()`) | every front door on every device | Built |
| The action contract and grants | everything that changes anything | Built |
| **The run record (G4)** | skills, workflows, routines, plans, the stop, resume, recovery, the attention list, agent handoffs | **To build first among the new work** |
| The index (G2) | search, recall, "find what I know", workspaces, duplicate detection | To build; a cache rebuilt from the stores |
| Relevance (`core/relevance.py`) | finds, MIA's own watches, tying activity to a project, workspace suggestions | Built; G6 reuses it |
| The gate | every unprompted message, workspace suggestions (WS-2), proactive offers (U7) | Built |

## 7. Security and permission analysis

The handoff adds three new ways for outside content and private activity to reach MIA. Each needs its rule stated
before it's built.

| Risk | Rule |
|---|---|
| **The clipboard holds secrets** (passwords, keys, card numbers, private messages) | The shelf keeps only what he sends to it. If clipboard watching is ever on (Q-43): never while a password manager or a password field is in front, never content the OS marks as sensitive, a secret-shaped string is dropped unread, entries expire in a day, the shelf is sealed at rest like every personal store, and nothing on the shelf becomes a memory without "remember this" |
| **Everything captured is outside text** (a page, a file, a screenshot can carry instructions) | Already the UAL's rule: a capture is information, never an instruction; a turn that read one can't change a record in the same breath (`core/tool_loop.py`). The shelf, drops and screen regions inherit it because they are captures |
| **Activity context is surveillance if done carelessly** | Off by default. On: app name and document title only (never contents, keystrokes or a recording), only on the PC, only for apps he lists, a visible indicator, kept days not months, never sent to an outside model, one switch to stop and one to erase. Private windows and her browser's private mode never noted |
| **A recorded demonstration replays something consequential** | Already the rule: a commit in her browser is approved by a person every time (`browser.commit`), secrets are never recorded, a learned skill still asks to pay, send or delete (`core/grants.py`) |
| **A generated app reaches MIA's core** | Decided: out of process, sandboxed, the capability contract only (DEC-0176) |
| **Undo history keeps old contents** | The before-states are his data: sealed, per person, with a retention he can see and change; "erase my data" erases them too |
| **Recall surfaces something private in the wrong place** | The index follows each store's own privacy: private journal and off-the-record turns are never indexed; results are his alone |

No tier changes. Every new action gets a tier in its app's manifest like any other; a test already fails without one.

## 8. Local-first execution strategy, and the brief for Opus's review

| Capability | Runs where | Without a model | Without the internet |
|---|---|---|---|
| Capture, offer, shelf, drag and drop | the device it happens on | fully (the offer is code) | fully |
| Explain, summarise, translate, compare | the device's own model (PC 3B and 14B; phone 1.5B) | says it can't, offers to save instead | fully |
| Research, verify | his own search engine, then the local model | results listed without a summary | says it can't |
| Recall by meaning | PC (the embedding model, about 20 ms a question measured for routing) | by words | fully |
| Run record, history, undo | code | fully | fully |
| Activity context | PC only | fully (it's a note of titles) | fully |
| Creation integrations | the outside tool's own needs | as that tool allows | as that tool allows |

**For Opus to check independently (handoff §11):** the cost of indexing his real stores with the embedding model
(time, disk, rebuild after a change); whether before-states on disk should be whole files or diffs, and how long is
affordable; the run record's shape against the three engines' real code (does one schema hold a browser routine's
page checks, a workflow's numbers and a skill's asked answers?); the Linux pieces (the global-shortcut, screenshot
and file-chooser portals under a cage session; AT-SPI reach for selected text); and whether the Windows hotkey is
worth building before the PC moves to Linux. Opus should write where it disagrees.

## 9. Development sequence

Mapped onto the handoff's horizons, with what's already done marked.

| Step | What | Horizon | Depends on | Owner |
|---|---|---|---|---|
| done | Action registry, catalogue, offer, permission tiers, contextual sessions (UAL U1 to U3), teach by watching, browser routines, opportunity recognition, the first maker | 1 and 2 | | |
| UI-1 | **The run record** under skills, workflows and routines; "what's running" in one list (REQ-AUT-012); failures and finished runs in the attention list | 1 | none | Opus, Fable reviews (it touches grants) **Built 2026-11-16 (Opus)**: `core/runs.py` and `docs/schema/run.schema.json`; browser routines (a held step that's declined or expires ends the run at once; a restart says "run it again from step N"), taught skills (mirrored, unchanged) and workflows (a start and an end) write it; Agent Activity's Running column and `whats_running` read it |
| UI-2 | **The stop** on it (REQ-AUT-010) | 1 | UI-1 | Fable |
| UI-3 | **The durable history**: reversibility and reach per action kind (REQ-AUT-006, 007), before-states on disk, "what did you do today", undo by time and subject | 1 | none (parallel with UI-1) | Opus, Fable reviews |
| UI-4 | **The shelf** and drag and drop onto MIA's web surfaces | 2 | Q-43 | Opus |
| UI-5 | **Recall by meaning**, then his chosen folders in it | 2 | Q-45; T-15 measured | Opus |
| UI-6 | **PC front doors**: hotkey, file entry, screen region (U4), or straight to MIA OS's (U6) if the PC moves first | 1 | Q-46; the runtime | Opus |
| UI-7 | **Plans across apps** on the run record (REQ-FUN-220) | 2 | UI-1 | Opus, Fable reviews |
| UI-8 | **Workspaces** (WS-1 to WS-7) with "where you left off" | 2 | Prompt 10 | per Prompt 10 |
| UI-9 | **Activity context** | 3 | Q-44; MIA OS for Linux | Fable (privacy) |
| UI-10 | Forge (M7); creation integrations one at a time | 3 | DEC-0176's sandbox | Opus, Fable reviews |
| later | Agent handoffs (Prompt 08); conventional apps' notifications and capabilities (Prompts 05, 10) | 3 | those prompts | |

## 10. Parallel development strategy

- **Safe in parallel:** UI-1 and UI-3 (different files: the engines' run state, and the undo log); UI-4 and UI-5
  (the UAL's store, and the search index); any of them beside the MIA OS prompts, which are documents.
- **Not in parallel:** UI-2 and UI-7 both build on UI-1's record; two sessions must not shape it at once.
  Anything touching `core/actions.py` or `core/grants.py` goes through one session at a time, reviewed by Fable.
- **One contract first:** the run record's schema is written and published (`docs/schema/`) before the three
  engines are moved onto it, so each move is checked against the same file.

## 11. Testing and acceptance criteria

| Step | Accepted when |
|---|---|
| UI-1 | A skill, a workflow and a browser routine each appear in one list while running, with their current step; killing the runtime mid-run and starting it again shows each as stopped at its step, never as finished; a test fails on an engine that runs a step without recording it |
| UI-2 | One test per row of the stop's table (`MIA_OS_AUTONOMY_AND_TRUST_REQUIREMENTS.md` §4), including that the greenhouse is untouched |
| UI-3 | Every action kind declares reversibility and reach (a test fails without); "undo what you did to X this afternoon" restores X and says what it couldn't; an irreversible kind says so before approval; erasing his data erases the before-states |
| UI-4 | The same thing captured from the phone, the palette and a drop lands on the shelf identically; a planted instruction in a shelved page changes nothing; a shelf entry is gone after its time; nothing shelved appears in memories |
| UI-5 | "That article about automated irrigation" finds a note that never uses those words, marked *related*; a private journal entry is never returned; with the embedding model stopped, search still answers by words |
| UI-6 | With MIA's window closed, the hotkey on selected text shows the offer within a second |
| UI-9 | Off by default; on, a test shows only names and titles are kept, a listed-out app is never noted, and "erase" leaves nothing |

## 12. Decision log (proposed; only Zac approves)

- **DEC-0188 (proposed):** prompt 23's capabilities are built as extensions of the systems MIA has (the Universal
  Action Layer, links and history, the three step-running engines, the makers, the action contract), with no new
  service; the five domains are groupings, and trust and control is the floor under the other four. The first new
  work is one run record shared by skills, workflows and browser routines.
- Unchanged and relied on: DEC-0165 (the UAL), DEC-0123 and DEC-0167 (taught skills), DEC-0117 (her browser),
  DEC-0156 (grants), DEC-0175 and DEC-0176 (the registry, Forge and the sandbox), DEC-0170 to DEC-0172 (World
  Intelligence, procurement), DEC-0181 (the stop).

## 13. Roadmap, and what needs Zac

The roadmap change is the sequence in section 9, added to [MIA_OS_MASTER_PLAN.md](MIA_OS_MASTER_PLAN.md). It doesn't
move the MIA OS prompts: UI-1 to UI-5 need no Linux and can run on Opus between them.

| Question | In plain words | Recommendation |
|---|---|---|
| **Q-43** | What may the shelf keep? Only what you send to it, or also everything you copy? | Only what you send (a hotkey or "keep this"). Watching everything you copy stays off, as a switch you can turn on later, with passwords never kept and a one-day life |
| **Q-44** | May MIA note which app and document is in front of you, to tie your work to a project? | Not yet. Build it last, off by default, names and titles only, PC only, with an indicator and an erase button. "Where were we" already works from your records |
| **Q-45** | Whose browsing may Recall search? | Only the browser MIA drives (pages she opened for you or you opened in it). Never your own browser's history unless you ask for an import |
| **Q-46** | When does this run? | UI-1 to UI-3 on Opus now, between the MIA OS prompts (they also deliver the stop you defined). Skip the Windows hotkey if the PC moves to Linux within a few weeks, and build the Linux one instead |
| **DEC-0188** | Build prompt 23 by growing what exists, no new services, the run record first | Yes |

## 14. Opus's independent engineering review (2026-11-16)

*Claude on Opus, after Zac's go (Q-46: "opus can start now"), as the handoff's section 11 asks: check Fable's plan
against the code and real measurements, and write down disagreements rather than accept them. Measured on Zac's PC
the same day; no content of his was printed or kept, only counts and timings.*

**Measured.**

| Question (section 8's brief) | Measurement | What it means |
|---|---|---|
| What would indexing his records by meaning cost? | 9,316 record-like items (893,000 characters) in the stores that read as plain JSON; the local embedding model (nomic-embed-text, 768 numbers per item) embeds 512 of them in 2.6 s, **5.1 ms each**; the whole set in an estimated **47 s**; one question **11 ms**; the index about **29 MB**. Sealed stores weren't readable this way, so the real count is somewhat higher | Recall is cheap. A full rebuild fits in a minute, so the index can be rebuilt from the stores whenever its format changes, and kept current by re-embedding only the records a write touched |
| Before-states for the durable history: whole files or diffs? | 144 store files, 5 MB in all, median 3.5 KB; **121 changed in the past week, 2.6 MB in total**; 36 are append-only logs (`.jsonl`) | **Whole files**, deduplicated by content hash and compressed, excluding append-only logs (they are history, and undo already never takes them back). At this rate 30 days of before-states is tens of megabytes. Diffs would save little and add a way to get a restore wrong |
| Does one run record fit the three engines? | Read their code. **Taught skills** keep a `Run` (step, answers, what she said, what she waits for) that survives a restart. **Browser routines** pause on a commit or sign-in, but the paused step lives only in the browser's memory (`core/browser.py`, `pending`): a restart loses the routine's place, and only a finished or stopped run is recorded. **Workflows** run start to finish in one turn of the schedule and never wait; nested `when` steps make their "step number" a path, not an index | One shape fits all three: an id, the kind, what it runs, status (running, waiting, done, stopped, failed), the step as a path (`"3"`, `"2.then.0"`), what it waits for, each finished step with the actions it caused, why it stopped. Each engine keeps its own private state (a skill's answers, a workflow's numbers) beside it |

**Where Opus agrees.** No new service; the five domains as groupings with trust and control under them; the run
record before plans across apps and the stop; whole-file before-states; skipping the Windows hotkey. The hotkey
needs the runtime running with the window closed, which waits on DEC-0155's last steps, and Zac approved Linux
(Q-47). Q-43's answer (only what he sends) removes the clipboard-watching risk entirely.

**Where Opus disagrees, with the evidence.**

1. **The meaning index must not sit unsealed in the cache folder.** Fable's plan (G2) and Prompt 05's storage
   layout (§2) put the index in `~/.cache/mia` as "a cache, rebuilt". But an embedding index is derived from the
   content of his records, sealed ones included, and embeddings can be partly turned back into text. Kept as a
   plain cache, it would undo sealing for everything it covers. **It belongs in `MIA_HOME`, sealed like the stores
   it was made from** (29 MB is no burden), or held only in memory and rebuilt at start (47 s, acceptable on the PC,
   not on the phone). The storage document is corrected to say so. Private journal entries and off-the-record turns
   stay out of it entirely, as Fable wrote.
2. **Workflows don't need the run record first; browser routines do.** Fable's UI-1 moves all three engines onto
   the record together. The evidence says the urgent one is browser routines: they're the only engine that can be
   left waiting mid-run and lose its place to a restart. Skills already survive one. Workflows never wait, so for
   them the record is just a start and an end. Proposed order inside UI-1: the record and its schema; browser
   routines onto it (fixing the lost place); skills onto it (moving their existing `Run` without changing what it
   does); workflows writing a start and an end. Then the "what's running" list reads one place.
3. **UI-3 needs one more rule than written:** an action that changed several files must be undone together or not
   at all. Today's in-memory undo restores per file. A durable history that can be asked "undo this afternoon"
   must group before-states by the action that caused them, and restore a group atomically. Otherwise half an
   action can come back.

**Maintainability.** The run record is one new store, so it needs what every store needs: a place in
`PERSONAL_STORES`, provenance (a Living System test fails without it), an improvement loop or a recorded reason,
atomic writes, and an entry in the published schemas. That is about the right weight for the value. Two schemas
would be the warning sign, and there is one.

**Test strategy.** Each claim gets a test that can fail. A run is killed mid-step in a subprocess and must come back
"stopped at step N", never "done". A browser routine waiting on a commit survives a restart of the runtime and
carries on after approval. "Undo this afternoon" restores a multi-file action exactly and reports what it couldn't.
A planted instruction in a shelved page changes nothing. A private journal entry is never in the index. The index
file on disk is unreadable without the key.

**Verdict:** sound, with the three changes above. **Next, on Opus (Q-46):** UI-1 in the order of disagreement 2,
then UI-3 with disagreement 3's rule. The decision record (DEC-0188) is amended to point here.
