# MIA OS: system identity and architecture introspection (Prompt 09 §4)

*Claude (Opus), 2026-11-17. Planning only.*

**What MIA knows about how she's made, and from where** (all exists):

| Question | Answered from |
|---|---|
| What am I? | `core/personality.py`, `core/self_knowledge.py` |
| What am I made of? | the code atlas (`core/code_atlas.py`: every file and definition, documented), the system map (`core/system_map.py`) |
| Which apps do I have? | the Application Registry (`core/app_registry.py`), checked against the code by a test |
| Which version am I? | git: the commit she runs; the image's version on MIA OS (Prompt 14) |
| What do I run on? | `core/service_map.py` (services, checked now), `core/model_registry.py`, the hardware capability records (DEC-0203) |
| What was decided about me? | `docs/DECISIONS.md`, `MIA_OS_DECISIONS.md`, knowledge entries (`core/dev_knowledge.py`) |

**Rule:** introspection reads these sources; it never keeps a hand-written description of herself that could drift.
Where two sources disagree (a manifest names a tool the code lacks), the registry test fails, as it does today.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-001 | MIA's description of what she's made of shall be read from the code, the registry and runtime sources, never kept by hand. | Must | MVP | All | Exists | T: atlas and registry tests | DEC-0220 → 09 |
| REQ-SLF-002 | Asked which version she is, MIA shall answer from the running commit or image. | Should | R1 | All | Partial | T | DEC-0221 → 09, 14 |
