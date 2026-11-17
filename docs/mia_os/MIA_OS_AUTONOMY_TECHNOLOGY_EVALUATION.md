# MIA OS: autonomy technology evaluation and decision records (Prompt 08 §25, §27)

*Claude (Opus), 2026-11-17. Planning only. DEC-0213 to 0219 are PROPOSED.*

## 1. Technologies

| Option | For | Against | Recommendation |
|---|---|---|---|
| MIA's own contract, runs and grants (exists) | deterministic, undoable, tested, per person | grown by hand | **Keep and extend** |
| Temporal / durable workflow engines | durable long workflows | a server and a second model of runs and permissions | **No**: the run record and atomic stores already give durability at his scale |
| n8n / Node-RED | visual automation, integrations | a second automation system beside workflows and grants; outside text paths | **No** for her own automation; Node-RED possibly inside the homestead, under the node |
| Agent frameworks (LangGraph, CrewAI, AutoGen) | ready multi-agent loops | they let models call tools directly; hide the execution boundary | **No**: agents propose, code acts (DEC-0219) |
| Model Context Protocol (MCP) | a standard way to expose tools | outside servers' tools would bypass tiers unless wrapped | **Maybe later**: as a provider of *read* tools, each tiered in a manifest |
| Home Assistant | many device integrations | another automation brain | **Maybe later**, as a device owner MIA asks, never as the decider |

## 2. Decision records

### DEC-0213: the action contract is the one execution boundary
Context: every change must be deterministic and undoable. Requirements: REQ-AGT-011 to 014, 033. Selected: every change
(apps, system, devices) is an action kind; models only propose. Rejected: direct model tool execution; a second path
for the OS. Reversibility: full. Reconsider: never for the boundary itself.

### DEC-0214: one task model
Requirements: REQ-AGT-004 to 006, 022, 029, 032. Selected: goals → plans of steps with dependencies → runs; engines
converge on the step model gradually. Rejected: a new orchestration service. Risks: migration effort (gradual).

### DEC-0215: autonomy grows only by grants he gives, offered with evidence
Requirements: REQ-AGT-015, 016, 020. Selected: tiers + grants; a trust ladder that offers (Q-73); never grantable:
money, messages, publishing, deletion outside undo, system. Rejected: self-promotion; time-based trust.

### DEC-0216: risk computed in code sets the least tier
Requirements: REQ-AGT-017. Selected: reach, reversibility, money, people, physical; unknown is highest; a sweep test.

### DEC-0217: proactive help only through the gate, from records
Requirements: REQ-AGT-018, 019, 021. Selected: the communication gate for everything unprompted; triggers from records;
what he's working on shapes relevance and timing only (Q-74); quiet hours (Q-75).

### DEC-0218: verification reads effects back
Requirements: REQ-AGT-002, 025, 027, 030, 031. Selected: after execute, code reads the store, page, device or system
state; a model's "done" never counts.

### DEC-0219: agents propose; the coordinator acts
Requirements: REQ-AGT-007, 008, 028. Selected: agents are roles with read-only tools writing to the workspace; only the
coordinator in code makes proposals on the contract.
