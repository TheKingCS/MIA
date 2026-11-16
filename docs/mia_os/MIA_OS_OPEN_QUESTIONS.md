# MIA OS open questions

*Central register. Each question has an owner (Zac, a check on the PC,
or the prompt that will answer it). It replaces
`preliminary/MIA_OS_OPEN_QUESTIONS_FIRST_PASS.md`, whose questions are
folded in here.*

## Answered 2026-11-15

- **Q-01:** for Zac, perhaps close friends later (DEC-0159).
- **Q-02:** retire it (DEC-0160).
- **Q-03:** LEP handoff given (DEC-0161).
- **Q-04:** Smart Closet: inventory, outfits, ratings, previews, and more (DEC-0162).
- **Q-05:** Zac and his wife may talk at once, and MIA must tell who (DEC-0163).
- **Q-06:** logged (DEC-0159).
- **Q-07:** fix it (DEC-0160; done once the secrets are added).

## Still open for Zac

| ID | Question | Why | Needed by |
|---|---|---|---|
| Q-08 | May MIA go online in the background for LEP's event discovery, and from which kinds of source? Suggestion: a short list of approved sources, once a day, with nothing personal sent | first routine background online use | building LEP discovery |
| Q-09 | Are each partner's LEP interests private to them, with a shared couple's profile both can see? (suggested default: yes) | privacy between the two accounts | building LEP profiles |
| Q-10 | Should "Send to MIA" start on the phone (the text-selection menu) before MIA OS? | now part of the UAL (Q-11) | — |
| Q-11 | **Answered yes (2026-11-15)**: U1–U3 now | DEC-0165 | — |
| Q-12 | **Answered B + C (2026-11-15)**: web search on research/verify; outside AI only after showing what is sent and getting a yes | DEC-0165 | — |
| Q-13 | **Answered yes (2026-11-15)**: taught skills plus lab-built skills with Zac's approval, one skills system | DEC-0123, DEC-0167 | — |
| Q-14 | **Answered (2026-11-15)**: system-wide, every app, file and piece of code; layered capture (selection, accessibility, files, terminal, OCR on request) | DEC-0165 | — |
| Q-16 | **Answered yes (2026-11-15)**: World Intelligence approved | DEC-0170 | — |
| Q-17 | **Answered (2026-11-15)**: Marketplace, Craigslist, eBay and similar are read by skills Zac demonstrates (public information, his own steps) | DEC-0171 | — |
| Q-18 | **Partly answered**: Claude checked the starting sources (proposal 5b) and a source loop keeps improving them; Zac: add or drop an area? the free keys are **skipped for now** (Zac, 2026-11-15); auctions, home stores, import marketplaces and grocery stores added | the first adapters | — |
| Q-19 | **Answered (2026-11-15)**: no fixed limit on her own messages; pacing learned from what Zac engages with; about four finds a day to start | DEC-0171 | — |
| Q-20 | **Answered (2026-11-15)**: within 360 miles of the home place (kept in his own data, never in the repo), nearer scoring higher, each trip's cost counted | DEC-0171 | — |
| Q-21 | **Answered yes (2026-11-15)**: procurement approved | DEC-0172 | — |
| Q-22 | **Answered (2026-11-15)**: his own figures, learned from fill-ups and miles driven (phone now, his vehicle's OBD-II later) | DEC-0171 | — |
| Q-23 | **Answered (2026-11-15)**: Kroger, Walmart, the dollar stores and three local stores (named in his own data) | DEC-0171 | — |
| Q-24 | **Answered yes (2026-11-15)**: the Living System doctrine adopted | DEC-0173 | — |
| Q-25 | **Answered (2026-11-15)**: Fable reviews all Opus work; Copilot, Claude, ChatGPT and Muse as independent checkers where it fits, not for everything; no Codex | DEC-0174 | — |
| Q-26 | **Answered yes (2026-11-15)**: she slows herself down and says so | DEC-0173 | — |
| Q-27 | **Answered yes (2026-11-15)**: no app marketplace; "the only marketplaces will be the ones i shop from" | DEC-0177 | — |
| Q-28 | **Answered yes (2026-11-15)**: the sandboxed extension proof of concept, once grants exist | DEC-0176 | — |
| Q-29 | **Answered (2026-11-15)**: DEC-0175 approved as prompt 22's direction, DEC-0176 yes, DEC-0177 approved with Zac's clarification | — | — |
| Q-30 | **Answered yes (2026-11-15)**: manifests as JSON in `apps/<id>/manifest.json`, a registry that reads them, code moved app by app later; M1 built | DEC-0178 | — |
| Q-15 | **Answered (2026-11-15)**: Raspberry Pi OS on the Pi, Fedora on the PC, the app on stock Android. Was: the Pi 5's base system: Raspberry Pi OS (Debian 13, the AI HAT+ 2's official drivers, sound works) or Fedora (Pi 5 support is a working minimum in Fedora 44/45, no sound yet)? The PC stays Fedora bootc unless one base for both is wanted | DEC-0168, DEC-0157 | Zac |
| Q-32 | What MIA OS is (DEC-0179): a personal, AI-native operating environment on a standard Linux image, one node of a distributed personal intelligence | settles the identity for Prompts 05 to 17 | Prompt 05 |
| Q-33 | How requirements are judged (DEC-0180): MoSCoW plus a release tier; when principles conflict, authority and safety, then security and privacy, then reliability, then local-first, then attention, then maintainability | the decision rule every later prompt uses | Prompt 05 |
| Q-34 | Autonomy (DEC-0181): keep the five tiers built in M4; add whether each action can be undone and what it reaches; add one "MIA, stop" | finishes the autonomy model | Prompt 08 |
| Q-35 | The first MIA OS (DEC-0182): the scope in `MIA_OS_MVP_DEFINITION.md` §2 | what Prompt 16 plans first | Prompt 16 |
| Q-36 | Prompt 02's multi-user list (two speakers, a couples' profile, a household display) predates DEC-0119 ("for Zac alone"): mark those not planned, keeping only "each account's data stays its own"? | consistency with DEC-0119 | Prompt 13 |

## The original questions (for the record)

| ID | Question | Why it matters | Needed by |
|---|---|---|---|
| Q-01 | Who is MIA OS for: Zac alone (DEC-0119), or others later (DEC-0050, DEC-0127)? | signed public images, licensing, installer, multi-user scope | Prompt 04 |
| Q-02 | Should the older Companion app (`android/`) be retired in favour of `android-phone/`? | two apps to maintain (R-03) | Prompt 02 |
| Q-03 | What is the Life Enrichment Protocol? Prompt 02 describes discovering activities (parks, cafés, events, budget-aware) | no code exists; needs a definition | Prompt 02 |
| Q-04 | What should Smart Closet do, and does it involve a camera? | no code exists | Prompt 02 |
| Q-05 | Shared Conversation: who joins (Zac and a guest, the household)? DEC-0119 says MIA is for Zac alone | conflicts with DEC-0119; needs speaker identification | Prompt 02 |
| Q-06 | Log the five established decisions (E1–E5) as DEC-0159? | the record | now |
| Q-07 | The private security finding of 2026-11-15: fix now? | open weakness | now |

## To check on the PC (a PC session)

| ID | Check |
|---|---|
| P-01 | `git status` in `C:\Users\zacrh\MIA` for edits left uncommitted by the deleted PC session |
| P-02 | Ollama on the RX 7900 XTX: model, speed; later the same under Linux (ROCm or Vulkan) |
| P-03 | Whether TPM2 is enabled in the firmware, and the drive layout and free space |
| P-04 | Run `tests/live_model_check.py` (the person cases) on the 14b for repetition and dead ends |
| P-05 | The installed Python package versions, compared with this audit's |

## For later prompts

| ID | Question | Prompt |
|---|---|---|
| T-01 | Semantic memory retrieval (embeddings) or stay with keywords? | 07 |
| T-02 | Runtime IPC: the API and SSE are enough, or D-Bus or a local socket too? | 05 |
| T-03 | A schema and versioning per store | 05/15 |
| T-04 | Device identity (certificates, revocation) | 12/13 |
| Q-31 | **Answered yes (2026-11-15)**: the grant check is on. MIA's own initiative: reads and drafts just happen; a change to his records only within a grant (a learned skill, a published workflow; one list, each can be taken back); paying, buying, sending, publishing, deleting or sharing needs his yes every time | DEC-0156 | — |
| T-05 | Why do `test_response_style` and `test_server_app`'s recovery-key test fail only in the full run? | 15 |
| T-06 | Typed events across processes: delivery guarantees, idempotency | 05 |
| T-07 | The capability contract's fields as code, and its test | 08 |
| T-08 | The extension sandbox's profile and threat model | 13 |
| T-09 | A MIA portal (D-Bus) for Flatpak apps to offer capabilities | 05/10 |
| T-10 | The PC's Linux base: Ubuntu LTS (`docs/HARDWARE.md`, ROCm's matrix) or Fedora Atomic (DEC-0157); a 14B model on the RX 7900 XTX on each decides | 06 |
| T-11 | The 32B model writes at 14 tokens a second on Windows, below this GPU's expectation; measure on Linux | 06/07 |
| T-12 | Boot targets (REQ-PER-001, 002) need the image to be measured | 14 |
| T-13 | Orca and keyboard access inside MIA's cage session | 10 |
| T-14 | Her surfaces in a browser engine in the session, or a native shell | 10 |
| T-15 | Meaning search: which embedding model, where, how fast on his data | 07 |
| T-16 | Each action kind's reversibility (REQ-AUT-006), from the undo log's coverage, hand-checked | 08 |
