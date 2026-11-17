# MIA OS: intelligence acceptance criteria (Prompt 07 §24)

*Claude (Opus), 2026-11-17. Planning only.*

| The prompt's criterion | Met by |
|---|---|
| Existing infrastructure audited | the architecture document §2 (verified in the code) |
| Identity separated from models | DEC-0206, the identity document |
| Provider-independent architecture | DEC-0207, the provider abstraction |
| Local and cloud strategies | local inference; cloud only on a per-request yes |
| Routing documented | DEC-0208 |
| Council defined | DEC-0209 |
| Memory and context designed | DEC-0210; context engineering |
| Multimodal addressed | multimodal document |
| Voice established | DEC-0211 |
| Capability registration | the registry document |
| Quality measurable | the evaluation framework |
| Learning kinds distinguished | DEC-0212 |
| Provider lifecycle | the lifecycle document |
| Security boundaries | the security document |
| Observability | the observability document |
| Failure handling | the failure document |
| Technologies evaluated | the technology evaluation |
| Consistent with Prompt 06 | local inference uses DEC-0201 to 0204's hardware and queue |
| Records complete; questions and risks explicit | DEC-0206 to 0212; Q-68 to Q-72; R-45 to R-49 |

## Requirements REQ-INT-001 to 036

| IDs | Verified by | When |
|---|---|---|
| 001 to 004 | a call sweep; schema tests; the cloud adapter's refusals; trace fields | building the interface |
| 005, 006 | bench before and after; both models loaded | the cache setting |
| 007 to 009 | routing tests with fake registries | building the router |
| 010, 011 | council prompt assertions | the council |
| 012, 013 | identity sweep; store-only memory | exists |
| 014 to 018 | recall index tests | UI-5 |
| 019 to 021 | UAL, browser and Look tests | exists |
| 022 to 024 | voice measurements on his phrases | Q-70 |
| 025, 026 | registry tests | the registry |
| 027, 028 | evaluation sets | Night School |
| 029, 030 | forge refusals | the forge |
| 031, 032 | lifecycle tests | Prompt 14 |
| 033 to 036 | grants sweep; secrets tests; trace; the suite with no model | exists |
