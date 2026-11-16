# MIA OS: autonomy and trust requirements (Prompt 04, deliverable 7, with §11 and §16)

*Claude (Opus), 2026-11-15. Planning only. Row format: [SYSTEM_REQUIREMENTS](MIA_OS_SYSTEM_REQUIREMENTS.md) §1. The
autonomy model already exists in code since Zac approved DEC-0156 (`core/grants.py`, M4); this document states it as
requirements and adds what the OS needs. Prompt 08 designs agents on it; Prompt 13 secures it.*

## 1. The levels (§11), onto the tiers that exist

The prompt's seven levels map onto DEC-0156's five tiers without a new one. **Recommendation (DEC-0181, proposed):
keep the five tiers; add two properties instead of more levels**, because the seven mix two different things: how far
she may go (the tier), and who started it (the person or her).

| Prompt §11 level | Tier in code | On her own initiative |
|---|---|---|
| 1 Observe | `observe` | always |
| 2 Inform | `observe` | always (through the gate, at his pace) |
| 3 Recommend | `suggest` | always, marked as hers |
| 4 Prepare | `suggest` | always (drafts, plans, nothing sent or changed) |
| 5 Execute permitted actions | `act_within_grant` | only inside a grant (a learned skill, a published workflow) |
| 6 Request approval | `act_with_approval` | never; his yes each time, whatever was granted |
| 7 Restricted | `never` | never, even inside a skill |

**The two added properties** (New):

- **Reversibility:** each action kind is *undoable* (the undo log restores it), *compensable* (it can be reversed by
  another action, like unmarking a bill paid) or *irreversible* (sent, bought, deleted outside MIA). Irreversible is
  always shown before approval.
- **Reach:** *his records*, *a device*, *the system*, *outside* (another person, a shop, a site). A tier can't be
  lower than its reach allows: anything reaching outside or the system is `act_with_approval` at least.

**Information versus action** (§11): reading is governed by which stores a capability reads (`stores.read:*`, its
manifest's permissions); acting by the tier. A grant to act never implies a grant to read more.

## 2. Requirements

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-AUT-001 | Every tool and action kind shall carry one of five tiers (observe, suggest, act_within_grant, act_with_approval, never) in its app's manifest. | Must | MVP | All | Exists (M4) | T: `tests/test_grants.py` | DEC-0156 → 08 |
| REQ-AUT-002 | Anything the person presses or says themselves shall run as theirs; the grant check applies only to MIA's own initiative. | Must | MVP | All | Exists (`grants.decide`) | T | DEC-0156 → 08 |
| REQ-AUT-003 | On her own initiative MIA shall change the person's records only inside a grant, and never do what's tiered act_with_approval or never. | Must | MVP | All | Exists (`grants.require`, skills, workflows) | T | DEC-0156, E4 → 08 |
| REQ-AUT-004 | Grants shall be listed in one place with what each covers and how it was given, and each taken back by one action. | Must | MVP | All | Exists (Apps › Manage apps, `list_grants`, `grant.take_back`) | T | DEC-0156 → 08 |
| REQ-AUT-005 | No action, tool, page, mail or model output shall be able to create a grant. | Must | MVP | All | Exists | T: `tests/test_grants.py` | DEC-0156 → 13 |
| REQ-AUT-006 | Each action kind shall declare its reversibility (undoable, compensable, irreversible) and its reach (records, device, system, outside); irreversible ones shall say so in the approval sentence. | Must | R1 | All | New (undo exists; the declaration doesn't) | T: a test fails on an undeclared kind | §11 → 08 |
| REQ-AUT-007 | A kind whose reach is the system or outside shall be tiered act_with_approval or never. | Must | R1 | All | New | T | §11 → 08, 13 |
| REQ-AUT-008 | Every approval card shall show the exact change in code-written words before it runs; nothing runs from a model's description of itself. | Must | MVP | All | Exists (`describe` in each action type) | T | DEC-0013 → 08 |
| REQ-AUT-009 | An approval shall expire: a proposal unanswered for a day lapses; a standing grant lapses after 90 days of not being used, with a notice first. *(the 90 days provisional)* | Should | R1 | All | Partial: proposals lapse after a day; grant expiry New | T | §11 → 08 |
| REQ-AUT-010 | One command ("MIA, stop", a button always on screen) shall halt every running skill, workflow and agent at its next step and pause her own initiative until resumed. | Must | R1 | All | New | T: a running skill stops at the next step | §11 emergency stop → 08 |
| REQ-AUT-011 | A run in progress shall be cancellable by the person at any step, leaving completed steps recorded and undoable. | Must | MVP | All | Exists for skills (stop on "no"); New for plans | T | §11 → 08 |
| REQ-AUT-012 | Background autonomy (jobs, workflows, watches) shall be listed with when each last ran, what it changed and how to turn it off. | Must | R1 | All | Partial (jobs in health; workflows logged; one list New) | D | §11 → 08, 14 |
| REQ-AUT-013 | Settings that let MIA act alone (receipt auto-filing, World Intelligence on, a device granted) shall appear in the same list as grants. | Should | R1 | All | New (noted when M4 was built) | T | DEC-0156 → 08 |

## 3. Trust and transparency (§16)

**Three kinds of claim, said three ways:** *knows* (a record says so: "the payment was recorded at 3:10"), *believes*
(her reasoning: "I think the pump is undersized, because…"), *can't verify* ("I asked the thermostat but it didn't
confirm"). The kinds of knowledge are in [FUNCTIONAL](MIA_OS_FUNCTIONAL_REQUIREMENTS.md) §9 to §12.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-TRU-001 | Every change MIA made shall be listed in one history with what, when, why (the request or the job), which capability, which records and whether it can be undone. | Must | MVP | All | Partial: the history (`life_events`) and undo log exist; one page joining why and undo is New | T | P9, prompt 23 §6.2 → 08 |
| REQ-TRU-002 | "Undo what you did to X this afternoon" shall find MIA's changes to X in that window and undo them in reverse order, saying what couldn't be undone. | Should | R1 | All | Partial ("undo that" for the latest change) | T | prompt 23 §6.2 → 08 |
| REQ-TRU-003 | Every unprompted message and why it was sent or held shall be in the gate's log, readable by the person. | Must | MVP | All | Exists (`/api/why`, the gate's log) | T | DEC-0171 → 08 |
| REQ-TRU-004 | Every call to a model shall be logged with which model and provider answered and whether data left the device; the person can list cloud transfers. | Must | R1 | All | Partial (which level answered is said; no transfer list) | T | P7, P16 → 07, 13 |
| REQ-TRU-005 | When an operation fails, the person shall see what was attempted, what happened, what was left changed and what to do next, from records. | Must | MVP | All | Partial (failed proposals say why; Fix-It Log) | D: S-16 | P17 → 14 |
| REQ-TRU-006 | MIA shall never state success, a capability or a system state without a record or a reading behind it; asked how she knows, she names it. | Must | MVP | All | Partial (code-assembled answers; self-description from the registry) | T: FR-C1, REQ-AI-002 | §10 → 07, 09 |
| REQ-TRU-007 | Which apps, agents and devices MIA used for a request shall be visible on its answer. | Should | R1 | All | Partial (tools named in the tool loop) | D | §16 → 08 |
