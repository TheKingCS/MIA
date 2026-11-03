# Personality & Ecosystem Audit (Phase 0)

*Claude, 2026-11-03, for Zac's review. The handoff "Personality Evolution &
Intelligence Ecosystem" asked for two audits before any building. Nothing here
is implemented yet: each proposal needs Zac's approval.*

**How this was done.** Read the code that writes MIA's words, her prompts and
modes, and the self-knowledge, testing and tooling she already has. Measured
her real answers: the 112 questions of the Intelligence Benchmark
(`pc-check/intelligence-qwen2.5-14b.json`, qwen2.5:14b), lengths and habits
counted, nothing personal quoted. Not done yet: a fresh run of real
conversations (jokes, frustration, disagreement), which is the first job of the
corpus in A6.

---

## Audit A: Personality & Communication

### A1. Where her words come from today

Six producers, each with its own rules:

| Producer | Where | Voice rules it gets |
|---|---|---|
| Fixed replies (safety floor, mode switches, show-off) | `core/talk_it_out.py`, `core/show_off.py`, `core/safety_floor.py` | Written by hand |
| Plain-word commands ("I weigh 182") | `core/quick_commands.py` | Code templates |
| Detailed questions (DEC-0052 plans) | `core/question_plans.py` | Its own system prompt (`ANSWER_PROTOCOL`) plus the identity line |
| Action requests | `assistant_chat.build_system_message(is_action_request=True)` | **The bare identity line only** ("You are MIA (Multifunctional Intelligent Assistant), the user's personal assistant...") |
| Everything else to the model | same, info path | Identity + `_IDENTITY_WARMTH` + `_IDENTITY_APP_FLUENCY` + context + `CONVERSATION_INSTRUCTION` |
| Personal modes (Listen, Direct, Plan...) | `build_personal_system_message` + `conversation_modes.MODE_INSTRUCTIONS` | Identity + warmth + agency + one tone line per mode |
| Action confirmations | every `*_actions.py` | Code templates ("Added X to the grocery list.") |
| Unprompted notes, the Chronicle, buffs | `communication_gate`, `personality.guilt_in` | Guilt check only |
| Other prompts | `core/discovery_manager.py:464` ("You are MIA, a personal capability-building assistant") | Its own identity |

Personality itself lives in three unconnected places: prose strings in
`core/assistant_chat.py`, the guide `docs/design/MIA_VOICE.md`, and
`core/personality.py`, which only checks for guilt words (DEC-0014).

### A2. What the measurements show

Median **62 words**, about **25 seconds spoken**; one in ten past **127 words,
about 50 seconds**. The handoff's glasses target is 5 to 8 seconds, about 15 to
20 words.

| Route | Answers | Median words | 90th percentile |
|---|---|---|---|
| Model, no tools | 41 | 71 | 245 |
| Code plans (today, progress, freedom, money...) | 62 | 50 to 106 | up to 178 |
| Model with tools | 9 | 28 to 100 | 163 |

Habits, out of 112: 29 end with an offer or a question ("Let me know if..."), 8
use a list, 6 use markdown bold, 6 open with filler ("Sure", "Of course").
**None narrate operations, and none apologise.**

### A3. Why her answers run long

1. **Nothing knows which device is listening.** The glasses, the phone and the
   PC all run the same turn (`core/assistant_turn.py`), with the same
   instructions. There's no surface anywhere in the pipeline.
2. **The plans answer everything they found.** `ANSWER_PROTOCOL` asks for "a
   few short sentences or a short list" and "the one thing that matters most",
   but hands the model the whole fact sheet, and the model uses it.
3. **"Keep it brief" is the only length rule**, at the end of a long prompt,
   with no budget.
4. **Replies pile up.** A turn returns a list (a mode notice, then each tool's
   confirmation, then a learning offer), joined for speech.
5. **My own glasses fix is the truncation the handoff rules out.**
   `core/glasses_voice.spoken()` (2026-11-03) cuts her answer to about 220
   characters at a sentence end. It should be replaced by composition (A7).

### A4. Why she feels robotic

The measurements rule out the obvious cause: she doesn't narrate. What does it:

1. **Information dumps.** Long answers that list what she found, not what
   matters.
2. **Closing offers.** One answer in four ends "Let me know if...".
3. **Code templates.** Confirmations are correct and flat ("Logged 182 lb."),
   and they're most of what she says after an action.
4. **Her identity reads like a product.** "You are MIA (Multifunctional
   Intelligent Assistant), the user's personal assistant": a title and "the
   user", not a person she knows. On the action path that line is all she gets.
5. **The warmth line is generic** ("like a lifelong friend... celebrate their
   wins, comfort them"). Nothing in any prompt allows humor, disagreement,
   pointing out what's missed, or noticing a joke: the Companion, Natural and
   Independent picks aren't written down anywhere she reads.
6. **The voice guide disagrees with the new direction.** `MIA_VOICE.md` says "a
   warm, plain-spoken friend... encouraging without cheerleading". Close, but no
   wit, no confidence, no disagreement. Its first line is also corrupted
   ("patched ok"), left there by a script.

### A5. Where a statement becomes a command

`looks_like_action_request()` is pure keyword matching (`"open "`, `"remind
me"`, `"what did i do"`...). "I really need to get this workshop built" doesn't
match, so it goes to conversation, which is right. The risk is the other way:
"open" or "remind me" anywhere in a sentence makes it an action, with tools.
`core/meaning.py` and `question_plans.NOT_A_PLAN` already sort some intent; no
single place decides "command, question, chat, joke, feeling, plan" first.
Context: history keeps the last 12 messages; `core/conversation_state.py`
carries the topic. Not yet tested: losing the thread across surfaces (glasses
to phone).

### A6. What already exists to build on

`conversation_modes` (nine modes, kept), `conversation_state`, `meaning`,
`question_plans` (facts in code, the model phrases), `presence` and `findings`
(what to notice), `communication_gate` (five a day, spacing, duplicates,
dismissals: kept as is), `personality.guilt_in`, `tools/intelligence_check.py`
and `model_bench` (real-model runs), and `failure_log` (where she stumbles).

### A7. Proposed changes

**P1. One personality, one place.** `core/personality.py` grows from a guilt
check into the policy: a compact persona (Companion, natural humor,
independent; JARVIS, EDITH and Cortana as inspirations only; honest about
being an AI; DEC-0014), plus the rules code can check. Every prompt takes its
identity from there, in second person ("you know Zac"). `MIA_VOICE.md` is
rewritten to match and its corruption fixed. **The action path keeps its short
line**: it gets the new identity sentence, no more, because that's the
fragile, tuned path.

**P2. Device-aware composition: `core/response_composer.py`.** A surface
(`glasses`, `phone`, `pc`) travels with each turn, from `glasses_voice`, the
phone's Talk and the desktop. The composer:
- Gives each surface a budget: glasses one or two sentences (about 20 words),
  phone a short paragraph, PC full.
- For **code answers** (plans, commands, confirmations), the facts gain a
  ranked headline, so the glasses get the headline, not a cut-off paragraph.
  This covers most of what she says on the move, with no extra model call.
- For **model answers**, the surface's length line goes into the prompt, and
  the glasses get a spoken version composed from the answer. Composing costs a
  second short model call (about 1 to 3 seconds); measured before choosing.
- Keeps the whole answer in the conversation, so the phone or PC shows it.
- Replaces `glasses_voice.spoken()`.

**P3. Intent before action.** One step, in code first, that sorts a message:
command, question, chat, humor, frustration, feeling, plan, follow-up, advice,
hypothetical. It feeds the existing split (action path, info path, personal
modes) instead of the keyword list alone. The action path's prompt and tools
don't change.

**P4. Independent initiative, inside the existing gate.** Her noticing comes
from `presence` and `findings`; her offers go through Propose (DEC-0062's
pattern). The gate's limits stay.

**P5. The golden conversation corpus.** A new `tools/conversation_check.py`,
built like `intelligence_check.py`: the handoff's categories (greetings, jokes,
frustration, emotional, planning, commands, follow-ups, disagreement, wrong
assumptions, failed tools, suggestions), run on the real local model, per
surface. Scored two ways: code checks (length, filler, closing offers, lists,
guilt, numbers from the facts only), and Zac's review of a sample.

### A8. Files

- **Modify:** `core/personality.py`, `core/assistant_chat.py` (identity and
  info prompts), `core/question_plans.py` (headlines), `core/assistant_turn.py`
  (surface, composer), `core/glasses_voice.py`, `server/app.py` (surface on
  Talk), `docs/design/MIA_VOICE.md`.
- **New:** `core/response_composer.py`, `tools/conversation_check.py`,
  `data/conversation_cases.json`, tests.
- **Leave alone:** the action path's prompt and tool calling, the safety floor,
  `communication_gate`'s limits, the modes.

### A9. Regression risks

1. **Tool calling**: the measured weak spot. Identity text grows only on the
   info path; the benchmark's tool-choice score (213/213) must hold after every
   change.
2. **Grounding**: a shorter answer mustn't drop a caveat ("that's an
   estimate"). The corpus checks numbers against the facts.
3. **Latency**: any composing call is measured; the glasses can't wait.
4. **Safety floor and DEC-0014**: unchanged, covered by existing tests.

### A10. Test strategy

Every existing test stays green; the Intelligence Benchmark is rerun before
and after each phase (tool choice, speed, answer length); the corpus runs on
the real model; and Zac reviews a sample on the glasses themselves.

---

## Audit B: Development & Intelligence Ecosystem

### B1. What exists (inventory)

| Area | What MIA has |
|---|---|
| Project tracking | `docs/NEXT_SESSION.md` (to-do), `docs/ROADMAP.md`, `docs/DECISIONS.md` (66 decisions), `docs/HANDOFFS/` (81), `docs/CURRENT_STATE.md`, `docs/QUESTIONS.md`: the team's shared memory (DEC: `docs/COLLABORATION.md`) |
| Code | GitHub, private; 6 CI workflows (Windows, Android, phone, model check, Pages, food table) |
| Tests | 291 test files; `tools/intelligence_check.py`, `bench_audit.py`, `model_check.py`, `pc_check.py`, `web_check.py`, `user_sync_check.py` |
| Self-knowledge | `capabilities.py` (what she can do, from code), `self_docs.py` (her own design docs), `model_registry.py` (which model, asked of the runtime), `inspection.py` (Universal Inspection: the core, this computer, herself), `fact_owners.py` (one owner per fact) |
| Self-development | `dev_lab.py` + `tools/lab.py` (proposals written and tested in isolation, in only by approval: DEC-0058) |
| World and life | `life_events.py`, `links.py`, `context_assembler.assemble_life_state_v2` (`/api/state`), `presence.py`, `findings.py`, `why_graph.py`, `world_map.py` |
| Monitoring | `logger.py` (file log), `failure_log.py` (where she stumbles), `system_health.py`, `usage_tracker.py` (page and app use), `undo_log.py`, `backup_manager.py` |
| Models | Ollama on the PC (qwen2.5:14b; qwen3:14b, qwen2.5:32b, llama3.2 installed; nomic-embed-text for memory), llama.cpp on the phone, Kokoro and Piper voices; `llm_manager` already routes home PC, then the phone's own |
| Integrations | Plaid, Tailscale, Cloudflare (relay and the glasses' page), Meta's toolkit and Web Apps, GitHub, Claude (the lab) |
| Agents | One assistant with a lookup loop (`tool_loop.py`); no separate agents |

### B2. Existing versus missing

| Capability | Status |
|---|---|
| Feature, bug and milestone tracking | **Partial**: Markdown files, not queryable |
| Capability registry | **Exists** (`capabilities.py`), without dependencies |
| Hardware registry | **Partial**: Inspection reads this computer; the phone, glasses, Pi and AI HAT aren't recorded together |
| Software registry | **Partial**: module discovery and `requirements.txt`, no versions or services |
| Dependency map (service, capability, device) | **Missing**: the biggest gap; nothing can answer "if Ollama stops, what breaks?" |
| Performance registry | **Partial**: benchmark files and the failure log, no history over time |
| Development registry | **Exists**: the lab's proposals |
| Model router | **Seed**: home PC then phone; not by task |
| Specialized agents | **Missing** |
| Vision | **Partial**: OCR for receipts; no general vision model |
| Turn tracing (what she was given, which tools, how long) | **Missing**: the failure log keeps stumbles only |
| Capability marketplace | **Seed**: `module_validator` checks a module before install; no discovery, scoped permissions or revocation |
| Development dashboard | **Missing** |

### B3. Duplicates to avoid

Many of the handoff's registries already exist under other names. Building them
new would make two of each:
- The **Capability, Knowledge and Development registries** are `capabilities`,
  `self_docs` with `DECISIONS.md`, and `dev_lab`.
- **Hardware** belongs in `inspection`.
- **Performance** belongs with `failure_log` and the benchmarks.
- **Interconnection** should use `links.py`, which already relates things by
  `kind:id`.

The handoff's warning about competing systems applies here directly.

### B4. External tools

| Tool | Problem it solves | Already have? | Recommendation |
|---|---|---|---|
| **GitHub** | Code, CI, history | Yes | Keep as the source of truth for code |
| **GitHub Issues + Projects** | Queryable tasks, bugs, milestones | Free, in the same place | **Recommended** in place of Linear: no new account or sync, and cloud Claude sessions already reach GitHub. Mirror `NEXT_SESSION.md`'s build queue into issues and keep the file as the session note |
| **Linear** | The same, with better planning | Duplicates GitHub Issues | Not now. A second tracker to keep in step; revisit if the team outgrows Issues |
| **Notion** | Documentation and research | `docs/`, which every Claude reads | **Not recommended**: copies would drift, and Claude sessions don't read Notion by default |
| **Langfuse** | Model traces and evaluation | Partly (failure log, benchmarks) | Not yet. Self-hosting needs Docker and Postgres, and the cloud version sends conversations out. **Native turn traces first** (a JSONL beside the failure log); Langfuse later if those prove too thin |
| **MCP servers** | New tools, shared format | No | Later, through the marketplace's sandbox only. Each server runs with real access |
| **Vision model** (e.g. a Qwen-VL in Ollama) | Inspecting images and surroundings | OCR only | Worth evaluating locally for Inspection and the glasses' camera |
| **SearXNG** | Private web search | Approved (DEC-0053), not built | Build as approved |

Cost and privacy: every recommendation above is free and keeps personal data
on MIA's own devices, except where noted.

### B5. Dependency map, in short

```
Talk  -> llm_manager -> Ollama (PC, Tailscale) | llama.cpp (phone)
      -> memory -> nomic-embed-text (Ollama)
Voice -> Kokoro | Piper (PC) ; phone's own speech
Glasses -> phone app -> relay (Cloudflare) -> page (Cloudflare)
Money -> Plaid (cloud) ; Budget, Freedom
Lab   -> Claude (cloud) ; git worktrees ; the test suite
```

The registry work (C3) would make this map from code, so it can't go stale.

### B6. Architecture gaps

1. No dependency map between services, capabilities and devices.
2. Tasks live in prose, so nothing can query them.
3. No record of each turn, so "why did she answer like that?" is guesswork.
4. The model can't be chosen by task.
5. One assistant does everything; no specialized agents.

---

## C. Recommended order

| Phase | What | Why now | Size |
|---|---|---|---|
| **1** | **Glasses composition** (A7 P2, code answers first) and the **persona policy** (P1), measured by the corpus (P5) | The daily pain; most of it needs no extra model call | Medium |
| 2 | **Turn traces** (native), then GitHub Issues for the build queue | Makes every later phase measurable and trackable | Small |
| 3 | **Self-Knowledge registry**: extend `capabilities` + `inspection` with devices, services and their dependencies, through `links.py` | Answers "what breaks if...", and is the base for everything after | Medium |
| 4 | Intent first (P3), then model routing by task (extend `llm_manager`) | Needs the traces to tune | Medium |
| 5 | Specialized agents (research, engineering, QA) on the lab | Builds on the lab and the registry | Large |
| 6 | Capability marketplace (discover, sandbox, scoped permission, revoke) | The riskiest: last, with its own security review | Large |
| 7 | Development Intelligence Center: one dashboard over the above, no new database | Shows what phases 2 to 6 made | Medium |

**Acceptance for phase 1:**
- **Length:** 90% of glasses replies at 25 words or fewer, with the full answer
  kept in the conversation.
- **No regressions:** tool-choice still 213/213, no grounding errors added,
  median latency within half a second of today.
- **Tone:** corpus checks for filler and closing offers fall by half.
- **Zac's say:** he rates a sample on the real glasses.

## D. Decisions for Zac

1. Approve phase 1 as described?
2. Rewrite `MIA_VOICE.md` to the Companion personality (P1)?
3. GitHub Issues in place of Linear and Notion?
4. Native turn traces before Langfuse?
5. The composer's second model call for long model answers: allowed, if the
   corpus shows it's needed and it stays under about 2 seconds?

---

## E. Phase 1 results (2026-11-03, qwen2.5:14b, 37 corpus cases)

| | Before | After |
|---|---|---|
| Glasses, median words | 51 | **15** (about 6 seconds spoken) |
| Glasses, within 25 words | 8 of 37 | **36 of 37** (97%; target 90%) |
| Glasses, median time to answer | 2.0 s | **1.5 s** |
| Filler, closing offers, lists, markdown on the glasses | 4 | **0** |
| Phone, median words (whole answer) | 51 | 44 |
| Tool choice (`tools/pc_model_check.py`) | 213/213 | **213/213** |

How: one personality (`core/personality.py`: IDENTITY, CHARACTER) in every
prompt but the action path's; the glasses' answer composed by
`core/response_composer.py`. **Her own opening sentences when they fit** (32
of 37), and a short model rewrite only when her opening is too long to speak
(5 of 37). Tried the other way round first, the rewrites lost her warmth
("I'm here, Zac." disappeared), flattened jokes, and once added a fact
("smell of blood" about bulls), so the order was flipped and the rewrite told
to add nothing. Numbers in a rewrite must be the answer's own.

**What phase 1 didn't fix: the model's own manner.**
- She still misses some jokes, answers "Do you have feelings?" stiffly, and
  ends phone answers with an offer of help more often than before (4 of 37,
  was 1).
- She once listed what you "haven't completed", which brushes DEC-0014. The
  guilt-word check doesn't catch that phrasing.

These are the next things to work on, with the corpus to measure them:
tighter wording in CHARACTER, a few worked examples, or qwen3:14b, which the
benchmark found reasons better. Full runs: `pc-check/conversation-*.md`, kept
out of git.

Unrelated, and found along the way: `tests/test_inbox.py` and
`tests/test_ocr.py` fail on this PC on unchanged code (Tesseract is
installed, and the tests expect it not to be), and the full suite stops with
a Qt access violation near `tests/test_password_vault.py`.

## F. Tuning, round 1 (2026-11-03)

Zac's order: tune her instructions, then ratings, a fine-tune later, models
shopped for later.

- **Instructions:** CHARACTER now says what to do about the misses (an AI
  question answered simply and warmly, never listing what they haven't done,
  no closing offer), and EXAMPLES shows four short exchanges of tone,
  different from the corpus's own cases, on the conversation path only.
- **The phone:** the model kept its "Sure!" and "let me know", however it was
  asked, so `response_composer.polish` takes off only a filler opening and a
  last sentence that offers help. Lists and length stay.
- **Results** (37 cases each): glasses 37 of 37 within 25 words, median 18;
  every flag at 0 on both devices (phone was filler 2, closing offers 4); tool
  choice 213/213.
- **A bug found in my own check:** two new patterns had a control character
  where `` belonged, so they matched nothing; every run was rescored after
  the fix.
- **Ratings:** a 👍 and a 👎 under each answer on the phone and PC
  (`web/shell.js`), kept per person in `core/answer_ratings.py`, through the
  `answer.rate` action. A 👎 still reaches the Fix-It Log. The glasses' own
  rating comes with the relay's next change. These ratings are what a
  fine-tune would learn from later.

