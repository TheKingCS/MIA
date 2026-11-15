# MIA OS open questions

*Central register. Each question has an owner (Zac, a check on the PC,
or the prompt that will answer it). It replaces
`preliminary/MIA_OS_OPEN_QUESTIONS_FIRST_PASS.md`, whose questions are
folded in here.*

## For Zac

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
| T-05 | Why do `test_response_style` and `test_server_app`'s recovery-key test fail only in the full run? | 15 |
