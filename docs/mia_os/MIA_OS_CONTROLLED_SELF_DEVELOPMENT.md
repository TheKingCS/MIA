# MIA OS: controlled self-development (Prompt 09 §13; DEC-0225)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. What exists

`core/dev_lab.py` (DEC-0058): a change is written in a git worktree beside MIA (no real records, no credentials by
construction), by Claude Code headless or her own coder (`core/mia_coder.py`), allowed only to edit files there and
run the suite. It's refused if it touches `PROTECTED`. The full suite runs and is compared with the same suite before;
a change is ready only with no new failure. Merging (Zac's approval, and since DEC-0200 Claude's pass may cover code)
runs the suite again and reverts the merge by itself on a new failure. Night School runs this nightly on small,
test-first exercises.

## 2. The protected list

The files she may never change, whatever passes: the lab and its rules, the action contract and undo, the safety
floor and escalation, child accounts, secrets, the password and memory vaults, Plaid, mail sending, the home link,
accounts, the communication gate, the server, `main.py`, deployment and CI, config, data, the decisions log,
requirements, the phone app, the development platform's own records and judges, and the creations' checks.
**Proposed additions for MIA OS:** `core/grants.py`, `core/kind_grants.py`, `core/stop.py`, `core/browser_safety.py`,
`core/action_effects.py`, `core/model_inspection.py`, the helper's operation list (Prompt 05) and the image's
definition (`os/`).

## 3. Rules

1. **Only through the lab.** No other path changes her code.
2. **Never her own judge:** the lab, the inspection, the grants and the tests that check them are protected.
3. **Test first, suite before and after, automatic revert.**
4. **Claude's pass merges** (DEC-0200); Zac sees every merge in a daily summary (Q-76) and can revert any.
5. **Small changes:** one fix or one capability per change, so a revert is clean.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-013 | No change to MIA's code shall reach the running MIA except through the lab's suite-before-and-after and merge with automatic revert. | Must | MVP | PC | Exists | T: lab tests | DEC-0225 → 09 |
| REQ-SLF-014 | A change touching a protected file shall be refused before it's tested, whatever its source. | Must | MVP | PC | Exists | T | DEC-0225 → 09 |
| REQ-SLF-015 | The protected list shall include her grant, stop, safety, inspection and effect rules. | Must | R1 | PC | New (the additions) | T | DEC-0225 → 09 |
