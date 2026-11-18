# MIA OS: keeping documentation true (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Kept true by | What |
|---|---|
| `tests/test_documentation.py` | every file and definition documented; old files' undocumented counts only go down |
| `tools.docs stale` | a docstring not changed with its code |
| Generated and checked | ATLAS, MIA_MAP, LOOPS, PARITY, EVENTS, the requirements matrix |
| Decisions | `docs/DECISIONS.md`, `MIA_OS_DECISIONS.md`; only Zac approves |
| Knowledge entries | what was built, how, why, what went wrong (`work/knowledge/`) |
| State | `docs/CURRENT_STATE.md`, `docs/NEXT_SESSION.md`, `docs/WAITING_ON.md` |
| The OS plan | `docs/mia_os/`, its master plan, status, open questions, risks |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-026 | Every generated document shall be checked by a test against what it's generated from. | Must | MVP | All | Exists | T | DEC-0266 → 15 |
