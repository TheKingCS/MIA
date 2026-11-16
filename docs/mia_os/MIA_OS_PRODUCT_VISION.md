# MIA OS: product vision (Prompt 04, deliverable 2)

*Claude (Opus), 2026-11-15. Planning only. The experience MIA OS is for; what it is and why is
[MIA_OS_SYSTEM_PHILOSOPHY.md](MIA_OS_SYSTEM_PHILOSOPHY.md); what must be true is
[MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md).*

## Core value

One person's whole life (home, homestead, money, work, learning, health, projects) kept by one intelligence that
works on his own machines, knows his records, does the routine on its own with an exact undo, asks before anything
that matters, and keeps working when the internet or the model doesn't.

What he gets that a stock desktop with a chatbot doesn't:

1. **Outcomes across apps.** "Get the greenhouse ready for frost" becomes one plan over the greenhouse, the weather,
   needs, prices and the calendar, approved step by step (scenario S-05).
2. **Recall by meaning.** "That pump we compared last month" finds the needs, the prices and the conversation (S-04).
3. **A record of everything she did.** Each change listed with why, and undoable (REQ-TRU).
4. **Continuity.** Start on the PC, carry on from the phone or the glasses (S-15).
5. **Her own initiative at his pace.** She notices what's due, wrong or worth knowing, and learns how often he wants to
   hear it (DEC-0171).
6. **Offline.** Local models and local stores: the house, the homestead and his records work with the internet down
   (S-12).

## Where it's used (target environments)

| Environment | Today | MIA OS target |
|---|---|---|
| The PC (Ryzen 7 9800X3D, Radeon RX 7900 XTX 24 GB, 32 GB RAM, 1 TB NVMe) | Windows; MIA's desktop app opens her web front end | Linux image, MIA's session by default, KDE beside it (DEC-0157, proposed) |
| The phone (Android) | MIA's app with her engine inside (Chaquopy) and a small local model | Unchanged platform; a MIA endpoint, synced with the PC |
| Meta Display glasses | Cards and voice through the phone and a sealed relay | Unchanged; ambient surface |
| Raspberry Pi devices (later, DEC-0015) | Homestead node (`homestead/`), headless MIA Core | MIA Runtime as a service; embedded endpoints |
| His truck (later, Zac 2026-11-15) | — | Through the phone or a Pi with a screen and OBD-II |

## The three experience modes (§5; requirements in [UX](MIA_OS_USER_EXPERIENCE_REQUIREMENTS.md))

They are presentations of one runtime, not separate systems. Each device supports the modes its hardware allows.

- **Ambient:** MIA present without asking for attention: the orb, voice, a glance on the glasses, notifications paced
  by the gate, background jobs. Default on the glasses and the phone's lock screen; on the PC, a small presence beside
  other work.
- **Workspace:** ordinary productive computing: windows, files, apps, terminals, her web screens and KDE apps side by
  side, with her one shortcut away. A project can be opened as a workspace (`MIA_OS_WORKSPACE_AND_CONTEXT_MODEL.md`).
  Default on the PC.
- **Immersive:** full-screen or spatial: Living Worlds, the Dungeon, spatial dashboards, AR on the glasses later. On
  demand only, never a place he's put without asking.

## Defining capabilities (what must be there for it to be MIA OS, not Linux with a chatbot)

1. Boots into MIA; the desktop and recovery without her are one step away (E2, E5).
2. One capability registry, tiered and granted, behind every surface (DEC-0156, DEC-0175).
3. The action contract on every change: preview, approval where needed, record, undo.
4. Her records and their history and links, searchable by meaning, sealed at rest.
5. Local intelligence by default, replaceable providers.
6. Her apps registered, healthy or saying why not (M1 to M5, built).
7. The system's own state visible to her (inspection, DEC-0056) and changeable only through the helper.

## Long-term direction

**Realistic (the next years, on hardware he has or can buy):** the Linux image on the PC; the runtime on the Pi and
the homestead node; sync across devices; local models in the 14B to 32B class on the PC; the Universal Action Layer
on any selection (DEC-0165); Forge building small apps in the lab; speaker identification; a self-maintaining loop of
inspection, the lab and his approvals.

**Feasible later (needs work that isn't started):** spatial interfaces beyond the glasses' cards; MIA in the truck;
OS-level context (what's open, what's selected) with consent; cross-app automation of conventional Linux apps through
accessibility interfaces.

**Speculative (kept out of requirements):** dedicated MIA hardware; full AR environments; "hundreds of agents". None
of these shapes the first system.
