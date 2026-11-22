# MIA OS: the capability truth registry (Prompt 09 §5; DEC-0220)

*Claude (Opus), 2026-11-17. Planning only. **Built 2026-11-22 (WP-08)**: `core/capability_registry.py`, one record per
app from its manifest, the tests, the turn traces, the Fix-It Log, parity and `LIMITS`; shown on Diagnostics as
"What I Can Do". Not yet: a record per cross-app capability (voice, browser...), each test's last result, the
version.*

## 1. From what exists

`core/capabilities.py` already gives each app a status from the code (implemented, partial, planned, unavailable here,
malfunctioning) with evidence verified or inferred, and `work/parity.json` decides each gap. The registry extends that
from apps to **capabilities** (the prompt's list: voice, speech recognition, image understanding, browser, email,
greenhouse monitoring, software development...) and joins their evidence.

## 2. A capability record

| Field | From |
|---|---|
| id, name, description | the code (a capability maps to tools, action kinds and services) |
| responsible component | the app that owns it (`app_registry.owner_of`) |
| required services, hardware, permissions | `service_map`, the hardware records (DEC-0203), the tiers |
| supported operations | its tools and action kinds |
| supported devices | the parity table |
| availability now | the services and hardware it needs, checked now |
| state | the state model (`MIA_OS_CAPABILITY_STATE_MODEL.md`) |
| verification | the tests that cover it, the bench, a golden set, with their last result and date |
| last success, last failure | the turn trace and the Fix-It Log |
| known limitations | `capabilities.LIMITS` |
| evidence and confidence | each source cited; confidence from how direct the evidence is |
| version | the commit that last changed its code |

**Derived, never edited:** the registry is rebuilt from its sources (at start, on a change, daily). Nothing writes a
state into it by hand, and nothing a model says changes it.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-003 | Each capability shall have one record joining its owner, needs, operations, devices, state, verification, last success and failure, limits and evidence. | Must | R1 | All | Exists (WP-08: per app, `core/capability_registry.py`; the version per capability not yet) | T | DEC-0220 → 09 |
| REQ-SLF-004 | The registry shall be rebuilt from its sources and never edited by hand or by a model. | Must | R1 | All | Exists | T: no write path | DEC-0220 → 09 |
