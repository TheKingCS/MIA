# MIA OS: data classes and privacy (Prompt 13 §14; DEC-0251)

*Claude (Opus), 2026-11-18. Planning only.*

| Class | Examples | Stored | Syncs | Local model | Cloud model | Shown on glasses / spoken |
|---|---|---|---|---|---|---|
| **Public** | news, plans, reference packs | as is | yes | yes | yes | yes |
| **Personal** | calendar, kitchen, projects, notes | sealed where listed | to his devices | yes | only on his yes, minimised | yes |
| **Sensitive** | health, money, journal, location history, relationships, conversations | sealed | to his devices | yes | **never** (Q-91) | only when he asks, never on the household display |
| **Secret** | passwords, keys, recovery codes, card numbers | vaults, own keys | only between devices holding the vault key | never | never | never |

**Minimisation for a cloud request** (personal only): the question and the few records it needs, names replaced
where they aren't needed, never a store's whole contents; the request and what was sent recorded for him.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-025 | Every store shall be assigned a data class, and the class shall decide its sealing, sync, model and display rules. | Must | R1 | All | Partial | T: a test that every store has a class | DEC-0251 → 13 |
| REQ-SEC-026 | Sensitive and secret data shall never be sent to a cloud model. | Must | MVP | All | Partial (cloud only on a yes) | T | DEC-0251 (Q-91) → 13, 07 |
