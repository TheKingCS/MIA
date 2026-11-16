# MIA OS: non-functional requirements (Prompt 04, deliverable 5, with §15 and §18)

*Claude (Opus), 2026-11-15. Planning only. Row format: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md) §1.
Security here is the system-level requirement; the design is Prompt 13's. Reliability is in
[RELIABILITY](MIA_OS_RELIABILITY_AND_DEGRADATION_REQUIREMENTS.md), accessibility in
[USER EXPERIENCE](MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md).*

## Security (SEC)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-001 | The PC's disk shall be encrypted (LUKS2), unlocked at boot by the TPM plus a PIN; the phone keeps Android's encryption. | Must | MVP | PC | Planned (DEC-0157) | I, D | P8 → 13, 14 |
| REQ-SEC-002 | Personal and household stores shall be sealed at rest with a key the OS keeps for the person (Windows: DPAPI; Linux: the systemd credential), unreadable from another user account or a copied disk. | Must | MVP | PC, Pi | Exists (DEC-0126; DEC-0169 proposed, built for Linux) | T: `tests/test_at_rest.py`, `tests/test_key_unlock.py` | P7, P8 → 13 |
| REQ-SEC-003 | Every capability shall run with least privilege: the runtime as the person's unprivileged user, extensions sandboxed, system changes through the helper only. | Must | MVP | PC, Pi | Partial: tiers and grants exist; helper and sandbox planned | T | DEC-0156, DEC-0158, DEC-0176 → 13 |
| REQ-SEC-004 | The runtime's local API shall accept only authenticated callers (the person's sessions and paired devices); nothing listens on a public interface by default. | Must | MVP | PC, Pi | Partial: pairing tokens for the phone; review needed for the image | T: an unauthenticated call is refused | P8 → 12, 13 |
| REQ-SEC-005 | Text from outside MIA (web pages, search results, mail, feeds, a selection from another app) shall reach the model marked as outside text, and no change shall follow from it in the same turn. | Must | MVP | All | Exists (`browser_safety.untrusted`, `tool_loop.OUTSIDE_TOOLS`, manifests' `outside` tags) | T: `tests/test_grants.py` sweep | DEC-0156, DEC-0117 → 13 |
| REQ-SEC-006 | Nothing MIA reads or says shall be able to give her a grant; grants come only from what the person does (teaching a skill, publishing a workflow). | Must | MVP | All | Exists (no grant-giving action or tool) | T: `tests/test_grants.py` | DEC-0156 → 08, 13 |
| REQ-SEC-007 | Secrets (keys, tokens, passwords) shall never be typed by her browser, shown to the model, logged or committed. | Must | MVP | All | Exists as rules (browser safety, failure-log redaction, the public repo) | T, I | DEC-0117 → 13 |
| REQ-SEC-008 | The OS image and MIA's updates shall be signed and verified before they're applied; an extension's update must be signed by the same key. | Must | R1 | PC | Planned (DEC-0157, DEC-0176) | D | P8 → 13, 15 |
| REQ-SEC-009 | Python and system dependencies shall be pinned and audited for known vulnerabilities on a schedule. | Should | MVP | All | Exists (dependency audit daily check) | T | P8 → 15 |
| REQ-SEC-010 | Approvals for consequential actions by voice shall need an identified speaker on that person's own device. | Must | Mature | PC, Ph, Gl | New (MU-5) | T | MU-5 → 13 |

## Privacy (PRV)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-PRV-001 | MIA shall record nothing continuously (screen, microphone, keystrokes, clipboard) unless the person turned that kind on, for a stated retention, visibly while it runs. | Must | MVP | All | Exists as practice (no continuous recording); a per-kind switch is New for OS context | I, T | P7, prompt 23 §2.1, §3.1 → 13 |
| REQ-PRV-002 | Everything MIA keeps about the person shall be listable by store, exportable and deletable by them. | Must | R1 | All | Partial: stores listed; export per app; no one-step export | D | P5 → 13 |
| REQ-PRV-003 | No personal data shall leave the person's devices except to a destination they chose (a cloud model, a backup target, a sync peer), and each kind of transfer shall be listed. | Must | MVP | All | Exists today (only the person's SearXNG and feeds, words only) | I: network audit | P3, P7 → 13 |
| REQ-PRV-004 | Searches and watches shall send only the person's own words, never their records. | Must | MVP | All | Exists (DEC-0122, World Intelligence matches on the PC) | T | DEC-0122 → 13 |
| REQ-PRV-005 | Voiceprints, health records and private journal entries shall never be synced to a cloud or shown in a shared session. | Must | MVP | All | Exists for journal and health; voiceprints New | T | MU-9 → 13 |

## Performance (PER)

**Baselines measured on Zac's PC, 2026-11-15** (Ryzen 7 9800X3D, Radeon RX 7900 XTX 24 GB, 32 GB RAM, Windows 11,
Ollama; method: Ollama's own timings, one 20-word question, 64 tokens out, temperature 0; MIA's engine timed in
Python):

| What | Measured |
|---|---|
| llama3.2 3B: load from disk / answer once loaded / writing speed | 4.1 s / 0.3 s / 220 tokens a second |
| qwen3 14B | 11.2 s / 0.9 s / 73 tokens a second |
| qwen2.5 32B | 37.0 s / 3.4 s / 14 tokens a second (well below what this GPU should give; worth checking on Linux with ROCm) |
| MIA's engine: import, cold / warm | 1.7 s / 0.5 s |
| The day's whole picture (`assemble_life_state_v2`) | 0.02 s |
| The sidebar (`shell`) / the Apps page (`apps_page`) | 0.005 s / 0.03 s |
| The phone (earlier, `docs/PHONE_MODEL_TEST.md`) | Qwen 2.5 1.5B: 28 s a turn after the fixes; 9 tokens a second writing |

Targets are set from these and marked *(provisional)* where they need the Linux image to be measured. Each says why it
matters, where and how it's measured.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-PER-001 | From power-on to a usable login on the PC shall take under 30 s, and from login to MIA's session showing Home under 10 s. *(provisional)* Why: the PC should feel like an appliance. | Should | R1 | PC | New | M: `systemd-analyze` and a timestamp at Home's first paint, median of 5 cold boots | §6 → 14 |
| REQ-PER-002 | The conventional desktop shall be usable within 10 s of choosing it at login, with MIA's runtime still starting or failed. *(provisional)* | Must | MVP | PC | New | M: as above | E2 → 10, 14 |
| REQ-PER-003 | A screen of MIA's (Home, an app page) shall show its data within 1 s of being opened, warm. Measured today: the engine assembles them in under 0.1 s. | Must | MVP | All | Exists on the PC | M: browser timing, 95th percentile | P1 → 10 |
| REQ-PER-004 | Search across every store shall return within 0.5 s for the person's data size. *(provisional)* | Should | MVP | PC | Partial | M: a 100k-record synthetic set | P4 → 07 |
| REQ-PER-005 | On the PC, a spoken or typed question answered by a lookup shall start answering within 2 s; one needing the everyday model (3B to 14B, loaded) within 3 s. Measured: 0.3 s and 0.9 s once loaded. | Must | MVP | PC | Exists | M: turn timing in the Fix-It Log's `slow` records | E3 → 07 |
| REQ-PER-006 | The everyday model shall be kept loaded while the PC is in use, so a first question never waits for a load (4 to 11 s measured), unless memory is needed elsewhere. | Should | R1 | PC | New | M | P18 → 07 |
| REQ-PER-007 | A heavy model (30B class) shall be used only for tasks that ask for it, with the person told it will take longer (37 s to load, 3.4 s an answer measured). | Should | R1 | PC | New | T: routing rules | E3 → 07 |
| REQ-PER-008 | MIA's runtime, idle, shall use under 1 GB of memory and under 2% of one core on the PC, excluding loaded models. *(provisional)* | Should | R1 | PC, Pi | New | M: 1 hour idle | P13 → 05 |
| REQ-PER-009 | Background work shall yield to the person: deferrable jobs wait while the PC is busy, on battery or offline, and say so. | Must | MVP | All | Exists (homeostasis) | T | DEC-0173 → 05 |
| REQ-PER-010 | The phone shall answer offline with its own model within 30 s for an everyday question, and say which model answered. Measured: 28 s. | Should | MVP | Ph | Exists | M | DEC-0022 → 07, 12 |

## Maintainability (MNT)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-MNT-001 | The full test suite shall pass before every commit to the main branch, on Windows today and on Linux once the image exists. | Must | MVP | All | Exists on Windows (6,483 tests); Linux run done once (2026-11-15) | T | P15 → 15 |
| REQ-MNT-002 | Every process (store, action family, job, app) shall have an improvement loop or a recorded reason it has none. | Must | MVP | All | Exists (`tests/test_loop_coverage.py`) | T | DEC-0094 → 09 |
| REQ-MNT-003 | Every Opus change shall be reviewed by Fable (and the reverse where it fits), recorded in the notes. | Must | MVP | — | Exists (DEC-0174) | I | DEC-0174 → 15 |
| REQ-MNT-004 | No decision changes without a logged DEC entry Zac approved. | Must | MVP | — | Exists | I | CLAUDE.md → 17 |

## Compatibility (CMP)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-CMP-001 | MIA shall keep running on Windows until the Linux image is Zac's daily system; no change may make Windows MIA worse in the meantime. | Must | MVP | PC | Exists | T: the suite on Windows | P1 (preserve working features) → 16 |
| REQ-CMP-002 | Existing data shall carry over to the Linux image with nothing lost (stores, history, sealed files re-sealed under the new key). | Must | MVP | PC | Planned | D: migration rehearsal on a copy | P5 → 16 |
| REQ-CMP-003 | Ordinary Linux GUI apps (Flatpak) and Windows-only needs shall be listed before the switch, each with its Linux answer or a reason to keep dual boot. | Must | MVP | PC | New | I | DEC-0157 → 06, 16 |
| REQ-CMP-004 | The phone app and the glasses shall work against the Linux PC exactly as against the Windows PC. | Must | MVP | Ph, Gl | New | T: sync and link tests against the Linux runtime | P11 → 12 |

## Operational (OPS)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-OPS-001 | Updates shall be offered, not forced; applied atomically; and reversible by choosing the previous deployment at boot. | Must | MVP | PC | Planned (bootc) | D | DEC-0157 → 14 |
| REQ-OPS-002 | A documented recovery path shall reach a working desktop and his data from a USB stick, without MIA and without the network. | Must | MVP | PC | New | D: rehearsed once a release | E5 → 14 |
| REQ-OPS-003 | Every deferred or failing job shall be visible in the runtime's health with its last error. | Must | MVP | All | Exists (`scheduler.status`, app statuses) | T | DEC-0173 → 14 |

## Developer experience (DX)

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DX-001 | A new MIA-native app shall need only its folder, its manifest and its code, checked by the registry; no edits to core lists. | Should | Mature | All | Partial (manifests are the app list; code moves in M6) | T | DEC-0178 → 08, 15 |
| REQ-DX-002 | A cloud session without the PC's libraries shall still run the Qt-importing tests through stand-ins. | Should | MVP | — | Exists (`tools/cloud_tests.py`) | T | CLAUDE.md → 15 |
| REQ-DX-003 | Building the OS image shall be one command from the repository, reproducible on another machine. | Must | MVP | PC | Planned | D | DEC-0104 → 15 |
