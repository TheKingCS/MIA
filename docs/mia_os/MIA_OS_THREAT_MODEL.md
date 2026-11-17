# MIA OS: threat model (Prompt 13 §3)

*Claude (Opus), 2026-11-18. Planning only. Threats and controls in general terms; specifics in `audit/` (local).*

## 1. What's protected

His whole life: money, health, journals, conversations, memories, locations, photos, passwords, his home's devices,
his greenhouse, and his family's shared things. Also MIA's own integrity: her code, her rules, her models.

## 2. Threats, most likely first

| # | Threat | Access needed | Path | Consequence | Protections (existing → proposed) | Detection | Recovery | Residual |
|---|---|---|---|---|---|---|---|---|
| T1 | **Content steering MIA** (a page, email, document, message, a model's own output) | none: he just reads it | text the model treats as an instruction | an unwanted change, a leak | marked as data, actions need a card, no grant from content → DEC-0249 everywhere | traces, the Fix-It Log | undo | low |
| T2 | **A lost or stolen phone or laptop** | the device | its storage, a live session | his records read | sealed stores, device keys revocable, two-step → erase on reconnect (Q-90), disk encryption | security log | unlink, re-pair | medium until disk encryption everywhere |
| T3 | **Someone guessing their way in** (another device on the network) | network reach | sign-in, device linking | an account | the doubling wait, two-step, Tailscale only away | the security log alerts | Sign Out Everywhere | low |
| T4 | **A mistake by MIA herself** (a model error) | — | a wrong proposal | an unwanted change | cards, tiers, grants never for money/messages/publishing/system, undo, the stop | the Fix-It Log, corrections | undo | low |
| T5 | **Secrets leaking** (logs, the repo, chat, the glasses, speech) | — | a value written where it shouldn't be | a credential exposed | tests on every log call, secrets never by voice or on the glasses, the public-repo rule | tests | rotate | low |
| T6 | **A malicious add-on or dependency** | a package or module installed | its code runs with MIA's rights | anything | modules only from here, the weekly OSV check → sandboxing, signed images | the dependency audit | remove, restore | medium |
| T7 | **A compromised home device** (a controller, a sensor, a camera) | that device | its key or its network | false readings; reaching MIA | single-purpose keys, read-only exports → network segment for IoT | late or odd readings | unlink, reflash | low |
| T8 | **MIA changing her own safeguards** | her lab | a self-made change | weaker rules | the protected list, the suite, revert, Claude's pass | the daily summary | revert | low |
| T9 | **Physical harm** (an unsafe greenhouse or equipment command) | a command path | a setpoint out of range | heat, water, power hazards | the safety MCU and controllers' own limits; MIA proposes only | the node's alarms | the hardware interlocks | low |
| T10 | **A cloud service seeing his data** | his yes to a cloud model | a request | private data outside | local first; cloud only on a yes per request → never for sensitive data (Q-91) | the audit | — | low |
| T11 | **Someone in the house reading another's private things** | a shared screen | the household display, a signed-in PC | privacy | per-person stores, household key sees household only | the security log | sign out | low |

## 3. Out of scope

A state-level attacker with physical access and time; side channels on the CPU; the security of Meta's, Google's or
Tailscale's own services (each is a dependency named in the supply-chain document).
