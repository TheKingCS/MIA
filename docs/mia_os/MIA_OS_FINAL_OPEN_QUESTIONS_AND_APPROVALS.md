# MIA OS: final open questions and approvals (Prompt 17)

*Claude (Opus), 2026-11-18. Version 1.0. The questions also appear in `MIA_OS_OPEN_QUESTIONS.md`. Each says what it
decides in plain words.*

## 1. For Zac

| Q | Question | Recommended | Decides |
|---|---|---|---|
| **Q-105** | The first version of MIA OS (the MVP) is too big to prove as planned. Make its checklist the 67 must-haves that need the OS itself, and move 26 (accessibility polish, two monitors on two graphics chips, cloud models with consent, the capability registry) to the next release, Alpha, and 4 to Beta? Nothing is dropped; they're just checked later. The releases become MVP (first install), Alpha (your only system, signed monthly releases), Beta (R1 in your order) and Stable (three months without a rollback). | Yes | DEC-0276 |
| **Q-106** | Your disk will be encrypted. Unlock it with the TPM **plus a short PIN you type at each start** (the PIN is what really protects it if the PC is stolen), or the TPM alone (no typing, but anyone who has the PC can start it to the login screen)? Either way a printed recovery key opens it if something changes. | TPM plus a PIN | DEC-0277 |
| **Q-107** | Windows often refuses to start from a USB enclosure. Before installing MIA OS, try it once (about 15 minutes). If it won't start, the fallback is putting the old drive back in the slot (about ten minutes with a screwdriver). OK? | Yes | DEC-0272's fallback |
| **Q-108** | The repository has no licence yet, and Piper (the fallback voice) is now GPL-3.0. Choose a licence for MIA: GPL-3.0 (compatible with Piper; anyone who shares a changed MIA must share their changes), or keep it unlicensed for now (all rights reserved; Piper stays a separate install, not bundled)? | Keep it unlicensed for now, and don't bundle Piper in the image until you choose | the repository's licence |
| **Q-109** | Start building with the foundation work in a virtual machine, beginning with **FW-01, a reproducible image build** (the same packages every time, MIA starting on the right model)? Nothing on your PC changes. | Yes | the first work package |
| **Q-110** | 53 decisions are still marked "proposed": 48 from Prompts 05 to 16 that were never their own question, and 5 new ones from this review. Approve them as a batch, as listed in `MIA_OS_FINAL_ARCHITECTURE_DECISION_LOG.md` §4, except any you name? | Yes, as a batch | 53 decisions |

## 2. Approvals still needed before each stage

| Stage | Needs |
|---|---|
| Foundation | Q-109; Q-110 (or at least DEC-0263, DEC-0275, DEC-0276 and DEC-0279) |
| FW-05 | Q-106 |
| FW-08 | the phone's signing key (DEC-0160, his step) |
| MV-01 | the drive, the enclosure, the USB stick; HW-01 passed; HW-02 tried (Q-107); his go on the day |
| MV-02 → Alpha | Zac passes the MVP gate |

## 3. Open technical investigations (not his to answer)

| Investigation | Settled by |
|---|---|
| KWin as MIA's session, or cage | FW-03 (PoC 3) |
| Fedora's ROCm on his card | HW-01 (PoC 1) |
| greenboot's rollback on Kinoite's boot loader setup | FW-04 |
| Plasma Login Manager's custom sessions | FW-03 |
| whisper.cpp vs Vosk on his voice | needs his recordings (DEC-0211) |
