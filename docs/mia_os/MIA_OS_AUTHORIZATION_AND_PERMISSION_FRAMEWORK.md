# MIA OS: authorization and permissions (Prompt 13 §6)

*Claude (Opus), 2026-11-18. Planning only.*

## 1. Who may do what

| Subject | Permissions come from | Evaluated |
|---|---|---|
| A person | their account (adult; child accounts as built) | on every request (`require_profile_id`, `view_for`) |
| A device | its key's scope (DEC-0242) | on every request |
| An app | its manifest: tools, action kinds, stores it may write (`stores.write:<store>`), tiers | tests today (manifests claim exactly what the code has); at runtime when apps are separated |
| MIA herself | the tier of each kind + his grants (learned skills, published workflows, From Now On) | `grants.require()` before anything she starts |
| An agent | its role: read-only tools, its project's workspace | `core/specialists.py` roles |
| A sensor | one series | `core/sensors.py` |

## 2. Lifecycle of a permission

Granted (a card's Approve From Now On, teaching a skill, publishing a workflow, a manifest at install) → used
(recorded) → reviewed (listed with his grants; lapses after 90 days unused) → taken back (one press,
`grant.take_back`). **Never granted by anything MIA reads** (DEC-0156).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-014 | Every grant shall be listed with where it came from, lapse after 90 days unused, and be taken back with one press. | Must | MVP | All | Exists | T | DEC-0215, DEC-0248 → 13 |
| REQ-SEC-015 | An app shall write only the stores its manifest names, checked at runtime once apps run separately. | Must | R1 | All | Partial (tests) | T | DEC-0253 → 13, 05 |
