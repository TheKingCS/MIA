# MIA OS: application framework requirements (Prompt 02 §16)

*Claude, 2026-11-15. Requirements for Prompt 03; no design is done here.*

## The kinds of app MIA has, or will have

| Kind | Today's example | Notes |
|---|---|---|
| MIA web app | most of the 102 pages (`web/`), data assembled in core | the main kind |
| Qt module | `modules/*` (classic view) | auto-discovered; secondary |
| Engine-only capability | sync, the gate, the Loop's reminders | no screen of its own |
| Background service | daily checks, backups; LEP discovery (planned) | needs a runtime scheduler |
| Device app | the Android app, glasses cards, greenhouse firmware | its own platform |
| External app | any Linux or Windows program on MIA OS | needs Send to MIA and system awareness |
| Agent-powered | the development council, Game Master | owner-only and gated |

## Requirements for Prompt 03

- AF-1 **Registration from code.** An app declares its id, name, destination, permissions and actions in one place. Today that is `core/web_surfaces.APPS` plus `ACTION_TYPES` plus the tools.
- AF-2 **Lifecycle.** Install, start, health, failure, update and remove, with an honest status ("installed, not working") in `core/capabilities.py`.
- AF-3 **Shared services only.** Apps use the services catalogue (calendar, money, weather and so on). Apps can't open another app's files.
- AF-4 **Actions are declared** with inputs, side effects, whether they're undoable, and what approval they need. They are exposed both as tools and as controls (parity).
- AF-5 **Permissions are declared** (reads, writes, goes online, uses the camera or microphone) and shown to the person.
- AF-6 **Background parts are declared separately** from the screen, with a schedule and resource limits.
- AF-7 **Each app declares the devices it supports** (DEC-0125: same functions, different presentation).
- AF-8 **Data has an owner.** Removing an app never silently deletes the person's data.
- AF-9 **Third-party apps run sandboxed** (R-04). First-party ones may stay in-process.
- AF-10 **Apps reach other apps through actions and events,** never by importing them. This is already the rule for modules.
- AF-11 **Every app works without the model.** AI is an extra.
- AF-12 **Apps outside MIA** (Linux or Windows programs) get MIA's tools through Send to MIA. Deeper control comes only through declared, granted capabilities.
