# MIA OS: capability priorities (Prompt 02 §14)

*Claude, 2026-11-15.*

*Categories:*
1. *Foundational*
2. *Essential*
3. *High value*
4. *Expansion*
5. *Advanced*
6. *Experimental*

*This is about importance and dependencies, not order. Order is Prompt
16's job.*

| Capability | Cat. | Why | Depends on | Exists? |
|---|---|---|---|---|
| Runtime service (scheduler, server host, store owner) | 1 | everything background depends on it; OS needs a service | — | no (R-01) |
| Key backend for Linux and Android | 1 | data must stay sealed on MIA OS | runtime | no (R-02) |
| Capabilities and grants | 1 | any system action, Send to MIA, LEP's online fetch | actions | no (R-05) |
| Actions, stores, identity, context | 1 | already the spine | — | yes |
| Online fetch policy | 1 | first routine background online use (LEP) | grants | no |
| Talk, tools, voice | 2 | MIA-first experience | model | yes |
| Speaker identification | 2 | two people speaking (DEC-0163) | voice, identity | no |
| Dashboard, missions, finances, calendar | 2 | daily use | services | yes |
| Smart Closet (minimum) | 3 | daily use, small, self-contained | weather, calendar | in progress |
| LEP: profiles, recreation catalogue, Spontaneous Mode, discretionary money | 3 | committed; mostly reuses services | money, places, weather | no |
| LEP: background discovery | 3 | needs the fetch policy and adapters | fetch policy | no |
| Send to MIA (phone) | 3 | small, high value | actions | no |
| Workspaces from projects | 4 | builds on projects | projects | partial |
| Cross-app planner | 4 | Prompt 08 | actions, grants | no |
| Project Japan (data now, property research later) | 4 | long-term | projects, money | no |
| System management (read, then act) | 4 | MIA OS proper | runtime, grants, privileged helper | no |
| Living Worlds phases 2–4, the Convergence | 5 | large | worlds | phase 1 |
| Spatial, wearables, neural | 6 | hardware | — | no |
