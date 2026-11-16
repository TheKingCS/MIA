# MIA OS: capability classification (Prompt 02 §5)

*Prompt 04 (2026-11-15): requirements now live in [MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md) and [MIA_OS_FUNCTIONAL_REQUIREMENTS.md](MIA_OS_FUNCTIONAL_REQUIREMENTS.md); the OS, platform, app and AI split is §25 there.*

*Prompt 03 classifies applications, capabilities, agents, skills, extensions, connectors and the rest: [MIA_OS_APPLICATION_MODEL.md](MIA_OS_APPLICATION_MODEL.md). The capability is the unit MIA invokes.*

*Claude, 2026-11-15.*

*Roles:*
- *A: core platform service.*
- *B: operating-system capability.*
- *C: native application.*
- *D: background service.*
- *E: AI-powered capability.*
- *F: specialised agent.*
- *G: interface environment.*
- *H: external integration.*

*Status is from `MIA_OS_FEATURE_INVENTORY.md`. Committed and Proposed are
as defined in the ecosystem report.*

| Capability | Primary | Secondary | Depends on | Status |
|---|---|---|---|---|
| Identity, profiles, sign-in, households | A | — | stores, crypto | Verified |
| Stores, atomic writes, undo, life events, links | A | — | filesystem | Verified |
| Action contract (propose, approve, execute, record, undo) | A | — | stores | Verified |
| Communication gate | A | D | notifications | Verified |
| Notifications and push | A | D | pywebpush | Implemented |
| Search (Ctrl+K providers) | A | E | providers | Implemented |
| Sync and home link | A | D | network, Tailscale | Verified (tests) |
| Model routing (three levels) and the model registry | A | E | Ollama, llama-server | Implemented |
| Presence and context assembly | A | E | stores | Verified |
| Safety floor | A | — | region | Verified |
| Encryption at rest, backups | A | D | DPAPI (Windows only) | Partial |
| Scheduler (daily checks, the Loop) | D | A | Qt today (R-01) | Implemented |
| Device framework, cameras, serial, power | B | D | hardware | Implemented |
| Inspection, self-knowledge, service map | E | B | code, stores | Verified |
| Browser with a commit gate | E | B | Playwright | Implemented |
| Conversation (Talk) | E | G | model, tools | Verified (scripted) |
| Game Master | E | — | Dungeon, Loop | Implemented |
| Fix-It Log | D | E | turns | Verified |
| Development council, work agents, lab | F | E | cloud AI accounts, git | Experimental |
| Dashboard | C | G | many services | Verified |
| Calendar, notes, journal, reminders | C | — | stores | Verified |
| Missions, projects, the Loop, the Dungeon, XP | C | D (Loop reminders) | calendar, finances | Verified |
| Finances, businesses | C | H (Plaid) | Plaid | Verified offline |
| Kitchen, maintenance, garage, property | C | — | stores | Verified / Implemented |
| Homestead and greenhouse | C | D (sensors), B (nodes) | firmware | Implemented |
| Workouts, learning paths, Trade Master, Classroom | C | E (tutoring) | stores | Verified |
| Memory Vault | C | E (captions) | phone photos | Implemented |
| **Smart Closet** | C | E (suggestions), D (weather-aware morning card) | weather, calendar, Loop, Memory Vault photos | Committed; minimum version in progress |
| **Life Enrichment Protocol** | C | D (discovery), E (planning), H (event sources) | places, weather, calendar, finances, Memory Vault, gate, online sources | Committed |
| **Speaker identification** | A | E | microphone, voice models | Committed |
| **Send to MIA on a selection** | B | E | OS hooks (Android PROCESS_TEXT, Windows hotkey), action contract | Proposed (DEC-0164) |
| Voice (speech to text, text to speech) | A | B | Vosk, Piper, Kokoro, Android | Implemented |
| Living Worlds, the Nexus | G | C | stores | Experimental |
| The Convergence | G | — | Living Worlds | Planned |
| Glasses cards, the relay | G | H (Meta, Cloudflare) | phone | Implemented |
| Ambient, Workspace, Immersive modes | G | — | desktop (Prompt 10) | Planned |
| Online lookup, weather fetch | H | E | network | Implemented |

**The ambiguous cases:**
- **LEP is primarily an app (C)**, though its discovery job is a background service. It is kept as one app so its data has one owner.
- **Speaker identification is a platform service (A), not a feature of the Talk app.** Every voice surface needs it: PC, phone, glasses and the Pi.
- **"Send to MIA" is an OS capability (B).** It must exist outside MIA's own windows to be useful.
- **The development council is an agent (F).** It is owner-only and, unlike everything else, reaches cloud models.
