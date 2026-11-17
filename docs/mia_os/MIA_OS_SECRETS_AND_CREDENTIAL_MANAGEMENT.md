# MIA OS: secrets and credentials (Prompt 13 §17)

*Claude (Opus), 2026-11-18. Planning only.*

| Secret | Kept | Used by | Never |
|---|---|---|---|
| His passwords (the Passwords app) | the vault | him; autofill on his phone | spoken, on the glasses, in a log, in an action |
| Mail and bank credentials | the credentials vault | the mail drafter (reading), Plaid (deferred) | in actions, logs, exports, the undo log |
| Device keys | hashed on the hub, sealed on the device | requests | in logs |
| Tailscale | its own client | the network | in MIA |
| API keys for cloud models (the developer council) | the credentials vault, owner only | the council | in his records |
| The data key's recovery key | him, offline | restore | in chat, the repo, a log |

**Rules:** secrets never typed by her browser; never in the repository (it's public); `tests/test_no_secrets_in_logs.py`
on every log call; rotation on a suspected leak (incident response).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SEC-030 | No secret shall appear in a log, an action's parameters, an export, the undo log, speech or the glasses. | Must | MVP | All | Exists | T | DEC-0251 → 13 |
