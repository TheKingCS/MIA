# MIA: universal runtime contracts (Prompt 21, deliverable 4)

*Claude (Opus), 2026-11-18. Version 1.1, revised after independent reviews by Fable and Codex
(`MIA_LIVING_SYSTEM_REVIEW.md`). Planning only. These are the interfaces subsystems meet at, each starting from what
the code has. Proposed decisions:
- DEC-0280: trace ids;
- DEC-0283: one capability description;
- DEC-0285: sync's losing value kept, implementing the approved DEC-0243.*

## 1. The one boundary, and the four places a capability is described

Every change goes through the action contract:
- propose, approve, execute, record, undo (`core/actions.py`, DEC-0213);
- tiers from the manifests and grants (`core/grants.py`, `core/kind_grants.py`);
- reach and reversibility (`core/action_effects.py`).

It works and stays. A capability is described in four places:
1. the tool (`AssistantAction`, about 420 of them);
2. the action kind (`ActionType`, about 380);
3. its manifest (tier, outside text);
4. the effects table.

## 2. One description per capability (DEC-0283, proposed)

The four are **read together, not rewritten**. A check assembles one description per capability from them and fails
when they disagree, for example:
- a tool that proposes a kind with a different tier;
- a kind with no effect entry where it reaches beyond records;
- a tool marked outside with no outside tag.

Additions are made only where something uses them:

| Field | Today | Added |
|---|---|---|
| inputs | tools have a JSON schema; kinds a description of their parameters | nothing new; the check reports a kind whose tool's schema doesn't match its parameters |
| outputs | text | **unchanged**: structured outputs only for a capability whose result another step reads (the plan steps, a team's work), as each is touched |
| tier, reach, reversible, outside text | the manifest and the effects table | — |
| auth | scattered (vaults, device keys, connectors) | named for the kinds that need one, so a missing credential is said before trying |
| **deadline** | model calls only | **for device and outside reach only**, passed into the call that waits (most already take a timeout). Synchronous Python can't safely be cut off mid-write, so no deadline is imposed on record changes, which are fast and local |
| **cancel** | the stop between steps; `stop.stop_now` ends speech, a running skill and browser tasks | a cancel check inside long loops (a browser task, a file import), honoured by the stop; nothing interrupts a write |
| **read-back** (DEC-0218) | some flows re-read their effect | **one generic read-back for every change:** the records it says it touched still resolve (through the record-type registry, §3), and the files it wrote are the ones recorded. A capability-specific check only for device and outside reach (a sensor's state, a page committed) |
| errors | `ActionError` with words | four kinds named in the words he sees: refused (tier, grant, stop), invalid, unavailable (a service or device away), failed |
| audit | the history, change history, turn trace | the trace id (§4) |

New integrations still arrive as manifests and descriptions, and the runtime isn't changed to add one.

## 3. The record-type registry

Links, the history, recall, parity and loops each keep their own list of `kind:` names for `kind:id` references. One
registry (`core/record_types.py`, to be written) lists every record type with:
- its store;
- how to read one by id;
- its title and page;
- its class.

The others read it, and the generic read-back uses it. A test fails on a `kind:` it doesn't know.

## 4. Trace ids (DEC-0280, proposed)

A trace id is made at intake and carried on the thread-local context the undo log already uses
(`core/undo_log.py`) into:
- the turn trace;
- each proposal;
- each life event and change-history entry;
- the security log;
- a run.

It's kept in memory for a private turn, which is never traced (as today). The turn trace also records the prompt
template's version, so a regression can be tied to a prompt change.

## 5. A change that fails part way

`ActionCenter.approve` already records each file a change writes before writing it (`recording`). A change that
failed part way left its first writes in place, while saying "nothing was changed". **Fixed now (2026-11-18):** the
failure branch puts back every file it had written and re-reads the stores that read them, and the sentence is true.
No per-capability compensation framework is needed:
- a change inside MIA's records is restored from those before-images;
- a change that reached a device or outside is irreversible or compensable by its own declared effect (already in
  `action_effects.py`) and is said as such before it's approved.

## 6. Events

The bus stays synchronous and in-process (CLAUDE.md). Events name their record refs and trace id. Nothing durable is
added for noticed signals: at start, the state is re-derived from the stores (they're the current state), so nothing
device-only goes into the history, which syncs and is never rewritten.

## 7. Models: the provider contract

`LLMBackend` gains `embed` and `see` beside `generate` and `chat`. The model server's address comes from one setting
(`llm.base_url`) everywhere. Today at least ten modules call the server's API directly, most with the address written
in. The runtime's own calls move onto the backend (`meaning`, `recall_index`, `sight`, `paths`, `creation_maker`).
The development tools may keep their own client, reading the same setting.

## 8. Devices and sync (DEC-0285, proposed)

| Part | Today | Contract |
|---|---|---|
| What syncs | every personal `.json` file outside `NEVER_SYNC` | the retention registry's `syncs` column decides (memory §6). **Fixed now:** four device-only files had been syncing (what's noted on the PC, the recall index, runs, turn traces) |
| Merging | the three-way merge by record id (DEC-0243, approved, built) | unchanged |
| A field changed on both sides | one side wins (`prefer_local`); the other value is gone | **DEC-0243 as approved, built:** the losing value kept in the change history, one note naming the record and field (never quoting a sensitive value). No new clock: in the star topology (the device that travels drives, the hub answers), the three-way merge finds every conflict without one |
| A third full engine (the laptop, Beta) | — | the topology question is researched before it's built: whether the laptop syncs with the hub only (the star holds) or with the phone too |
| Handoff | conversations sync | a conversation's working state stays on its device; a question started on the PC is continued on the phone from the synced conversation |

## 9. Sandboxes

Code that isn't MIA's runs out of process, sandboxed (DEC-0176). Her own changes run in the lab's worktree as the
same user; that holds only because the protected list, the suite and Claude's pass do. On MIA OS the lab's runs move
into a Landlock-narrowed worker (Alpha).

## 10. What each contract is tested by

| Contract | Test |
|---|---|
| Capability descriptions | the four sources agree for every tool and kind |
| Record types | no `kind:` outside the registry |
| Trace | a turn that proposes and executes a change leaves one trace id in the turn trace, the proposal, the life event and the change history |
| A failed change | a change made to fail after its first write leaves that file as it was (`tests/test_authority_review.py`) |
| Provider | the model server's address read from one setting everywhere; no runtime module calls the server but the backend |
| Sync | a store missing from the retention registry fails; a field changed on both sides keeps the loser in the change history and opens one note |
