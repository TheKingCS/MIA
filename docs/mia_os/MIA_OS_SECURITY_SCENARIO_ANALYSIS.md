# MIA OS: security scenarios (Prompt 13 §28)

*Claude (Opus), 2026-11-18. Each: threat, path, boundaries, controls, behaviour, audit, recovery, residual risk.*

| | Threat and path | Boundaries | Controls | Expected behaviour | Audit | Recovery | Residual |
|---|---|---|---|---|---|---|---|
| **A. Malicious webpage** | a page tells her to reveal memories or run commands | B1, B2 | marked as data; no tool that reveals private stores to a page; changes need a card; commits on his press only | she summarises the page; any proposal is a card he sees | the trace | none needed | low |
| **B. Malicious document** | a shared document carries instructions for an agent | B1, B2 | ingestion marks it; agents read-only; the coordinator proposes; cards | the agent notes it as content; nothing changes | the workspace, the trace | decline the card | low |
| **C. Unauthorized file access** | an app asks for private files | B3, app permissions | manifests limit stores; files only inside his MIA folder; the portal for others | refused, said | the action record | — | low |
| **D. High-impact operation** | paying a bill | B2, B3 | money is never grantable; a card each time, bound to its parameters | card → his approval → execute → record → undo where possible | the action record, history | undo / correct | low |
| **E. Lost phone** | stolen, maybe unlocked | B5 | unlink from the PC; sealed data; two-step on new sign-ins; erase on reconnect (Q-90) | access ends at once | the security log | re-pair a new phone | medium until it erases |
| **F. Compromised greenhouse controller** | it sends false data or tries other paths | B5, B7 | its key reaches only its snapshots; no command path into MIA; readings checked for range | odd readings flagged; nothing else reachable | sensor log | reflash, re-key | low |
| **G. Agent privilege escalation** | an agent asks another to do more | agents | roles read-only; scope only passes down; the coordinator proposes | refused | the run record | — | low |
| **H. Cloud model and sensitive data** | a task seems to need a bigger model | B10 | sensitive never sent (Q-91); personal only on a yes, minimised | done locally, or asked first | the request recorded | — | low |
| **I. Shared household device** | someone opens another's conversation on the display | B4 | the household key reads household stores only | refused: "ask on your own screen" | the security log | — | low |
| **J. Unsafe physical command** | a setpoint out of range | B7 | the action's range check, the node's limits, the MCU, interlocks | refused at the first check; recorded and told | action record, node log | — | very low |
| **K. Approval replay** | an old approval reused for a different change | B2 | bound to id, parameter hash, person, once, expiry | refused; a new card | the action record | — | low once REQ-SEC-016 is built |
| **L. Security service failure** | the grant check or session lookup fails mid-change | B2, B3 | fail closed (DEC-0254): no change; reading goes on; alarms and the safety floor unaffected | "I couldn't check that's allowed, so I didn't" | the Fix-It Log | retry | low |
