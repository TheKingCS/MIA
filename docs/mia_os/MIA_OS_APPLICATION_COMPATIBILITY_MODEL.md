# MIA OS: compatibility and long-term evolution (Prompt 03 §17)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

| Area | Rule | Checked by |
|---|---|---|
| Local API | path-versioned (`/api/v1`); fields added, never repurposed or removed within a version | a contract test over the route list (proposed) |
| Capabilities | versioned per capability (`id@n`); new optional inputs only; breaking change = new version beside the old, with a deprecation date | a contract test over the registry's schemas (proposed) |
| App vs OS version | MIA's own apps ship with the OS image, so they always match | the image build |
| Runtime dependencies | pinned (`requirements.txt`); the phone's libraries pinned separately (CI `phone-libraries`) | CI |
| Hardware | declared per capability (`needs.devices`); a missing device means `missing_dependency`, not a crash | the app status |
| Devices | parity rows per device | `tests/test_parity.py` |
| Store schemas | version per store file, migrations on load, old file kept until the next backup (T-03) | per-store migration tests (proposed) |
| Deprecation | announced in the registry with date and replacement; the voice answer and the page say so | — |
| Replacement | a new app takes over an old one's capabilities; old ids alias (as `core/web_areas.py` aliases old area ids) | the app catalogue tests |
| Unsupported or legacy | the Qt classic view: fixes only (DEC-0168); the retired Companion app (DEC-0160) | — |
| Before an update | the suite runs in the lab on the new image; an extension past its contract's deprecation date is flagged before the update | the lab, the extension host |

Compatibility is recorded where it's tested: CI results per commit, `docs/PARITY.md`, and the extension host's list
of each extension's contract version.
