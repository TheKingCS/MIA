# MIA OS: intelligence security and privacy boundaries (Prompt 07 §17)

*Claude (Opus), 2026-11-17. Planning only. Prompt 13 designs security as a whole.*

| Threat | Boundary (exists unless marked) |
|---|---|
| Prompt injection from pages, files, emails, selections, other agents | outside text framed and marked; a turn that read it can't change a record in the same breath (`tool_loop.py`); nothing MIA reads can grant anything (DEC-0156) |
| A model asked to act | models propose; the action contract and grants decide; only a person approves outward or irreversible actions |
| His data reaching a cloud model | no cloud path in turns; the cloud adapter refuses without a consent token for exactly that content (REQ-INT-003, **new**) |
| A model inventing numbers | figure work goes through the worksheet; numbers traced to calculators (`specialist_work.py`) |
| Secrets in prompts | password fields never typed or read (`browser_safety.py`); the vault never in a prompt; logs scrubbed (the Fix-It Log's redaction) |
| Poisoned memory | a model can't write a confirmed memory; derived notes are marked and withdrawable |
| A malicious model file | models only from Ollama's library or a named source, checksummed; never code inside a model package |
| Crisis | the safety floor never depends on a model; numbers follow his country |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-033 | No model shall be able to approve, grant or execute an action; every action goes through the action contract and grants. | Must | MVP | All | Exists | T: the grants sweep | DEC-0156 → 07, 08 |
| REQ-INT-034 | Secrets (passwords, keys, card numbers, the recovery key) shall never enter a prompt. | Must | MVP | All | Exists (browser and vault rules) | T | → 07, 13 |
