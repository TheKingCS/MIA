# MIA OS: platform services and their APIs (Prompt 03 §6)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).
Extends `MIA_OS_SHARED_SERVICES_CATALOG.md` (Prompt 02) with contracts; it doesn't replace it.*

## 1. Two ways in, one set of services

- **In-process (MIA's own apps):** the `AppContext` field (`context.calendar`, `context.communication`...), as today.
  No change.
- **Out of process (extensions, devices, surfaces):** one **local API**, versioned, the same contract the web screens
  already use: read with `/api/state` and each screen's `/api/<screen>`, change with `/api/actions` (propose →
  approve → execute → record → undo), know when to re-read with `/api/live`. Transport: HTTP today (the phone server,
  `server/app.py`, 277 routes); on MIA OS the same API over a Unix socket for local callers, and D-Bus only for
  desktop integration (portals, notifications, the global shortcut). Prompt 05 settles it (T-02).

## 2. The services, with their contracts

| Service | Purpose | In / out | Depends on | Security boundary | Failure | Core or optional |
|---|---|---|---|---|---|---|
| Identity and profiles | who's signed in, their own view (`view_for`) | profile id → scoped context | profile store | a caller only ever gets its own person's view | no profile: sign-in | core |
| Authentication and authorization | sessions, tokens, approval of actions | token → profile; proposal → decision | identity, the action contract | grants (DEC-0156) checked at the API | refused with why | core |
| Memory and context | what MIA knows; the life state | queries → records with sources | stores, links, the history | personal stores sealed; never another person's | a section missing is marked, not invented | core |
| Model access | one way to ask a model | prompt + purpose → text, with which model answered | `core/llm_manager.py` backends | apps never hold model keys; untrusted text framed | works without it (AF-11) | core (model optional) |
| Agents | specialists, the council, Game Master | task → result with sources | model access, capabilities | owner-only for dev agents | falls back or says so | optional |
| Voice | speech in and out | audio ↔ text | local models | on-device | text still works | optional per device |
| Notifications and the gate | MIA speaking up | candidates → decisions | the gate's log | paced, learned (DEC-0171) | logged, retried | core |
| Calendar and scheduling | events, alarms, the scheduler | records, jobs | stores | household store | jobs isolated | core |
| Search and indexing | find any record | words → records | `links.KINDS` catalogue | the person's own view | partial results | core |
| Files | documents, photos, the library | paths in MIA's home | `core/data_root.py` | inside MIA_HOME | — | core |
| Storage | the stores | records | atomic write, at-rest sealing, undo | one owner per store | a bad file set aside, store starts empty | core |
| Networking and connectivity | online or not; outward requests | status; fetch | `core/connectivity.py` | only declared, granted calls go out | online work waits (homeostasis) | core |
| Devices and hardware | sensors, the glasses, the phone | readings, commands | `core/sensors.py`, the relay | per-device keys; commands are actions | `missing_dependency` | optional |
| Smart home | Home Assistant and devices | states, actions | connectors (planned) | consequential actions approved | — | optional |
| Location and environment | places, weather | readings | places, weather | personal | unknown is said | optional |
| Workflows | multi-step skills | skill → runs | taught skills, the UAL | each step's own gate | stops where it fails | core |
| Logging and diagnostics | what happened | log, runtime health | the scheduler, the Fix-It Log | no personal words in logs | — | core |
| App management | manifests, status, the extension host | — | everything above | the only path to install code | — | core (proposed) |

## 3. Versioning and compatibility

- **The local API is versioned by path** (`/api/v1/...` once it serves out-of-process code; today's unversioned
  routes become v1 unchanged). A response may gain fields; a field is never repurposed or removed inside a version.
- **The capability contract is versioned per capability** (`world_watch.add@1`): parameters may be added with
  defaults; a breaking change is a new version kept beside the old for a deprecation period.
- **Deprecation:** announced in the capability registry with a date and a replacement; the parity and documentation
  tests already fail on undecided changes, and a contract test (proposed) fails when a published capability's schema
  changes without a new version.
- **Stores** get schema versions (T-03, Prompt 15): every store already migrates old records on load by ignoring
  unknown fields and defaulting missing ones (`pick` in each `_load`); a version number makes that explicit.

## 4. No duplication

Apps don't implement their own versions of these services: no app owns a model client (model access), sends its own
notifications (the gate), writes files outside the atomic write, or schedules its own timers. This is already the rule
(CLAUDE.md: the gate, the atomic write, the scheduler, no global singletons).
