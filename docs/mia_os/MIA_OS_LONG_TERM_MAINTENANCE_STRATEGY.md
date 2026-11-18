# MIA OS: maintaining MIA for years (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Concern | Strategy |
|---|---|
| Fedora releases every six months | move the image's base a month after each release, through `next` and the VM |
| Python versions | one minor version behind the newest, moved yearly |
| Qt and the classic view | retire the Qt screens as parity completes; the host window stays |
| Models | re-benched when a new family appears; replaced only when better |
| Dependencies | the weekly check; a yearly prune of what's unused |
| Knowledge | entries per build; `docs/REBUILD.md` kept able to rebuild MIA from nothing |
| His data | additive formats; migrations with backups; exports in open formats (JSON, Markdown) |
| Bus factor | everything in the repository and his backups; no service only a model knows how to run |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-030 | `docs/REBUILD.md` shall stay able to rebuild MIA from nothing, checked against the code by a test of the files it names. | Should | R1 | All | Partial | T | DEC-0262 → 15 |
