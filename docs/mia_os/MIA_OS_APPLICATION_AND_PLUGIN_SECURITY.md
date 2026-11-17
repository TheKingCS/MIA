# MIA OS: application and add-on security (Prompt 13 §12)

*Claude (Opus), 2026-11-18. Planning only.*

| App kind | Today | Plan |
|---|---|---|
| MIA's own apps (in this repository) | reviewed, tested, tiered; run with MIA's rights | the same; manifest permissions enforced at runtime when apps run separately |
| Apps MIA makes (Forge, creations) | written in the lab, checked, approved | the same; protected rules |
| Third-party MIA add-ons | not installed (no sandbox) (CLAUDE.md) | only once a sandbox exists (a separate process with only its manifest's capabilities), and signed (Q-94) |
| Conventional Linux apps | — | Flatpak with its permissions and portals |
| Browser extensions in her browser | none | none |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-040 | By the time MIA is built out, every add-on and capability shall run on his own machines, with no cloud service required (Zac, Q-94). | Must | Later | All | Partial | R: the capability registry | DEC-0253 (Q-94) → 13, 16 |
| REQ-SEC-023 | No third-party MIA add-on shall be installed until add-ons run sandboxed with only their manifest's capabilities. | Must | MVP | All | Exists (none installed) | R | DEC-0253 (Q-94) → 13 |
