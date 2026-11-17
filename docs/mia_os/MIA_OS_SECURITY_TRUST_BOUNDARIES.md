# MIA OS: trust boundaries (Prompt 13 §4)

*Claude (Opus), 2026-11-18. Planning only.*

| # | Boundary | Crossing it requires | Enforced by |
|---|---|---|---|
| B1 | Outside world → MIA's context | nothing (reading is free), but it arrives marked as data | `untrusted()`, the UAL's marking, tool results labelled |
| B2 | Model → a change | a proposal on the contract, a card or a grant | `core/actions.py`, `core/grants.py` |
| B3 | A person → their records | their session (password, two-step away from the PC) | the server, `require_profile_id`, `view_for` |
| B4 | One person → another's records | not crossable (household stores shared only by joining) | personal / household stores |
| B5 | A device → the hub | its own key, scoped | `home_link`, sensor keys |
| B6 | MIA's runtime → the OS | the fixed-operation helper, the OS's password dialog (polkit) | DEC-0194 |
| B7 | MIA → a controller | an approved action to its own interface; its safety limits beyond | DEC-0246 |
| B8 | MIA → her own code | the lab, the protected list | `core/dev_lab.py` |
| B9 | His devices → the internet | outbound only; nothing listens publicly | Tailscale, `server.enabled` |
| B10 | Data → a cloud model | his yes, per request; never sensitive (Q-91) | the provider interface (DEC-0207) |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-011 | Each trust boundary shall be enforced in code at the point of crossing, never only by the model's instructions. | Must | MVP | All | Partial | T: a test per boundary | DEC-0248 → 13 |
| REQ-SEC-039 | When a session, grant or authorization can't be evaluated, a change shall not happen (it waits and says why), while reading, alarms and the safety floor carry on. | Must | MVP | All | Partial | T: fault-injection tests | DEC-0254 → 13 |
