# MIA OS decisions register

*MIA's decisions live in `docs/DECISIONS.md` (the project's rule: only
Zac approves). This register lists the ones that belong to MIA OS and
their status.*

## Established by Zac (Master Directive §3; requirements)

| # | Decision |
|---|---|
| E1 | The foundation is Linux; no custom kernel without strong evidence |
| E2 | MIA-first experience; a conventional desktop is always available |
| E3 | Hybrid, local-first intelligence; useful offline |
| E4 | Proactive, with approval for consequential actions; observe, recommend, prepare and execute are kept apart |
| E5 | MIA boots by default, with a conventional desktop, recovery, safe mode and a no-AI path |

Logged as **DEC-0159** (2026-11-15), with who MIA OS is for: Zac, perhaps close friends later.

## Proposed (first pass, 2026-11-13; re-examined by later prompts)

| DEC | Title | Status | Re-examined in |
|---|---|---|---|
| DEC-0154 | Intelligence stays independent of the OS | PROPOSED | 04, 05 |
| DEC-0155 | MIA Runtime: a long-running service, extracted first, on Windows | PROPOSED | 05, 14, 16 |
| DEC-0156 | Capabilities and grants for every tool and action | APPROVED (Q-31, 2026-11-15); M4 built | 08, 13 |
| DEC-0157 | PC image: Fedora Atomic (bootc), a cage session plus KDE, dual boot | PROPOSED | 05, 06, 14 |
| DEC-0158 | System management only through a narrow privileged helper | PROPOSED | 05, 13 |

## Decided on 2026-11-15 (Zac's answers to Prompt 01)

| DEC | Title | Status |
|---|---|---|
| DEC-0159 | The five foundations, and who MIA OS is for | APPROVED |
| DEC-0160 | Retire the Companion app; signing key from secrets | APPROVED |
| DEC-0161 | The Life Enrichment Protocol | APPROVED as direction |
| DEC-0162 | Smart Closet | APPROVED |
| DEC-0163 | MIA tells who's talking | APPROVED as a requirement |
| DEC-0164 | Send to MIA on any selection | absorbed into DEC-0165 |
| DEC-0165 | The Universal Action Layer | APPROVED as direction; phases await approval |
| DEC-0166 | Which Claude model does which work | APPROVED as direction |
| DEC-0170 | World Intelligence | APPROVED; W1 built 2026-11-15 |
| DEC-0171 | Zac's answers on World Intelligence and MIA's own messages | APPROVED |
| DEC-0172 | Procurement & Opportunity Intelligence | APPROVED |
| DEC-0173 | The Living System doctrine, adopted as invariants on what MIA already is | APPROVED; L1 and L2 built 2026-11-15 |
| DEC-0174 | Fable reviews all Opus work; four independent checkers where it fits | APPROVED |
| DEC-0175 | Capability-first; MIA owns her app ecosystem, one manifest per app (prompt 22) | APPROVED |
| DEC-0176 | Code that isn't MIA's runs out of process, sandboxed, through the capability contract | APPROVED |
| DEC-0177 | MIA first-class in the OS image; MIA-native apps by the runtime, conventional apps by Flatpak; no app store | APPROVED (Zac's clarification) |
| DEC-0178 | Manifests as JSON in apps/<id>/, a registry that reads them, code moved app by app later | APPROVED; M1 built |

Prompt 01 makes no new decisions; it is an audit. Its findings support DEC-0155 (R-01) and DEC-0156 (R-05), but don't settle them.

## Proposed by Prompt 04 (2026-11-15)

| DEC | Title | Status |
|---|---|---|
| DEC-0179 | What MIA OS is | APPROVED (Q-32) |
| DEC-0180 | How requirements are judged; the principles' order | APPROVED (Q-33) |
| DEC-0181 | Autonomy: five tiers, plus reversibility, reach and one stop | APPROVED (Q-34, Q-40) |
| DEC-0182 | The first MIA OS (the MVP) | APPROVED (Q-35) |

DEC-0154 (intelligence independent of the OS), listed for re-examination in Prompt 04: the requirements rest on it
(REQ-ARC-003); recommended for approval with Prompt 05, which designs the adapters it calls for.
| DEC-0183 | Glass is MIA OS's visual identity; Aquatic (from Zac's picture) the default | APPROVED as direction (prompt 24, Q-37) |
| DEC-0184 | The appearance engine: theme, colour scheme, layout | PROPOSED |
| DEC-0185 | MIA adjusts the greenhouse's controllers; a stop never touches the greenhouse (amends DEC-0150) | APPROVED (Q-40) |
| DEC-0186 | Gold allowed as an accent; rewards are legendary orange | APPROVED (Q-41) |
| DEC-0187 | Each app's own atmosphere colour, outside the meaning colours | APPROVED (Q-42) |
