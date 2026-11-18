# MIA OS: system updates (Prompt 14; DEC-0257)

*Claude (Opus), 2026-11-18. Planning only. Building and signing: Prompt 15.*

| Step | How |
|---|---|
| Built | the image from this repository (Fedora Atomic base + MIA), in CI, signed (cosign) |
| Found | `bootc upgrade --check` on a timer |
| Downloaded | in the background, at low priority, never during a model job |
| Staged | the new deployment ready beside the running one |
| Applied | at a restart: when he says, or at night if he's allowed it (Q-95), never mid-run |
| Checked | greenboot's health checks after boot (the runtime reaches core ready, the shell starts) |
| Rolled back | automatically if the checks fail twice; by hand from the boot menu any time |

**What's in an update:** the OS, MIA's code, her default config. **What isn't:** his data, his settings, his models
(in `/var`), his Flatpaks (their own updates).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-REL-023 | An update shall be downloaded in the background and applied only at a restart he allows, never during a run or a model job. | Must | MVP | PC | Planned | D | DEC-0257 (Q-95) → 14 |

## Engineering (Prompt 15, 2026-11-18)

Releases and channels: `MIA_OS_RELEASE_ENGINEERING_AND_VERSIONING.md` (DEC-0265).
