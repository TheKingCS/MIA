# MIA Homestead — Offline Assistant Plan

## Why this exists

`SAFETY_SPEC.md`'s entire premise is that the control loop survives without
a human, without the network, without the Pi even being trustworthy. But
`assistant/greenhouse_assistant.py` — the thing meant to be the single
conversational interface to everything this system does — currently hard-
requires `anthropic.Anthropic()` and `ANTHROPIC_API_KEY`, with zero offline
fallback. That's a real contradiction: the one surface built to explain a
self-sufficient system is the least self-sufficient thing in the codebase.

**Decision (2026-08-26): any reliance on an outside/cloud service defeats
the actual point of this being self-sufficient.** The assistant must run on
a fully local model. This is not a cost optimization or a "nice to have
someday" — it's the same design principle as the two-tier Pi/MCU safety
architecture, applied one layer up.

## This is not a blank-slate problem — reuse the sibling project's scars

MIA Homestead's sibling project (M.I.A., the Pi5 kiosk assistant at
`~/Projects/MIA`) already made this exact transition: cloud-shaped
assumptions → a real local Ollama-backed tool-calling assistant, running on
comparable Pi-class hardware. Several of its hard-won lessons transfer
directly and should NOT be relearned the expensive way here.

### 1. Tool count is not free on a local model — and this project is already past the danger line

MIA Homestead's `TOOLS` list has **54 entries, and `ask()` attaches every
single one to every single message, unconditionally** — no gating exists
today. That's fine against a large cloud model. It is measurably not fine
against a small local model: M.I.A. hit real, reproducible cross-schema
tool-calling failures (hallucinated nonexistent tool names, wrong tool
picked) once its own registry crossed roughly 35-40 tools on `llama3.2:3b`,
diagnosed via direct bisection against the model backend. MIA Homestead is
already past that threshold before it's been run against a local model even
once.

**Fix: domain-scoped tool attachment**, mirroring M.I.A.'s
`AssistantAction.trigger_phrases` / `gating_keywords()` pattern. Every tool
gets tagged with a domain; a cheap deterministic keyword classifier (NOT an
LLM call) decides which domain(s) the incoming message touches, and only
that subset (+ a small always-on core) gets attached. MIA Homestead's tools
already cluster naturally — see "Proposed domains" below, this is mostly
categorization work on what exists, not a redesign.

Unlike M.I.A.'s mostly single-domain action requests, MIA Homestead's
questions are often multi-domain ("what's low on stock and what needs
maintenance" spans two domains in one message) — the classifier should
attach the **union** of matched domains, not force a single winner.

### 2. Bundled destructive tool calls are a real local-model failure mode, not a hypothetical

While benchmarking a larger local model, M.I.A. found it would sometimes
return TWO tool calls in one reply — a legitimate read plus a spurious
*destructive* write the user never asked for — something the cloud model
it replaced had never done. MIA Homestead's write tools are already well-
designed defensively (exact-match lookups, fail-closed), but nothing stops
a bundled spurious call from executing today.

**Fix, before local rollout**: an equivalent of M.I.A.'s
`split_safe_tool_calls()` — a reply bundling 2+ tool calls skips any
destructive ones and asks the user to confirm explicitly; a single call
always executes (the normal case). See Sequencing step 3 below for the
final, implemented `DESTRUCTIVE_TOOLS` list — done as of 2026-08-26.

### 3. Determinism and latency settings, already proven correct

- `temperature: 0` by default — M.I.A. found the same prompt gave different
  answers across calls otherwise. Note even at 0, CPU floating-point
  non-determinism means occasional variance is expected, not a new bug.
- `keep_alive: -1` on every request — Ollama's default 5-minute idle unload
  otherwise reads as "the assistant is slow" when it's actually a cold
  reload. This matters even more here: the assistant should feel as
  available as the control loop it's reporting on.

### 4. Don't assume a bigger local model is a better one

M.I.A. benchmarked `llama3.2:3b` against `qwen2.5:7b` and `mistral:7b` on a
60-case golden set on comparable Pi-class hardware: **60/60 at 2.69s/case
vs 58/60 at 12.01s/case vs 17/60 at 18.75s/case.** The smallest model won
outright on both accuracy and speed. Re-run the same style of bake-off
against MIA Homestead's own tool set once real hardware exists — don't
default to "biggest model that fits" as the assumption.

### 5. Build the golden-set regression harness before, not after

`scenarios/scenarios.py` proves the control loop's safety behavior.
Nothing today proves the assistant's tool-calling accuracy the way M.I.A.'s
`tests/live_model_check.py` does. Build `assistant/live_model_check.py`
(or similar) alongside the local-model conversion, seeded with real
questions per domain — every trigger-phrase/gating change in M.I.A.'s
history was verified against a live model, never guessed at, because
several "obviously safe" phrasings turned out to have real collision risk
only visible against actual model behavior.

## Compute target: Pi 5 + AI HAT (same class as MIA Home) — with an honest caveat

The greenhouse Pi is expected to have the same Hailo-10H NPU-equipped
hardware as MIA Home. That's real potential headroom over CPU-only
inference — but **don't gate this plan on it being available soon.**
As of M.I.A.'s own hardware bring-up (2026-07-17/18), the Hailo chip was
detected on the PCIe bus but **no `/dev/hailo*` device node existed yet —
the driver/runtime was never actually installed**, and that work was
paused, not completed. Separately, Hailo-accelerated LLM inference is not
a drop-in Ollama backend (Ollama's backends are CPU/CUDA/Metal/ROCm via
llama.cpp) — it needs Hailo's own Dataflow Compiler/HailoRT toolchain and
model conversion, a meaningfully bigger and more specialized lift than
"install Ollama," and not yet proven working on *either* project's hardware.

**Recommendation: build against the known-good path first.** Stand up the
exact same CPU-based Ollama + `llama3.2:3b` pattern M.I.A. already validated
end-to-end. Treat Hailo-accelerated inference as a shared stretch upgrade
for both projects once M.I.A.'s own Hailo bring-up actually completes and
produces a real, reusable pattern — solving Hailo LLM acceleration once,
not twice, independently, on unproven ground.

## Tool domains — DONE (2026-08-26)

`assistant/greenhouse_assistant.py` now has a `TOOL_DOMAINS: dict[str, str]`
mapping right after `TOOLS`, kept as a separate pure-data structure (never
merged into the tool dicts themselves, so the Anthropic tool schema those
are validated against is untouched — zero behavior change from this step
alone). `core/self_audit.py` gained a 6th check enforcing the mapping can
never silently drift from `TOOLS` as tools are added/renamed/removed.

13 domains. Table below is as of the tool count settling at **55** (one
more was added mid-step, `send_greenhouse_report` — see the "done" note
under Sequencing step 2):

| Domain | Count | Tools |
|---|---|---|
| `status` (always-on) | 8 | get_current_status, get_open_alerts, get_power_status, get_deadmans_switch_status, get_greenhouse_report, send_greenhouse_report, record_human_checkin, get_last_human_checkin |
| `yield_planting` | 8 | get_yield_summary, get_expected_vs_actual_yield, get_water_usage, get_bed_plantings, record_planting, mark_planting_harvested, mark_planting_failed, record_water_usage |
| `experiments` | 7 | propose_experiment, start_experiment, get_active_experiments, complete_experiment_now, get_pending_parameter_changes, approve_parameter_change, deny_parameter_change |
| `inventory` | 6 | get_inventory_status, get_low_stock_items, get_to_order_list, approve_order, deny_order, get_consumable_forecast |
| `self_knowledge` (always-on) | 5 | get_system_capabilities, get_self_change_history, get_verification_coverage, get_recent_automated_actions, get_hardware_needs_list |
| `maintenance` | 4 | get_open_maintenance_tasks, create_maintenance_task, update_maintenance_task_status, assign_maintenance_task |
| `species` | 3 | get_species_profile, list_species, add_species |
| `infrastructure` | 3 | get_wiring_info, get_plumbing_info, diagnose_alert |
| `devices` | 3 | get_unpaired_devices, get_device_setup_instructions, pair_device |
| `backups` | 3 | create_config_snapshot, list_config_snapshots, restore_config_snapshot |
| `dosing` | 2 | get_dosing_history, get_dosing_rationale |
| `help_requests` | 2 | get_active_help_requests, acknowledge_help_request |
| `revenue` | 1 | get_revenue_summary |

`status` and `self_knowledge` are cheap and broadly relevant — marked
always-on (`ALWAYS_ON_DOMAINS` in the code) rather than gated, same as
M.I.A.'s always-on tools. Everything else attaches only when the message's
keywords match — gating is live now, see Sequencing step 2.

## Sequencing (planning phase — no hardware purchase yet)

Software prep that can happen now, independent of buying anything:

1. ~~Tag each `TOOLS` entry with a `domain`~~ — **done**, see above.
2. ~~Build the keyword-gating classifier + wire it into `ask()`~~ — **done**
   (2026-08-26). `relevant_domains()`/`tools_for_domains()` in
   `assistant/greenhouse_assistant.py`, gated once per user turn from the
   message that started it (not re-evaluated per tool-calling round-trip
   within a turn). Fails open exactly as specced: if only the always-on
   domains match, the FULL tool list is attached rather than a narrowed
   one. Verified against 15 realistic questions — clean single/multi-domain
   matches narrowed to 15-24 tools (from 55) for anything with clear
   keyword signal, safe fallback to all 55 for genuinely ambiguous ones.
   **Two real side-findings from re-running self_audit.py during this
   step**, worth recording since they're the exact kind of thing this
   project's own audit discipline exists to catch:
   - The keyword dict's vocabulary ("ph down", "nutrient", etc.)
     accidentally satisfied `check_conversational_coverage()`'s old
     whole-file text scan, hiding the two real (intentional, documented)
     dosing-pulse exceptions. Fixed by scanning only the actual `TOOLS`
     name+description text instead of the whole file — more correct
     regardless of this incident, not just a patch.
   - That same fix then surfaced a genuine, previously-hidden gap:
     `report_generator`'s `generate_and_send()` had no assistant tool —
     `get_greenhouse_report` only ever displayed the report, never
     dispatched it. Added `send_greenhouse_report`, honest in its return
     value about whether a notifier was actually configured (no silent
     "sent" claim when nothing was).
3. ~~Build `split_safe_tool_calls()` equivalent~~ — **done** (2026-08-26).
   `DESTRUCTIVE_TOOLS: set[str]` (9 tools) + `split_safe_tool_calls()` in
   `assistant/greenhouse_assistant.py`, wired into `ask()`'s tool-dispatch
   loop: a lone destructive call always executes (the normal case); a
   reply bundling 2+ calls where any is destructive skips every
   destructive one, logs it, and feeds the model a tool_result explaining
   why so it can tell the user honestly rather than silently doing
   nothing. `core/self_audit.py` gained a 7th check verifying every
   `DESTRUCTIVE_TOOLS` entry matches a real tool name. Functionally tested
   against 5 cases including the exact bundled-read-plus-spurious-write
   failure mode M.I.A. observed on a local model — all passed. The
   original draft list above (in the "why this exists" section) was
   missing one real case caught during implementation: `start_experiment`
   changes a cell's live dosing target immediately, per its own tool
   description — same risk class as `approve_parameter_change`, added
   alongside it. Final list: `approve_order`, `deny_order`,
   `restore_config_snapshot`, `start_experiment`,
   `approve_parameter_change`, `deny_parameter_change`,
   `acknowledge_help_request`, `pair_device`, `mark_planting_failed`.
4. ~~Stand up local Ollama + `llama3.2:3b` against this same tool set~~ —
   **done** (2026-08-26). Ollama was already running in this dev
   environment with `llama3.2:latest`, `qwen2.5:7b`, and `mistral:7b` all
   pulled and tool-capable — zero setup needed. Originally built as its
   own file, `assistant/ollama_backend.py`, with `OllamaGreenhouseAssistant`
   SUBCLASSING `GreenhouseAssistant` rather than reimplementing it —
   inherited all 55 `_tool_*` handlers, `_dispatch_tool`, and
   `_system_prompt` unchanged; only `__init__` (no anthropic client) and
   `ask()` (Ollama's chat protocol instead of Anthropic's) were
   overridden. **Superseded by step 6's restructuring**: that file no
   longer exists — its content moved into `greenhouse_assistant.py`
   itself as the new default `GreenhouseAssistant`, see step 6 below for
   the real final architecture (`_BaseGreenhouseAssistant` holding
   everything shared, with `GreenhouseAssistant` and
   `AnthropicGreenhouseAssistant` as thin sibling subclasses, not a
   subclass-of-a-subclass). Not yet the default at the time step 4 was
   written — that's what step 6 changed.

   **Two real bugs found via live-model testing, both fixed — exactly the
   "expect several rounds of real-model iteration, one pass is not
   enough" pattern this project's own history already establishes:**

   - **The step-2 "fail open, attach everything" fallback was empirically
     wrong.** "How is everything looking?" (matches only always-on
     domains → old fallback = full 55 tools) made `llama3.2:3b` stop
     calling tools entirely and narrate about its own schema instead —
     reproduced, then isolated by testing 55-tools/full-prompt,
     13-tools/full-prompt, and 55-tools/minimal-prompt independently: only
     the full combination broke it. `qwen2.5:7b` handled the identical
     55-tool/full-prompt payload fine and picked an excellent tool. So
     this is a real `llama3.2:3b` capacity limit at this tool count, not
     a bad payload, and it's a *worse* failure than the bounded miss the
     original fallback was designed to avoid. Fixed: `tools_for_domains()`
     now falls back to just the always-on domains' tools, not the full
     list. This is a **shared fix affecting the currently-live Claude
     cloud path too**, not just this new local one — an intentional,
     evidence-based tightening, not an oversight.
   - **A real grounding failure, more serious than the above.** With
     `sensor_readings` genuinely empty (fresh setup, matching this
     project's actual current state), `get_current_status` correctly
     returned `{"readings": []}` — but `llama3.2:3b` then fabricated
     specific numbers (pH 6.9, EC 740, battery 68%) **verbatim matching
     `PERSONALITY.md`'s own example exchange text**, instead of saying no
     data existed. A direct, real violation of this project's central
     grounding rule. Root cause: nothing told the model those examples
     were off-limits as a data source. Fixed at the time with a shared,
     model-agnostic strengthening of `_system_prompt()`'s grounding
     instruction. **Correction, found by step 5's golden-set harness**:
     that fix was NOT actually reliable — it only appeared to pass this
     step's 2 manual re-tests because they happened to run against the
     real dev DB, which had `system_capabilities` populated from an
     earlier `main.py` run (see step 5 below for the full story: the
     golden set's fresh, isolated test DB has an empty capabilities table
     by design, and against that exact same fix + question, the
     fabrication reproduced 100% of the time, word-for-word identical).
     The "5/5 real end-to-end questions correct" claim below is therefore
     narrower than it reads — it was 5/5 against ONE specific DB state,
     not 5/5 against the class of states that matter. Real fix landed in
     step 5.

   **Not tested live**: a model spontaneously bundling a destructive call
   with a safe one (step 3's actual defense target) — M.I.A.'s own history
   notes this was found incidentally during broader testing on a *larger*
   local model, not reliably reproducible on demand. `split_safe_tool_calls()`
   itself is already verified correct via direct unit-style testing (step 3,
   5 cases including this exact shape) — that logic doesn't depend on
   reproducing the trigger live to trust it.
5. ~~Build the golden-set regression script~~ — **done** (2026-08-26),
   `assistant/live_model_check.py`, 16 cases across all 13 domains. Every
   case runs against a fresh, isolated temp-file DB (never the real
   `mia_homestead.db`), grading on whether at least one expected tool was
   called (proves grounding happened at all) and, for the fabrication
   regression case, that none of a set of forbidden substrings appear in
   the final answer. **First run: 15/16, and 2 of the "passes" were
   actually further instances of the same class of bug this whole step
   was built to catch** — this step earned its keep immediately:

   - **The step-4 fabrication fix was NOT actually reliable** — the one
     manual case built into the harness with `base_ticks=0` (genuinely
     empty `sensor_readings`) reproduced the exact bug 100% of the time,
     word-for-word identical answer every run. Root-caused by comparing
     against the real dev DB (still worked there) vs. the harness's fresh
     DB (failed there): the only real difference was whether
     `system_capabilities` happened to be populated — meaning the step-4
     fix was accidentally dependent on unrelated system-prompt content,
     not actually robust. **Real fix, more structural than the step-4
     attempt**: `_dispatch_tool()` gained `_annotate_if_empty()` — a
     single, centralized check applied to every tool result (not a
     system-prompt clause, and not a per-tool special case) that injects
     an explicit in-band "no data, don't invent anything" note whenever
     every list-valued field in a result comes back empty. This was
     needed because the SAME fabrication pattern reproduced on a SECOND,
     different tool (`get_dosing_rationale`, in the
     `dosing_infrastructure_multi_domain` case) — proving a per-tool
     patch strategy doesn't scale to 55 tools; a shared mechanism at the
     one place every tool result already passes through does.
   - **`species_lettuce_ph` failed for a real reason**: "What pH does
     lettuce want?" matched no gated domain at all (no literal word
     "species" in the question), so `get_species_profile`/`list_species`
     were never even offered to the model — not a model failure, a
     keyword coverage gap in step 2's `DOMAIN_TRIGGER_KEYWORDS`. Fixed by
     adding the three baseline species names as keywords. Documented,
     deliberately-not-fixed-further limitation: a species added later via
     `add_species` won't auto-gate its own name until this list is
     updated by hand — the real fix is querying `species_profiles` at
     gating time instead of a static list, left as a known gap rather
     than solved here.
   - **`infrastructure_wiring`'s wrong-sounding answer was NOT a
     hallucination** — closest look yet at "is the model lying or is the
     data wrong": the model called `get_wiring_info(actuator_name='pH-up
     pump')`, got back a correctly-honest `{"wiring": null}`, and honestly
     reported "not wired" based on that. The real bug was
     `InfrastructureRegistry.get_wiring_for_actuator()`/
     `get_plumbing_for_actuator()` doing an exact-string match against
     the internal `ph_up_pump` name, with nothing telling the model what
     exact format to use — a natural-language guess like "pH-up pump"
     silently failed to match. Fixed with `_normalize_actuator_name()`
     (case/punctuation-insensitive comparison) in both lookup methods —
     a real correctness fix affecting the currently-live Claude path too,
     not a local-model-only patch.

   **Final clean run: 16/16 passed**, all answers read as honestly
   grounded (no further matches to PERSONALITY.md's example text, correct
   real data cited where it existed, plain honest "no data" where it
   didn't). Re-verify this stays true any time a new tool is added or an
   existing one's return shape changes — that's exactly what this script
   is for; `core/self_audit.py` intentionally does NOT run it
   automatically (it needs a live Ollama model + real round-trip time,
   unlike the six fast structural checks self_audit already runs).
6. ~~Swap `greenhouse_assistant.py`'s client from `anthropic.Anthropic()`
   to the local Ollama client~~ — **done** (2026-08-26). This was the
   first step in this whole plan that changes live default behavior
   rather than just adding new, inert-until-wired-in code — everything
   in steps 1-5 was additive. Real architecture landed:
   - `_BaseGreenhouseAssistant` — holds all shared state (`db`,
     `personality`, `history`) and every one of the 55 `_tool_*`
     handlers, `_dispatch_tool`, `_annotate_if_empty`, `_system_prompt`.
     No model client, no `ask()` — those are the only two things that
     differ by backend.
   - `GreenhouseAssistant(_BaseGreenhouseAssistant)` — **the new
     default.** Local-model-backed via Ollama, same content that used to
     live in the separate `ollama_backend.py` file (now deleted, merged
     in). `python assistant/greenhouse_assistant.py` with no flags now
     gives you this — no API key, no internet dependency.
   - `AnthropicGreenhouseAssistant(_BaseGreenhouseAssistant)` — the cloud
     path, kept as an explicit opt-in (`python
     assistant/greenhouse_assistant.py --cloud`) for re-running the
     local-vs-cloud bake-off, not removed. Both are SIBLING subclasses of
     the shared base, not one subclassing the other — avoids the
     semantic oddity of "the local backend IS-A cloud backend."
   - `assistant/live_model_check.py`'s import updated
     (`OllamaGreenhouseAssistant` → `GreenhouseAssistant`, now imported
     from `greenhouse_assistant.py` directly) and re-run clean — see
     result below.
   - **A real remaining self-sufficiency gap found and fixed while doing
     this**: `import anthropic` was still unconditional at module level,
     meaning even the new local-default `GreenhouseAssistant` couldn't be
     *imported* without the cloud SDK installed — a real contradiction of
     the whole point of this step. Fixed: the import moved to be lazy,
     inside `AnthropicGreenhouseAssistant.__init__` only. `anthropic` is
     now commented out of `requirements.txt` (the default path needs
     nothing beyond `pyyaml`), with a note on how to get it back for the
     `--cloud` path.
   - `README.md`'s "Running the assistant" section updated: local-default
     instructions first, cloud instructions clearly marked as the
     explicit-opt-in `--cloud` path.
   - Verified, not assumed: `self_audit.py` still 7/7 clean;
     `GreenhouseAssistant(db_path=...)` constructs with no `api_key` and
     answered a real question correctly end-to-end;
     `AnthropicGreenhouseAssistant` still constructs and inherits all 55
     tool handlers; full module imports cleanly with zero references to
     `anthropic` anywhere except the one lazy import site; **full 16-case
     golden set re-run against the fully restructured code: 16/16
     passed**, confirming the class reorganization (moving all logic from
     the separate `ollama_backend.py` into `_BaseGreenhouseAssistant` +
     `GreenhouseAssistant` inside `greenhouse_assistant.py` itself) didn't
     regress anything found and fixed in steps 4-5.
   `PERSONALITY.md` itself: unchanged, exactly as planned — the grounding
   requirements it defines are genuinely model-agnostic, and nothing
   about this restructuring needed to touch it.
7. Once real Pi+AI HAT hardware exists: re-run the model bake-off on the
   real target hardware before assuming `llama3.2:3b` is still the right
   choice there specifically.

## Open questions still unresolved

- Should notification delivery (email/SMS) be held to the same
  self-sufficiency standard, or is that a different question — alerting an
  off-site human inherently needs *some* network path, which is not the
  same category of dependency as "the assistant's own reasoning requires a
  remote AI provider to think at all"? Current lean: these are different
  concerns; SMTP/SMS reaching a human off-site is fine to depend on
  connectivity, the assistant's core reasoning is not.
- ~~Whether the local model should ever call out to a cloud model as a
  fallback/upgrade path when connectivity happens to be available~~ —
  **resolved 2026-08-31**: yes, as a human-triggered, explicit-opt-in
  escape hatch only — never automatic, never something the local
  model's own reasoning decides to reach for. Built as
  `GreenhouseAssistant.ask_with_cloud_escalation()`
  (`assistant/greenhouse_assistant.py`), which constructs a fresh, short
  `AnthropicGreenhouseAssistant` conversation (same db, no shared
  history with the ongoing local session) for just that one question.
  The REPL exposes it via a `/cloud <question>` prefix. Fails honestly
  (no silent local fallback) if `ANTHROPIC_API_KEY` isn't set or the
  API call itself fails — verified both paths live: a missing key
  returns a plain "NOT answered by the cloud model" message, and an
  invalid key surfaces the real 401 from Anthropic's API, neither one
  silently substituting a local answer. Confirms the local path is
  untouched by this: re-ran a real question against the local Ollama
  backend after this change and it answered correctly, grounded in real
  data, same as before.
