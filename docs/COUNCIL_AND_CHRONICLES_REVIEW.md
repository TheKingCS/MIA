# Council Mode, the Glasses, and MIA: The Chronicles: Review and Proposal

*Claude, 2026-11-04, for Zac's review. It answers the handoff "Council Mode,
Glasses Integration & The Chronicles" (filed as
`docs/HANDOFFS/H-0081_chatgpt-to-claude_council-glasses-chronicles.md`) and
Zac's requirement in the same message: "the AI need to be able to communicate
to each other but in some smart restricted manor as to not needlessly have
them eat up the usage. They wont be much of a council if they cant
communicate."*

*The handoff asks for an audit and specification first, so nothing here is
built yet. Zac's requirement is DEC-0080, approved because it's his. The
design is DEC-0081 to DEC-0087, proposed (section 12).*

**Where the evidence comes from:**
- the repo at `e6b2383`;
- the phone app's code (`android-phone/`);
- what's installed on this PC.

I haven't timed a council member's answer over the glasses. The latency
figures below are from the CLI calls made so far.

---

## 1. The headline

1. **One council, everywhere.** The dev window's chat (`core/council.py`,
   built yesterday) becomes the council. Each conversation is a *thread*.
   Zac can start one by typing in the window or by speaking through the
   glasses. Either way it's the same record, the same rules and the same
   knowledge capture. The glasses are a voice and a display for it, not a
   second system.
2. **Agents talk to each other through MIA, on a budget.** An agent can't
   call another agent directly. At the end of its answer it can name one
   member and one concrete question. MIA (code first, her local model when
   needed) passes the question on only if:
   - the thread's budget allows it;
   - that member has time (DEC-0079);
   - the question hasn't been asked before;
   - MIA can't answer it herself from what's already decided.

   Members read MIA's running summary of the thread, not the whole chat.
   That alone cuts most of the cost (section 3).
3. **The voices already exist on the PC.** Kokoro (DEC-0051) is offline and
   Apache-2.0. Its voice pack has dozens of voices, so every member can have
   one at no cost. The phone's Android voice is the fallback when the PC
   isn't reachable.
4. **Speed is the real constraint, not the glasses.** A cloud member answers
   through its CLI on the PC in about 10 to 60 seconds. Council Mode is built
   around that:
   - MIA answers at once ("Codex is looking"), from her local model, which
     costs nothing;
   - members are told to keep it short when spoken, and the full answer is
     kept;
   - a long answer starts speaking at its first sentence, where the CLI
     streams.
5. **"The Chronicles" needs its own name in the code.** MIA already has a
   *Chronicle* (`core/chronicle.py`, DEC-0028): each person's own week, told
   from their life. The comic is a different thing, about *MIA's*
   development. It gets its own store, `core/saga.py` (working name), and
   folder, and keeps the series title *MIA: The Chronicles*.
6. **Privacy decides where each thing lives:**
   - Development milestones are repo history.
   - *Creator and MIA moments* are Zac's personal life, so they stay in his
     own folder on the PC. They never go in the repo (DEC-0002), and appear
     in an issue only once he marks them for it.
7. **Nothing in MIA generates images today.** Her screen photos came from
   ChatGPT by hand (H-0024). Weekly *scripts* can be automatic. Weekly *art*
   needs a choice from Zac (section 8.4).
8. **One thing to settle early: names for anything published.** A comic shown
   outside the family, with characters called Claude, ChatGPT, Codex and
   Copilot, leans on other companies' trademarks. My recommendation:
   - inside MIA, members keep their real names;
   - in the published series, the council gets fictional names and looks
     that come from their roles.

   This is Zac's choice (DEC-0087).

## 2. What exists, and what each part reuses (Phase 1)

| Needed | What exists | Reuse or build |
|---|---|---|
| Council conversations | `core/council.py`: threads by `reply_to`, @asks, read-only member calls, `@mia` from her docs and the history; kept in the repo and on the PC (`core/dev_store.py`) | **Extend**: thread budgets, agent-to-agent asks, moderation, session mode |
| Providers, swappable | `work/agents.json` (providers and roles, configurable); `core/work_review.ask_provider` (read-only calls, usage recorded); `core/dev_usage.py` (limits, reset times) | **Reuse**; members become a third list beside providers and roles |
| Voices | Kokoro on the PC (`core/voice_manager.py`, `core/voice_catalog.py`: 8 curated, the pack has more); Piper on the phone and Pi; Android TTS in the phone app (`Voice.kt`); `core/voice_effects.py` | **Extend**: a voice per member |
| Glasses voice | `core/glasses_voice.py`: the glasses are the phone's Bluetooth headset, Android's recognizer on the phone, the answer spoken back. User Sync (`core/user_sync.py`) is already a *mode* in which the words mean something else | **Extend**: Council Mode as another such mode |
| Glasses display | `web/glasses.*` through the sealed relay (DEC-0062), cards from `core/glasses_feed.py`, the orb's states | **Extend**: a speaker card, the orb in the speaker's colour |
| Phone ↔ PC | `core/home_link.py` (Tailscale; the PC's model for the phone); `/api/heavy/speak` (the PC's voice as audio) | **Reuse**: council turns run on the PC; the phone fetches text and audio over the link |
| Knowledge from discussions | DEC-0073 approved, **not built** (T-0024) | **Build** with T-0024 |
| Story material | `core/life_events.py` (each person's history); `core/chronicle.py` (their weekly story); `work/activity.jsonl` (the development's history); DECISIONS.md; git | **Reuse as sources**; the archive itself is new |
| Story Bible | Design docs (`docs/design/STARK_INTERFACE.md`, `web/tokens.css`: cyan, graphite, the orb) | **Build**, seeded from these |
| Images | None; screen photos made by hand (`docs/design/IMAGE_REQUESTS.md`) | **Build**, after Zac's choice |
| Approval | `core/actions.py` (Propose → Approve → Execute → Record → Undo) | **Reuse** for every comic approval |
| Adults only | `core/child_accounts.py`: `CHILD_BLOCKED_DOMAINS` | **Reuse**: the council and the Chronicles are the owner's |

## 3. How the council talks to itself, without wasting usage (DEC-0080)

The rules live in code (`core/council.py`). No agent can open a line to
another; every exchange passes through MIA.

1. **A thread has a budget, set when it opens.** A plain question costs one
   call. "Claude, start us off" is one call. "Debate it" is two rounds among
   the members named. "Council, work it out" is up to 6 calls by default,
   and Zac can raise or lower that. The window and the glasses show what's
   spent. When it runs out, MIA says so and summarizes instead of asking
   anyone else.
2. **An agent asks another only through a line it ends its answer with:**
   `ASK codex: <one concrete question>`. MIA passes it on only if all of
   these hold:
   - the budget has room;
   - the member is ready, not resting at a limit (`core/dev_usage.state`);
   - the question isn't close to one already asked in the thread;
   - MIA can't answer it herself. She checks her docs and the development
     history first, so "what did we decide about X?" never reaches a paid
     model.

   An ask that fails these is kept, not sent: the thread shows "held:
   budget" or "held: answered by DEC-0071".
3. **Members read a summary, not the chat.** MIA keeps a running summary of
   the thread with her local model, at no cost. A member gets that summary,
   the last two messages and the question. Today a member reads the last 20
   messages, so this is the biggest saving.
4. **Short by default.** A chat answer is capped at about 150 words, and a
   spoken one at about 60, unless Zac asks for detail. Members are told so in
   their prompt, and a longer answer is cut on screen with "more".
5. **Cheap first.** Opinions that don't need a frontier model go to local
   members (qwen, coder), and MIA's own knowledge comes before either. A
   frontier model is used where the thread needs it, or where Zac names it.
6. **It stops by itself** when any of these happens:
   - the members agree (each says `AGREE`);
   - two rounds add nothing new (similar to what was said);
   - the budget is spent;
   - a member is low on usage (DEC-0079's reserve);
   - Zac says stop.
7. **Development work talks the same way.** A reviewer's objection and the
   author's answer are already a disagreement thread (DEC-0071). The runner
   (T-0026) gets one round of author ↔ reviewer before it goes to Zac.
8. **Every call is on record:** in `core/dev_usage.py`, with purpose
   `council` and the thread id. The window shows what each thread cost.

## 4. Council Mode (specification items 1 and 2)

### 4.1 Members

`work/agents.json` gains `members`, separate from providers and roles, so no
role is tied to a provider:

```json
"members": {
  "mia":     {"name": "MIA", "provider": "mia", "voice": "kokoro:af_heart", "phone_voice": {"pitch": 1.0, "rate": 1.0}, "colour": "accent", "about": "Systems Inspector, coordination, knowledge"},
  "claude":  {"name": "Claude", "provider": "claude-code", "voice": "kokoro:bm_george", "about": "implementation and code"},
  "chatgpt": {"name": "ChatGPT", "provider": "codex", "persona": "architecture, research, planning", "voice": "kokoro:af_sarah"},
  "codex":   {"name": "Codex", "provider": "codex", "persona": "QA, code and security review", "voice": "kokoro:am_michael"},
  "copilot": {"name": "Copilot", "provider": "copilot", "voice": "kokoro:bf_emma"},
  "qwen":    {"name": "Qwen", "provider": "ollama", "voice": "kokoro:af_nicole"},
  "coder":   {"name": "Coder", "provider": "ollama-coder", "voice": "kokoro:bm_lewis"}
}
```

The voices here are only placeholders. Zac picks them by ear in the window:
it plays a sample, and his choice is saved.

**An honest limit.** "ChatGPT" and "Codex" both run through the Codex CLI on
Zac's ChatGPT account, which is the only route here without an API key. They
are one model with two briefs. They share one usage window, and they don't
count as two independent reviewers: the review rules count *providers*, not
names.

### 4.2 A session

A council *session* is a thread with a mode, the same way User Sync is a mode
in `core/glasses_voice.py`. While it's open:

- "Claude, start us off" and "Codex, look for risks": a name at the start is
  the addressee.
- "Council" or "everyone" asks the members in turn, within the budget.
- "Debate it, Claude and ChatGPT": two rounds.
- "MIA, sum up" or "where do we stand?": MIA, from the summary, at no cost.
- "Hold on" or a tap: stops whoever is speaking.
- "That's all" or "end the council": closes the session and runs the capture
  (section 5).
- Anything else is a message to the thread that asks no one.

Outside a session, glasses words stay MIA's, as today.

### 4.3 Turn-taking and speed

There's one speaker at a time, and replies are queued:

1. MIA announces the next speaker ("Codex next"), from her local model, so
   it's immediate.
2. While a cloud member thinks (10 to 60 seconds), the glasses show "Codex
   is looking", and MIA says so once.
3. Where the CLI streams (Claude's `stream-json`), speaking starts at the
   first full sentence.
4. Members that aren't available are skipped with a reason ("Codex is
   resting until 3:10"), and the session goes on with whoever's there.

## 5. Voices and audio (specification items 3 and 4)

- **The PC speaks for every member.** A council turn runs on the PC, where
  the CLIs and models are. The reply's text and its audio are made with
  Kokoro, in the member's voice, and collected by the phone over
  `core/home_link.py`. That's the same link `/api/heavy/speak` uses today, so
  the audio doesn't have to fit through the sealed relay (the H-0079
  problem).
- **The phone's fallback.** When the PC is unreachable, the phone speaks with
  Android's own text-to-speech, using a voice, pitch and rate per member
  (`phone_voice`). Only MIA and the phone's local model can answer then; the
  cloud members are said to be unavailable.
- **Who's speaking, without looking:**
  - each member has a short sound before they speak;
  - MIA's voice is the only one with her `voice_effects` polish;
  - the glasses show a speaker card (name, role, colour), and the orb takes
    that colour;
  - Zac's words are shown as his, with a microphone mark;
  - a model's words are marked as generated.
- **Interrupting.** A tap on the glasses stops playback at once. That's the
  first version. Stopping by voice while a reply is playing is harder over
  Bluetooth headset audio and comes later, once tested on the real glasses.
- **Licences.** Kokoro's voices are Apache-2.0. Piper's vary voice by voice,
  so each one is checked before anything is published. No voice imitates a
  real person or a provider's own product voice (DEC-0082).

## 6. From discussion to knowledge (specification items 5 and 12)

When a session or thread closes, the pipeline runs: CAPTURE → TRANSCRIBE →
IDENTIFY → SUMMARIZE → EVALUATE → STORE → APPLY.

| Step | What happens | Where |
|---|---|---|
| Capture / transcribe | Every turn is already a message with its speaker. Zac's speech arrives as text from the phone's recognizer | `core/council.py` |
| Identify | Code splits the thread into proposals, objections (which member, about what), questions left open, and asks | code over the messages |
| Summarize | The local model writes the outcome. Every claim carries the message ids it came from | qwen2.5:14b, no cost |
| Evaluate | Each claim is *said by X, unverified* until something backs it: a test, a commit, a decision. **A member's statement is never stored as fact** | the knowledge entry's `verification` |
| Store | Knowledge entries (DEC-0073), kind `council`, linked to the thread | `work/knowledge/` (T-0024) |
| Apply | Tasks it suggests are proposed into `work/tasks/` as open, with the thread as their source. Decisions it suggests are **proposed** in DECISIONS.md, because only Zac decides. When a task built from it is done, its entry becomes *implemented*; when tested, *validated* | `tools.work`, the loop |

This is the apprenticeship of the Developmental Independence review: every
thread is something MIA observed. Her own contributions in it (`@mia`) are
graded the same way as her other work, in the ledger (DEC-0075).

## 7. The Chronicle Archive and the Story Bible (items 6 and 7)

### 7.1 Where things live

| Material | Lives in | Why |
|---|---|---|
| Development milestones, council history, setbacks, ideas | `work/saga/events/` (repo) | The project's own history, shared by the team |
| Creator and MIA moments | Zac's own folder: `data/profiles/<id>/saga/` (PC) | Personal (DEC-0002): never in the repo |
| The Story Bible | `docs/chronicles/` (repo) | The team's canonical creative reference |
| Scripts and issue manifests | `work/saga/issues/` (repo) | Text: versioned, reviewable |
| Art, panels and references | `data/saga/art/` (PC), each file's hash in its issue's manifest | Images bloat git; the hash keeps them traceable |

### 7.2 An event

```yaml
id: E-0001
at: 2026-11-03T15:40:00Z
title: The first council meeting
summary: One or two plain sentences, made from the sources.
category: milestone | moment | council | setback | idea | character
timeline: real | fictional
subsystem: [council, glasses]
involved: [zac, claude, codex, mia]
sources: [task:T-0030, commit:37f92a2, thread:2026-11-04T051132-fea9c8, dec:DEC-0077]
evidence: verified | partial | none
status: built | in progress | planned | imagined
significance: 1-5 (suggested by code, set by Zac)
privacy: series | private | never
approved: proposed | yes | no
issue: null | 1
related: [E-0000]
```

### 7.3 How events get in

Relevance filtering is in code: rules decide which history becomes a
*candidate*, not a model. Ordinary turns never become one.

- **Finished tasks:**
  - one tied to a decision becomes a milestone;
  - one a *first of its kind* (a new provider, a first glasses session, a
    first council session) becomes a milestone with significance 4 or more.
- **Approved decisions** become turning points.
- **Reverts and long failures** become setbacks, with how they ended once
  they do.
- **Council threads** go in when Zac marks them, or when they end in a
  decision or a disagreement that Zac settled.
- **Zac says so:**
  - "MIA, remember this for the Chronicles" adds the moment;
  - "keep that private" or "not for the comic" marks it.
- Candidates wait in the window's **Chronicles** view, where Zac accepts,
  marks or drops them. Nothing joins the series by itself.

### 7.4 The Story Bible

The Story Bible is markdown in `docs/chronicles/`:

- `premise.md`;
- `timeline.md`, generated from approved events;
- `characters/<name>.md` (appearance, voice, personality direction, role,
  strengths, limits, relationships, *real* capabilities with refs, and
  *fictional* ones marked as such);
- `world.md`;
- `visual.md` (the palette and orb from `web/tokens.css` and
  STARK_INTERFACE, the panel style, and reference sheets by hash);
- `arcs.md`;
- `threads.md` (open plot threads);
- `issues.md`.

**Continuity is checked in code before any script is approved:**
- every real-world claim in a script has an approved event behind it;
- a capability shown as real has `status: built`;
- appearances match the character files;
- nothing `privacy: private` or `never` appears.

A script that fails a check names the line.

## 8. The weekly issue (items 8 and 9)

### 8.1 Pipeline

GATHER → SELECT → OUTLINE → SCRIPT → REVIEW → ILLUSTRATE → APPROVE → PUBLISH → ARCHIVE

| Step | Who | Rule |
|---|---|---|
| Gather | Code: the week's approved events | Sunday, like the personal Chronicle |
| Select | Code ranks by significance and arc; the local model proposes a story | **If the week is thin, it says so** and offers a short special, or rolls the week into the next issue. It never invents drama for a deadline |
| Outline | The writer (8.3) | Title, number, story, opening, scenes, cast, ending, and a "real milestones" note |
| Script | The writer | Pages (6 to 12), panels, dialogue, narration, expressions, composition |
| Review | Code first (continuity, 7.4), then Zac in the window | He edits any line; each edit is a new version |
| Illustrate | 8.4 | Per panel, from the reference sheets; **one panel can be redone alone** |
| Approve | Zac | Through the action contract (Propose → Approve), so it's recorded and undoable |
| Publish / archive | Code | The manifest (scripts, panel hashes, events), the Story Bible updated, the timeline extended, the events linked to the issue |

### 8.2 An issue manifest

```yaml
issue: 1
title: The Council
week: 2026-W45
status: draft | in review | approved | published
pages: [{page: 1, panels: [{n: 1, script: "...", art: sha256:..., version: 2}]}]
events: [E-0001, E-0002]
real_note: The council chat (T-0030), DEC-0071 to DEC-0080.
versions: script v3, art per panel
```

### 8.3 Who writes

Weekly scripting is creative writing, which the frontier models do best, and
it spends usage. Recommended: **ChatGPT** (through Codex) writes, Claude
reviews for accuracy against the events, and Zac edits. The writer can be
changed in `members`. When the cloud is out, the local model writes an
outline, and the script waits or is written locally. That's a real step down
in quality, and the issue says it was.

### 8.4 Art: Zac's choice (nothing generates images in MIA yet)

- **(a) By hand through ChatGPT, at first** (recommended). MIA prepares a
  *prompt pack* per panel: the panel's description, the Story Bible's
  character and style notes, and which reference sheet to attach. Zac
  generates the images in ChatGPT and drops them into the issue, and MIA
  hashes, files and links them. This needs no key and gives the best
  quality, but it's a person's half hour a week.
- **(b) Automatic through an image API** (OpenAI's or another): weekly,
  hands-off. It needs an API key in MIA's secrets (`core/secrets_manager.py`,
  never the repo) and is paid per image.
- **(c) Local, on the 7900 XTX** (SDXL or Flux through ComfyUI): free and
  offline once it runs. AMD on Windows is the hard part, and I'd have to
  verify it works before promising it. Character consistency needs reference
  conditioning or a trained style, which is more setup.

**Continuity, whatever the route:**
- a reference sheet per character and for MIA's interface, made once,
  approved, and listed in `visual.md`;
- every panel's prompt built from the Bible, never written freehand;
- art stored per panel with its prompt and version, so a fix redoes one
  panel.

## 9. Privacy, permissions and approval (item 10)

- **The owner's only.** The council, the Chronicles and their screens are
  adults-only, in `CHILD_BLOCKED_DOMAINS` and `CHILD_APPS` terms. On the
  glasses they need the owner signed in on the phone.
- **Personal moments** never leave Zac's folder unless he marks them
  `series`. Even then, only the event's summary joins an issue, not the
  conversation it came from. The council's repo copy is already redacted
  (DEC-0077).
- **Approval:**
  - drafts are drafts until Zac approves them;
  - **publishing beyond his own devices** (a site, prints, sharing) is a
    separate approval each time;
  - the published names and looks follow DEC-0087;
  - his own likeness as "the Creator" is his choice, set once in the Bible.
- **Nothing in a council session approves anything** (DEC-0077 holds on the
  glasses too). Decisions and tasks from a session are proposals.

## 10. Offline and provider independence (item 11; Part 7)

- **Everything that matters is MIA's own files,** never a provider's: the
  council's record, the knowledge, the archive, the Bible, the scripts, the
  art and its hashes. They live in the repo and on the PC, and the repo has
  its private GitHub copy.
- **Members are configuration.** A provider that's gone is removed from
  `members`, and the council goes on without it.
- **With no cloud at all,** MIA, qwen and coder still make a council. MIA can
  still organize the archive, keep the Bible and outline issues.
- **The storyline the handoff suggests** (the council goes quiet and MIA goes
  on) is literally what this design allows. It's a good arc for when it
  happens for real.

## 11. Roadmap, dependency-aware (Phase 4)

The order changes from the handoff's. The council's talking comes first
because Zac uses it daily and it *produces* the story material. The archive
starts recording at step 2, so the first council session is in it.

| Step | Builds | Depends | Accept when |
|---|---|---|---|
| 1 | **Restricted agent-to-agent talk** (section 3): thread budgets, `ASK` lines, MIA's checks, summaries instead of the chat, short answers, stop rules, cost per thread in the window | today's chat | A debate of two members ends within its budget. A held ask says why. A question about a decision is answered by MIA without any paid call. Context per call is under a set size |
| 2 | **The archive's foundation**: events in the repo and the personal folder; candidates from tasks, decisions, reverts and threads; "remember this for the Chronicles"; the Chronicles view; the Bible seeded | 1 (threads) | The week's real work becomes candidates with sources. A private moment can't enter the repo (tested). Zac can accept, mark or drop |
| 3 | **Voices**: `members` with a voice each; Kokoro per member on the PC; Android fallback; sample-and-pick in the window | — | Each member has a voice on the PC and the phone. A member's sound plays before they speak |
| 4 | **Council Mode on the glasses**: the session mode, addressing by name, rounds and debates through step 1's rules, speaker cards, tap to stop, the PC's audio over the home link | 1, 3 | Tested on the real glasses: summon, address, interrupt, end, with a member unavailable along the way |
| 5 | **Capture to knowledge**: section 6, with the knowledge vault | 1, T-0024 | A closed session leaves entries with sources and verification. Proposed tasks and decisions only |
| 6 | **Issue planning and scripts**: select, outline and script, continuity checks, review and edit in the window | 2, Bible | A thin week says so. A script with an unbacked claim or a private event fails, naming the line |
| 7 | **Visual continuity and art**: reference sheets, prompt packs (8.4a), per-panel versions; (b) or (c) if chosen | 6, Zac's choice | Redoing one panel changes nothing else. Every panel's hash is in the manifest |
| 8 | **The weekly production**: Sunday's run, approval through the action contract, publishing to Zac's devices, the Bible and timeline updated | 6, 7 | Issue #001 is approved by Zac and traceable to every event in it |

Steps 1, 2 and 3 don't depend on each other's code and can go in any order.
Step 5 waits for T-0024.

## 12. Decisions

- **DEC-0080 (approved, Zac's requirement):** the council's members can
  talk to each other, in a restricted way that doesn't waste usage.
- **DEC-0081 (proposed):** one council everywhere. The dev window's chat,
  the phone and the glasses share threads, rules and capture
  (`core/council.py`); a voice session is a thread in a mode. The agent
  talk follows section 3: through MIA, budgeted, summaries not the chat, ask
  lines checked, cheap first.
- **DEC-0082 (proposed):** council voices. Members in `work/agents.json`,
  each with a Kokoro voice on the PC and an Android fallback on the phone,
  chosen by Zac by ear. A sound and a speaker card mark who's speaking. No
  voice imitates a real person or a provider's own voice, and each voice's
  licence is checked before anything is published.
- **DEC-0083 (proposed):** council threads become knowledge (section 6).
  Every claim keeps its source and stays unverified until something backs
  it. Tasks and decisions from a thread are only proposed.
- **DEC-0084 (proposed):** the Chronicle Archive (`core/saga.py`, working
  name), separate from the personal Chronicle (DEC-0028):
  - development events in `work/saga/`;
  - personal moments only in Zac's own folder;
  - candidates found by rules in code and joined only by Zac;
  - a privacy mark on every event.
- **DEC-0085 (proposed):** the Story Bible in `docs/chronicles/`, canonical.
  Continuity is checked in code before a script is approved: claims backed
  by approved events, real against fictional capabilities, appearances,
  privacy.
- **DEC-0086 (proposed):** weekly issues, drafts until Zac approves them.
  The weekly run may say a week is too thin rather than invent drama.
  Scripts go in the repo; art goes on the PC, by hash, versioned per panel.
  The writer is configurable. **Open choice:** art by hand through ChatGPT
  first (recommended), an image API (key in MIA's secrets, paid per image),
  or local on the GPU (once verified).
- **DEC-0087 (proposed; Zac's choice):** for anything published beyond his
  devices, the council gets fictional names and looks that come from their
  roles, and the real product names stay internal (recommended); or he
  keeps the real names and accepts the trademark question. Also his choice:
  whether "the Creator" looks like him.

## 13. Documentation that follows

Built with the steps, not before:
- `docs/chronicles/` (the Bible);
- `docs/user_help/council.md` (how to talk to the council on the glasses);
- `docs/schema/saga_event.schema.json` and `saga_issue.schema.json`, checked
  by tests as `life_state.schema.json` is;
- an entry in `docs/WEB_PARITY.md` for the Chronicles view;
- a handoff to Muse for the speaker cards, the Chronicles screen, and the
  reference sheets' direction.
