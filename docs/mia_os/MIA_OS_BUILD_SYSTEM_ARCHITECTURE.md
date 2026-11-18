# MIA OS: what gets built (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Artifact | Built from | Built by | Exists |
|---|---|---|---|
| The MIA OS image (PC) | `os/Containerfile` (Fedora Atomic KDE + MIA) | CI (`bootc` / podman) | Containerfile yes; CI build of the full image to add |
| The Pi image | a Pi variant of the image (cage kiosk, the household display) | CI | planned |
| The phone app (APK) | `android-phone/` | CI (`android-phone.yml`) | yes |
| The Windows install | `install.ps1` | his PC; CI dry-run | yes |
| The web front end | `web/` (no build step) | served as is | yes |
| The greenhouse node | `homestead/` | its own | yes |
| Generated documents | the atlas, maps, matrix | the tools, checked by tests | yes |

**No bundler for the web** (plain files, CSP-friendly) and no compiled Python: what's in the repository is what runs.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-014 | Every artifact (the PC image, the Pi image, the phone app) shall be built by CI from the repository alone. | Must | R1 | All | Partial (phone) | T | DEC-0264, DEC-0265 → 15 |
