# MIA OS: the critical path (Prompt 16; DEC-0271)

*Claude (Opus), 2026-11-18.*

| # | Step | Who | Blocks |
|---|---|---|---|
| 1 | PoC 1: Fedora from a USB stick runs the 14B model at 65 tokens/s or more on his GPU | Zac (an hour), Claude guiding | the whole OS (if the GPU fails under Linux, the base changes) |
| 2 | The image boots in a VM with the runtime at core ready | Claude | everything after |
| 3 | MIA's session under KWin (PoC 3); cage the fallback | Claude | M6 |
| 4 | Updates and rollback; the TPM-unlocked disk | Claude | M6 |
| 5 | Install on the 4 TB drive, his data moved | Zac and Claude together | the MVP |
| 6 | A week as his main system | Zac | the MVP gate |

**Shortest calendar:** steps 2 to 4 are Claude's and can run in parallel with step 1; once he has a USB stick and the
drive, steps 1, 5 and 6 are about a week and a half of his time, mostly the week of use.
