# MIA OS: API contracts (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Contract | Defined by | Checked by |
|---|---|---|
| Each screen's data | `docs/schema/*.example.json` (and schemas) | tests compare the live assembler's shape; the demo renders them |
| The Life State | `docs/schema/life_state.schema.json` | `tests/test_state_export.py` |
| Actions | `docs/schema/action.schema.json` | `tests/test_actions.py` |
| App manifests | `docs/schema/app_manifest.schema.json` | the registry tests |
| Phone ↔ PC (link, sync) | `core/home_link.py`, `core/sync.py` | sync tests |
| Device keys and sensors | the server's routes | server tests |

**Changes are additive**; a removal waits until no paired device uses it (REQ-DST-026).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-019 | Every API a screen or device uses shall have a schema or example checked by a test against the live code. | Should | R1 | All | Partial | T | DEC-0266 → 15 |
