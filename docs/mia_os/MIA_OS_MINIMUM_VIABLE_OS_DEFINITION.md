# MIA OS: the minimum viable OS (Prompt 16; DEC-0270)

> **Prompt 17 (2026-11-18):** `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md` governs the MVP and the releases where this differs (it restores DEC-0182's USB recovery path and keeps the MVP free of cloud models).

*Claude (Opus), 2026-11-18. The MVP is DEC-0182's (`MIA_OS_MVP_DEFINITION.md`), refined by Prompts 06 to 15.*

| Area | In the MVP | From |
|---|---|---|
| Boot | the signed image; Secure Boot; the disk unlocked by the TPM; Plasma and MIA at login; the previous deployment | DEC-0182, 0252, 0257 |
| MIA's session | her front end full screen under KWin; her window strip; the ambient view on the second monitor, folding to one | DEC-0227, 0231 |
| Everything MIA does today | every app, action, grant and screen | DEC-0182 |
| Intelligence | Ollama on the GPU with flash attention and the 8-bit cache; qwen2.5:14b everyday; the specialists' models | DEC-0206 to 0212 |
| Data | every store moved, counts matched; sealed stores; the history | DEC-0272 |
| Security | two-step offered; sensitive never to a cloud; the lockdown phrase | DEC-0250, 0251, 0254 |
| Reliability | readiness levels; restart limits; nightly backups with an off-PC copy; night updates rolled back by themselves | DEC-0255 to 0259 |
| Devices | the phone and glasses as now; Tailscale only away | DEC-0241, 0244 |
| Self-care | self-repair; her changes on Claude's pass with a daily summary | DEC-0222, 0225 |

**Not in the MVP (R1 and later):** the UAL on any selection, recall beyond the first slice, workspaces, cross-app
plans as one card, the household display, the laptop engine, Zeta Astralis, spatial.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-IMP-003 | The MVP shall be done only when every Must · MVP requirement in the matrix passes its verification on his PC. | Must | MVP | PC | New | T: the matrix's MVP list empty | DEC-0270 → 16 |
