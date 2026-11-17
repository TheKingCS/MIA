# MIA OS: configuration (Prompt 14)

*Claude (Opus), 2026-11-18. Planning only.*

| Layer | Where | Recovers by |
|---|---|---|
| Defaults | `config/default_config.json`, in the image | never edited; always there |
| His settings | `config/config.json` (merged with defaults on load) and per-person settings | a factory reset is deleting the file (built); backups |
| A damaged settings file | — | the defaults load, the bad file kept aside, he's told (as stores) |
| OS settings | KDE's and the image's `/etc` (3-way merged by ostree on update) | the previous deployment |
| Secrets | the vaults, sealed | the recovery key |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-026 | A damaged settings file shall never stop MIA: the defaults load, the file is kept aside, and he's told. | Must | MVP | All | Partial | T | DEC-0258 → 14 |
