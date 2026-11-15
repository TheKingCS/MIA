# MIA OS: how applications work together (Prompt 03 §7)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

## 1. The rule (exists)

**An app never imports another app or reads its files.** It cooperates through five shared mechanisms, each already
in MIA:

| Mechanism | What it's for | Where | Cross-process (proposed) |
|---|---|---|---|
| **Capabilities through the action contract** | asking another app to do something | `core/actions.py`, the tool registry | the local API's `/api/actions` |
| **Events** | telling whoever cares that something happened | `core/event_bus.py` (synchronous, in-process) | `/api/live` (exists: a change signal); typed events over it |
| **Links** | saying how records relate, by `kind:id` | `core/links.py` | the same refs in API responses |
| **The history** | what happened, for anyone to read | `core/life_events.py` | read through the API, filtered to the caller's grants |
| **The life state / screen data** | reading another app's facts | `core/context_assembler.py`, `/api/state`, each `/api/<screen>` | the same endpoints |

## 2. The prompt's examples, as they'd work

| Example | How |
|---|---|
| Calendar asks Finance for schedule information | Calendar reads the life state's money section (bills due), never the budget's file |
| Greenhouse asks for sensor readings | it reads `core/sensors.py` through its service; a device's reading is a capability |
| MIA runs an approved smart-home action through the Home app | MIA proposes the Home app's action kind; it executes on approval, recorded with undo |
| Learning asks another learning capability for progress | `core/paths.stats` through its tool or the life state, not its store |
| MIA coordinates several apps for a larger task | a taught skill (or the UAL's multi-step actions): each step a capability through its own gate; the run is recorded |

## 3. Workflows and handoffs

A multi-app task is a sequence of capabilities, owned by the taught-skills engine (`core/taught_skills.py`), not by
any one app. Each step keeps its own gate; a step that needs approval waits; a step that fails stops the run with
where. Data passes between steps as values the step returned, never as another app's file. Controlled file exchange
goes through MIA's file service (inside MIA_HOME) or, for external apps, the XDG file chooser and document portal.

## 4. Authentication, authorization, logging

Every cross-app call is a capability invocation, so it's authenticated (the caller's session or the runtime itself),
authorized (the action contract's approval; grants per capability, DEC-0156), logged (the proposal record, the
history, the undo log) and monitored (the loops over action families, `ACTION_KINDS` failures). **Belonging to MIA
gives no access by itself** (prompt §7): an extension calling another app's capability needs that capability granted.

## 5. Gaps

- Events are in-process only; out-of-process callers get a "something changed" signal (`/api/live`), not which
  event. Typed events over the live channel are proposed with the local API (Prompt 05).
- The event bus is synchronous by design (CLAUDE.md); a slow subscriber slows the publisher. Fine in one process;
  across processes, delivery must be asynchronous and at-least-once with idempotent handlers (Prompt 05).
