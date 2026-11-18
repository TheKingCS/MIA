# MIA OS: CI and delivery (Prompt 15; DEC-0264)

*Claude (Opus), 2026-11-18. Planning only.*

| Job | On | Does | Exists |
|---|---|---|---|
| Linux suite | every push, every PR | the full pytest suite on Ubuntu (and Fedora's toolbox) | inside the PoC job; a job of its own to add |
| Windows | every push (not docs-only) | install.ps1, the suite | yes |
| Phone | pushes touching `android-phone/`, `core/` | build and sign the APK | yes |
| OS image | pushes touching the image's inputs | build, VM boot test, sign, publish | VM workflow yes; publish to add |
| Model check | on demand | a small model on cases | yes |
| Dependency audit | weekly | OSV | yes (on the PC); in CI to add |
| Pages | pushes | the demo preview | yes |

**The gate:** a commit is pushed only after the full suite passes locally (practice); CI confirms on Linux and
Windows. **Her own changes** (the lab) are merged only after the suite passes there; if pushed (Q-100), CI checks
them too. **Delivery:** the PC and Pi pull signed images (DEC-0257); the phone APK he installs.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-016 | The full suite shall run on Linux and Windows on every push to master, and a failure shall be reported to the session that pushed. | Must | MVP | All | Partial | T | DEC-0264 → 15 |
