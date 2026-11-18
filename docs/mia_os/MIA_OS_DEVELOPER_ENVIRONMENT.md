# MIA OS: the developer environment (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Who develops | Where | With |
|---|---|---|
| Claude (Opus, Fable) at the PC | Windows 11, the venv, PowerShell and Git Bash | the full suite, the real models, his GPU |
| Claude in the cloud | a Linux container | `tools.cloud_tests` stand-ins for the PC's libraries |
| MIA (Night School, the lab) | git worktrees beside MIA | the suite, her own coder and Claude as teacher |
| ChatGPT, Muse | the repository's files and handoffs | `docs/COLLABORATION.md` |
| On MIA OS | a Fedora toolbox container (the same packages as the image) | the suite, the image build |

**Rules every session follows** (CLAUDE.md): read `docs/NEXT_SESSION.md` first; stage only your own changes;
document every file and definition; regenerate the maps; run the suite; commit with the attribution line; push.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-012 | A new development machine (the PC, a cloud session, the laptop, a toolbox) shall reach a passing suite by following one written procedure. | Should | R1 | All | Partial (install.ps1, cloud_tests) | D | DEC-0263 → 15 |
