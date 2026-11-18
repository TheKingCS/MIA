# MIA OS: the final risk register (Prompt 17)

*Claude (Opus), 2026-11-18. Version 1.0. Governs over `MIA_OS_RISK_REGISTER.md` (which keeps every earlier entry
for history). Duplicates are merged here and stale entries closed. New risks are R-86 to R-95. Impact and likelihood:
H, M, L. Weaknesses that aren't fixed yet are named here only in general terms; specifics stay out of the public
repository.*

## 1. Open risks, highest first

| ID | Risk | Impact | Likelihood | Earlier IDs | Response | Owner | Watch |
|---|---|---|---|---|---|---|---|
| R-81 | The GPU runs worse, or unstably, under Fedora | H | L | R-34, R-40 | HW-01 before anything else on his PC; the Vulkan backend; upstream Ollama's build; the Ubuntu comparison | Claude, Zac | HW-01's report |
| R-82 | KWin won't hold MIA as a one-app session with ordinary windows, or breaks between releases | M | M | R-36 | cage fallback (DEC-0191); FW-03 first among the session work | Claude | FW-03 |
| R-83 | The move loses or garbles data | H | L | — | rehearsal (FW-07), content hashes (REQ-IMP-009), Windows untouched, the backup | Claude, Zac | the verification report |
| R-86 | **Windows won't boot from the USB enclosure** | M | M | — | HW-02 tests it first; the fallback is the drive back in the slot (Q-107) | Zac | HW-02 |
| R-87 | A forgotten disk PIN and a lost recovery key lock him out of his PC | H | L | — | the recovery key printed and stored offline; the backup on the external drive restores onto a fresh install | Zac | MV-01 checklist |
| R-88 | Fedora's packages lag upstream (Ollama 0.24 vs 0.35) and a new model needs a newer one | M | M | — | upstream Ollama's build as a documented fallback inside the image | Claude | model changes |
| R-89 | A dependency's release changes the shell (PySide6 6.12's WebEngine split) | M | M | R-78 | hash locks (FW-01); the pin; CI on every push | Claude | the weekly VM run |
| R-90 | Documentation drifts from the code again (counts, statuses, PoC states) | M | H | — | the hierarchy (DEC-0275); statuses only in records; counts from code; the document index checked at each prompt | Claude | each session |
| R-91 | 53 decisions sit proposed, so work proceeds on unapproved ground | M | M | — | Q-110: settle them as a batch; nothing builds on a proposed decision without a note | Zac | the decision log |
| R-93 | The foundation work takes much longer than estimated (FW-03 above all) | M | M | R-84 | the critical path first in each session; the Windows backlog keeps MIA improving meanwhile | Claude | sessions per package |
| R-85 | His hands-on steps wait (USB stick, drive) | M | H | — | WAITING_ON; the VM work continues | Zac | WAITING_ON |
| R-79 | CI on Windows and in a VM grows slow | L | M | — | jobs only on their inputs; the VM weekly and on `os/` changes | Claude | CI times |
| R-80 | Several sessions at once overwrite each other's work | M | M | — | own files only; worktrees; never a broad restore | every agent | — |
| R-94 | Piper's maintenance and licence | L | M | — | Kokoro is the main voice; Piper the fallback; Q-108 | Claude | — |
| R-95 | Vosk stagnates | L | M | — | whisper.cpp measured (DEC-0211) | Claude | — |
| R-35 | Fedora's bootc-native desktop path isn't finished; the Kinoite container we derive from changes under us | M | M | — | the base pinned by digest (FW-01); the weekly VM run catches a changed base | Claude | the weekly VM run |
| R-37 | The privileged helper grows a general-purpose operation | H | L | — | a fixed list, each operation reviewed by Codex as security-critical (FW-06) | Claude, Codex | every helper change |
| R-39 | Fedora's twice-yearly release becomes a chore that's skipped | M | M | — | an automated rebase build to the next release, tested in the VM before it's offered | Claude | each Fedora release |
| R-92 | A user-unit watchdog can't reboot a hung machine | L | L | — | greenboot and the hardware watchdog cover the OS; the runtime's watchdog restarts only MIA | Claude | — |

## 2. Closed or merged

| ID | Why |
|---|---|
| R-02 "no Linux key backend" | closed: `core/key_unlock.py` uses systemd-creds or the TPM (DEC-0169, built) |
| R-03 (listed twice) | the two entries merged in the old register's history; neither is open in the final register |
| R-34, R-40 | merged into R-81 |
| R-36 | merged into R-82 |
| R-84 | merged into R-93 |
| R-09 to R-11, R-13 to R-18, R-20 | live in `MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md` (engine debt, not OS risks); unchanged |
