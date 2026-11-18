# MIA OS: the repository (Prompt 15; DEC-0262)

*Claude (Opus), 2026-11-18. Planning only.*

| Folder | Holds | Rule |
|---|---|---|
| `core/` | the engine: stores, actions, services | imports nothing from `gui/` or `modules/` |
| `apps/` | each app's manifest | every tool and kind claimed exactly once, tiered |
| `modules/` | Qt modules (the classic view) | only `core/`, through ModuleBase; retiring by parity |
| `web/` | the front end | talks only through `web/mia.js`; no logic |
| `server/` | the FastAPI server | thin routes over core |
| `gui/` | the desktop host | only `core/` |
| `homestead/` | the greenhouse node, self-contained | never imported by MIA's `core/` |
| `android-phone/` | the phone app | the same engine (Chaquopy) |
| `os/` | the bootc image and its proofs of concept | built from the repository |
| `deploy/` | install scripts and systemd units | |
| `tools/` | command-line tools | |
| `tests/` | the suite | |
| `docs/` | everything written, `docs/mia_os/` the OS plan | |
| `work/` | tasks, knowledge, benches, coverage decisions | protected from her lab |
| `data/`, `config/config.json`, `audit/`, `pc-check/` | his data and private findings | never in git |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-011 | Nothing personal, no secret and no description of an unfixed weakness shall be committed (the repository is public); a test shall check the ignore rules cover his data folders. | Must | MVP | All | Partial (ignore rules; practice) | T | DEC-0262 → 15, 13 |
