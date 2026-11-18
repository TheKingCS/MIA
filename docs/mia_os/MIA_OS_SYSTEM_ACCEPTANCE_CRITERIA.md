# MIA OS: system acceptance criteria (Prompt 04, deliverable 13, with §24)

> **Prompt 17 (2026-11-18):** the safety net is the Windows drive kept untouched (DEC-0272), not dual boot; the MVP's gate is in `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md`.

*Claude (Opus), 2026-11-15. Planning only. How MIA OS is judged at each stage. A feature is accepted only when its
behaviour works, its permission is enforced, its failure is handled and its result can be checked; a screen alone
proves nothing.*

## 1. The four stages

| Stage | Means | Accepted when |
|---|---|---|
| Minimum viable | [MVP_DEFINITION](MIA_OS_MVP_DEFINITION.md) §2 | every Must · MVP requirement verified; the MVP scenarios pass on the image; a week as Zac's main system |
| First daily-usable (R1) | his only PC system | every Must · R1 verified; Windows no longer needed for a month (dual boot kept as a safety net) |
| Mature | the vision's system | every Should verified or decided against; the Mature scenarios pass |
| Aspirational | Later and speculative | not judged; reviewed yearly |

## 2. Criteria by area (each names how it's measured)

| Area | Criterion | Measured by |
|---|---|---|
| Basic OS | boots, logs in, runs Plasma and conventional apps with MIA's services masked | D: REQ-ARC-002 |
| MIA availability | her session starts by default; the runtime answers within 30 s of login, or the recovery page shows | M: 20 boots, none without one or the other |
| Application management | every app listed with its status; a broken app is "failing" with why; nothing else stops | T: `tests/test_app_ecosystem.py`; S-13 |
| AI integration | every capability by screen and voice; no answer states an unlooked-up number; success only from records | T: parity, `invented_numbers`, REQ-AI-002 |
| Conventional desktop | usable within 10 s of choosing it, MIA running or not | M: REQ-PER-002 |
| Offline | a day's scenario with the network unplugged has no dead end | M: S-12 |
| Security | no capability untiered; outside text never steers a change; the runtime unprivileged; the disk encrypted | T: `tests/test_grants.py`; I: process owner; S-18 |
| Privacy | no data leaves except to listed destinations | I: a network capture during S-12 and S-03 shows only them |
| Reliability | each failure in the RELIABILITY table produces its stated behaviour | T and D: one injected failure each |
| Multi-device | the phone and glasses work against the Linux PC; offline edits sync without loss | T: sync tests against the Linux runtime; S-06, S-15 |
| User experience | the essential functions one action away; approvals in one plain sentence | D: a walk-through |
| Accessibility | WCAG 2.2 AA on her pages; keyboard-only use; Orca reads them | I: automated check plus manual pass |
| Performance | the PER targets on the reference PC | M: as each says |
| Recovery | restore from backup rehearsed; a failed update rolled back; the USB recovery reaches his data | D: once each a release |

## 3. Never accepted

- An action reported done without its record.
- A capability shown that doesn't exist (`core/capabilities.py` is the list).
- A consequential action (paying, sending, deleting, sharing) without his press at the moment.
- A fallback that is a blank screen.
