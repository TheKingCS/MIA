# Universal Inspection, Self-Knowledge and Self-Development: Audit and Plan

*Claude, 2026-10-30, from two documents Zac asked to implement back to
back: "MIA — Universal Inspection System" and "MIA — Master Development
Handoff". Decisions: DEC-0056 (Universal Inspection, phases 1-2 built),
DEC-0057 (Self-Knowledge and Introspection, phase 1 built), DEC-0058
(Self-Development lab, PROPOSED: it conflicts with two approved
decisions, section 6).*

## 1. What the handoff got wrong about the repository

- **Decision numbers:** DEC-0047 is "How missions work" and DEC-0048 is
  "User Sync, and a design audit", not Self-Knowledge and
  Self-Development. The new ones are DEC-0056 to DEC-0058.
- **Where MIA runs (DEC-0015):** the new home computer is production
  today; the phone is second, the glasses third, the Raspberry Pi
  fourth ("eventually"). The handoff's "Pi is production, PC is the
  lab" is the later picture; until there's a Pi, production *is* this
  PC, so the lab must be isolated **on the same machine** (section 6).
- **The model:** the PC runs qwen2.5:14b (qwen3:14b measured, Zac's call),
  not llama3.2; the voice is Kokoro (DEC-0051), Piper the fallback; the
  phone's server and Tailscale are real; workout tracking is built
  (DEC-0055).
- **Self-modification is already staged** (`docs/ROADMAP.md`, "Self-
  Modification / Dev Mode"): 1 read and explain, 2 propose don't apply,
  3 sandboxed self-testing, 4 scoped autonomy. MIA is at stage 1, and
  DEC-0049 (tier 3) says "she never changes her own code". The handoff's
  "PROPOSE" autonomy is stages 2-3: it needs Zac to approve moving on.

## 2. The audit: what exists

| Area | What exists | Where |
|---|---|---|
| Her capabilities | the capability map from the code (apps, tools, where they run, limits) and "can you…?" | `core/capabilities.py` (DEC-0041) |
| Her design | her decisions, specs and docs, searched with the file each answer came from | `core/self_docs.py` |
| Her model | which model, size, quantization, where it runs, from the runtime itself | `core/model_registry.py` |
| Her health | CPU, RAM, disk, network, temperature (psutil); Diagnostics screen | `core/system_health.py`, `modules/diagnostics` |
| Her stumbles | the Fix-It Log: corrections, errors, slow answers, broken pages, ranked issues, a fix report | `core/failure_log.py` (DEC-0049) |
| Online or not | what works offline and what needs the internet | `core/connectivity.py` |
| Devices | attached storage and serial devices, eject | `core/device_framework.py`, Field Kit |
| Network | a TCP connect port scanner, subnet calculator, hash identifier, password strength | `core/port_scanner.py`, Field Kit |
| Sensors | the Data Logger (readings by series), The Lab (experiments, calibration) | `core/data_logger_manager.py`, `modules/lab` |
| Cameras | home cameras over the local network | `core/security_cams.py` (DEC-0033) |
| Reading text | OCR of photos and scans (Tesseract) | `core/ocr.py` |
| Photos from the phone | the phone's gallery bridge, the Memory Vault | `android-phone/.../Gallery.kt` |
| Usage | desktop app opens, web page opens (2026-10-30) | `core/usage_tracker.py` |
| Engine state | Life State v2, `/api/state`, life events, links | `core/context_assembler.py`, `core/links.py` |
| Benches | tool choice (213 cases), the Intelligence Benchmark (112) | `tools/pc_model_check.py`, `tools/intelligence_check.py` |

## 3. Every discovery method, honestly

Level: **passive** (reading what a device says about itself), **authorized**
(reading with permission given), **active** (probing; asked first,
rate-limited), **disruptive** (never without explicit approval).

| Method | Obtains | Needs | Available | Level | Limits | Cost |
|---|---|---|---|---|---|---|
| OS facts | OS, version, name, uptime | nothing | **yes, built** | passive | — | built |
| CPU and memory | cores, threads, RAM, load | psutil (installed) | **yes, built** | passive | — | built |
| Windows hardware query | full CPU, GPU, board, BIOS names | Windows (CIM) | **yes, built** | passive | GPU memory not reliable there (4 GB cap) | built |
| Drives | size, free, use | psutil | **yes, built** | passive | SMART health needs admin + a tool | built; SMART small |
| Network adapters | addresses, speed, ports offered | psutil | **yes, built** | passive | only this computer | built |
| Attached devices | storage, serial | device framework | **yes, built** (desktop) | passive | not cameras, keyboards, other USB | built; full USB list small |
| Firewall | on/off per profile | Windows (netsh) | **yes, built** | passive | BitLocker needs admin | built |
| AI runtime | model, size, quantization, GPU use | Ollama | **yes, built** | passive | — | built |
| MIA's code, decisions, capabilities, health | counts, waiting decisions, issues | the repo, the Fix-It Log | **yes, built** | passive | test results not recorded yet | built |
| Running processes, services | what's running | psutil | no | passive | command lines can hold secrets: names only | small |
| Installed software, drivers, updates | inventory, versions | Windows registry / winget | no | passive | slow on Windows | medium |
| Local network map | devices, names, makers | ARP table (passive), mDNS/SSDP (active) | no | passive / **active** | names often missing; makers from MAC prefixes | medium |
| Port scan of a device | open services | the port scanner | **yes** (Field Kit, Talk) | **active** | **limited to own network since 2026-10-30** | built |
| Router's device list | every device the router knows | the router's admin page or API | no | authorized | brand-specific, needs its password from the person | medium-large |
| Phone camera | photo of a label, board, screen | the phone app (explicit capture) | partly (photos into the Inbox/Vault) | authorized | a photo, not live video | medium |
| Glasses camera | what the person sees | Meta Device Access Toolkit (phone app) | **no** (web apps can't; DEC-0029/0030 phase F) | authorized | photo capture only, explicit | large, waits on Meta |
| Object / device recognition | what's in a photo | a vision model (e.g. a local multimodal model in Ollama) | **no** | passive (on a given photo) | small local vision models are rough; never stated as confirmed | medium |
| OCR of labels, serials | text on a label | Tesseract | **yes** (`core/ocr.py`, if installed) | passive | glare, small print | small to wire in |
| Research (datasheets, manuals) | specs for a found model | reference packs offline; the web needs DEC-0053 | partly (offline packs, the Inbox's manuals) | authorized | DEC-0053 not approved: no web lookup | medium |
| Audio (sounds, noises) | what's heard | the microphone, a classifier | **no** | authorized (people may be present) | — | large |
| Phone sensors (GPS, motion, light) | position, movement | the phone app | GPS yes (Places), others no | authorized | — | medium |
| Lab sensors (USB, GPIO) | readings | the Data Logger, a serial sensor | the store yes; live sensors no | authorized | needs hardware | medium |
| Electrical probing (UART, I2C, SPI) | a device's internals | adapters, safety checks | **no** | **disruptive** | risk to the device | large, explicit approval |

## 4. Universal Inspection: the architecture (built: phases 1-2)

`core/inspection.py`:
- **Evidence**: fact, value, method, source, observed time, confidence
  (CONFIRMED, HIGH, PROBABLE, POSSIBLE, UNKNOWN), recheck time, note.
  **Gaps**: what couldn't be determined and why (never "doesn't exist").
- **Methods** (`METHODS`): the registry above, each with the subjects it
  applies to, what it obtains, what it needs, an `available()` check and
  its level. Only passive methods run unasked; the rest are listed as
  "asked first".
- **Correlation**: two methods agreeing make a fact CONFIRMED (with
  "agreed by"); a disagreement keeps both and is listed as a
  contradiction, never silently resolved.
- **Problems**: a full drive, memory pressure, a firewall off, decisions
  waiting.
- **Reports**: a spoken summary, the full sectioned report (each fact
  with confidence and source; UNKNOWN and NOT RUN sections), kept in
  `data/inspections/` (the latest 20 per subject) so follow-ups build on
  them; stale facts are noticed.
- **Asking**: "inspect this computer", "inspect yourself", "run a
  self-check", "the full inspection report" (`get_inspection`, answered
  by code). A follow-up ("can it run a bigger model?") goes to the model
  with the report in the conversation.

**Next phases** (each its own increment, nothing claimed before built):
3 running services and installed software; 4 the local network map
(passive ARP first, active discovery asked); 5 photos: OCR of a label,
then a local vision model, every visual identification at most PROBABLE
until something else agrees; 6 research (offline packs now, the web
with DEC-0053); 7 the knowledge graph across inspections (devices,
components, models, relations, by `kind:id` like `core/links.py`) and
change detection; then audio and sensors.

## 5. Self-Knowledge and Introspection (DEC-0057; phase 1 built)

**One rule:** self-knowledge is *derived* from the system, never a
hand-written description that drifts. The manifest is the `mia`
inspection subject plus what already exists:

| The handoff asks for | Where it comes from |
|---|---|
| system manifest, hardware, software | `inspect(context, "this_computer")` and `"mia"` |
| module registry, dependency graph | the code (`ast`; built: counts; next: imports between core modules, who uses what) |
| capability registry, statuses | `core/capabilities.py`; **next**: a status per capability: implemented / partial (its LIMITS entry) / planned (ROADMAP, never claimed) / unavailable here (e.g. desktop-only on the phone) / malfunctioning (the Fix-It Log's open issues for its tools) |
| service health | `core/system_health.py`, the AI runtime, the phone link, connectivity |
| known issues | the Fix-It Log (ranked issues) and `docs/KNOWN_ISSUES.md` |
| decisions, history | `docs/DECISIONS.md` (waiting decisions surfaced), git history |
| "how do you handle memory?" | `core/self_docs.py` (the docs) and, next, code retrieval (DEC-0043 step 4) |

**Introspection** (next): a weekly self-check through the communication
gate: inspect `mia`, compare with last week (new problems, stale facts,
a decision waiting, issues rising), and say what changed and why it
matters; verified vs inferred kept apart. Also the test suite's last
result recorded when it runs, so "do your tests pass?" is answerable.

## 6. Self-Development (DEC-0058, PROPOSED)

**The conflicts first:** DEC-0049 tier 3 says MIA never changes her own
code; the ROADMAP stages it (she's at stage 1). The handoff asks for
stages 2-3 under a PROPOSE boundary. And there's no Pi yet, so the lab
and production share this PC.

**The proposal, if Zac approves:**

1. **The lab is a separate copy, not the running MIA:** a git worktree
   (`lab/`, outside the running install's folder) on its own branch,
   with **its own data folder of made-up data** (no real records, no
   `config/config.json`, no vault, no Plaid or mail credentials, no
   phone tokens). Production keeps running from the main checkout,
   untouched.
2. **Who writes the code:** MIA proposes *what* (from the Fix-It Log,
   introspection and the benchmark: the problem, the evidence, the
   modules involved, the plan); the code is written either by her local
   model (a 14b writes small, contained changes at best) or by Claude
   Code running headless in the lab under the same rules. Recommended:
   Claude Code writes, MIA proposes and checks; it's what can actually
   produce code that passes this suite.
3. **Every change proves itself in the lab:** a failing test first (the
   Fix-It Log's tier 3 rule), then the change, then the full suite, the
   tool-choice bench and the Intelligence Benchmark, plus simulations
   (the phone link down, the model missing, a sensor absent) as tests.
   Hardware checks are marked as simulated unless done on the device.
4. **A proposal** is a branch plus a report (problem, evidence, diff,
   test and bench results, risks, rollback), shown in MIA (a new
   "Proposals" view in the Fix-It Log) and sent to Zac. **Nothing reaches
   production without his approval**; deploying is a git merge on the
   main checkout, then the suite again, then a restart; `git revert` is
   the rollback.
5. **She can't remove her own safeguards:** the lab's change checker
   refuses any diff that touches the protected list (the lab runner
   itself, `core/actions.py`'s approval path, the safety floor,
   child-account rules, credentials handling, `deploy/`, this list),
   and the list lives in the main checkout, which the lab can't write.
   Network in the lab: off except the package index, when allowed.
6. **Self-knowledge updates** after a merge (the next `mia` inspection).

**Zac's questions (DEC-0058):** move to stages 2-3 (MIA proposes and
tests in an isolated lab; tier 3's "never changes her own code" becomes
"never changes production without your approval")? The lab on this PC
until there's a Pi? Claude Code as the lab's coder, or her local model?

## 7. The rest of the handoff, mapped

| Handoff part | State |
|---|---|
| Part 5, workout | built: DEC-0055 phases 1-2 (`docs/ACTIVE_TRAINING_PLAN.md`) |
| Part 6, interface and glasses | the look is DEC-0023; the layout DEC-0045; the brief for the whole experience, glasses modes included, is `docs/design/CLAUDE_DESIGN_PROMPT.md`; context-aware glasses modes (workout, navigation, mission, notification, assistant) are the brief's job, then built |
| Part 7, onboarding | DEC-0050 (User Sync defaults), `docs/GLASSES_FIRST_BOOT_PLAN.md`, the cinematic first boot exists (`web/` first start); switching the active person exists (profiles, `view_for`) |
| Part 8, existing context | verified above (section 1) |

## 8. Order

1. **Built today:** inspection core, this computer, MIA herself; scans
   limited to the own network.
2. Capability statuses and the weekly self-check (DEC-0057 next).
3. Inspection phase 3 (services, software) and 4 (network map, passive).
4. Photos: OCR of labels, then a local vision model.
5. DEC-0058, if approved: the lab, then the first proposal from a real
   Fix-It Log issue, end to end.
