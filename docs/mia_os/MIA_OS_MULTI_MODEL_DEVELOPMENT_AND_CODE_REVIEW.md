# MIA OS: several models building MIA (Prompt 15; DEC-0268)

*Claude (Opus), 2026-11-18. Planning only. The team: `docs/COLLABORATION.md`.*

| Who | Does | Checked by |
|---|---|---|
| Zac | decides; approves decisions; tries things | — |
| Claude (Opus, Fable) | the engine, plans, most code | the suite; the other model's review (DEC-0174); an independent review of every large batch |
| ChatGPT | vision | Zac |
| Muse | design, the look | Zac, Claude for function |
| MIA herself | Night School exercises, fixes | the lab's rules, Claude's pass (DEC-0200, DEC-0225) |
| Codex, Copilot | providers on the task board (T-0006) | reviews from two providers, never the author's (DEC-0069) |

**Review practice (2026-11-18):** after a run of builds, a fresh agent reads the commits end to end for concrete
failing scenarios; it found six real bugs the suite missed on its first use. **Decisions** are only Zac's; models
propose them (CLAUDE.md).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-024 | A batch of changes made unattended shall be reviewed end to end by a model that didn't write it before it's called done. | Should | MVP | All | Exists (practice) | R | DEC-0268 → 15 |
