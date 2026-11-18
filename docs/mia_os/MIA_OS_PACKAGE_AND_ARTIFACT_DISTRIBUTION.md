# MIA OS: distributing what's built (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Artifact | Published to | Fetched by |
|---|---|---|
| MIA OS image | GitHub Container Registry, signed | the PC's update timer (bootc) |
| The Pi image | the same | the Pi |
| The install ISO | GitHub Releases | him, for a new machine |
| The phone APK | GitHub Releases (and CI artifacts) | him, installed on the phone |
| An SBOM per artifact | beside it | — |

**Nothing personal is ever in an artifact**: images carry code and defaults only; his data stays on his machines.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-021 | Every published artifact shall be signed, carry an SBOM, and contain no personal data. | Must | R1 | All | New | T | DEC-0265 → 15, 13 |
