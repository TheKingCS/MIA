# MIA OS: offline first and degraded operation (Prompt 12 §12)

*Claude (Opus), 2026-11-18. Planning only.*

| Lost | Still works | Gone until it's back |
|---|---|---|
| The internet | everything local; the home network; sync at home | weather, World Intelligence, web lookups, Plaid (deferred), email |
| The PC (away, or off) | the phone: all records, actions, Talk on its own model, voice, glasses | the big model, the specialists' models, sync, Night School |
| The phone | the PC, the desktop | the glasses (they ride on the phone), location, the phone's camera |
| The greenhouse node | its own control loop and safety MCU, always | MIA's view of it, alerts from it |
| Ollama on the PC | every screen; code answers; her self-repair restarts it (DEC-0222) | answers in words |

**Said, not hidden:** the orb's unavailable state, the level line ("answered on the phone"), the status strip. **On
reconnecting:** sync runs, deferred messages are re-offered by the gate, "remind me when I'm back online" fires
(`core/online_watch.py`).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DST-016 | Losing the internet, the PC or the node shall be said plainly where it matters and lose nothing; work resumes and syncs on reconnecting. | Must | MVP | All | Exists | D | DEC-0241 → 12, 14 |
