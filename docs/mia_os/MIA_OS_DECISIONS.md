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
| DEC-0163 | MIA tells who's talking | APPROVED as a requirement; low priority, not planned (Zac, 2026-11-17) |
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
| DEC-0188 | Prompt 23 built by growing what exists, no new service; the run record first | PROPOSED (Q-43 to Q-46) |
| DEC-0189 | The Linux foundation: Fedora Atomic (KDE) as a bootc image from the repository; the distribution's kernel; Ubuntu 26.04 the fallback | APPROVED (Q-47), conditional on PoC 1, 2 |
| DEC-0190 | MIA on the OS: a modular platform with one coordinator (the runtime the only writer) | PROPOSED; Q-51 answered yes |
| DEC-0191 | Wayland; two sessions at login; KDE's compositor for both on the PC, cage on the Pi | APPROVED as a direction (Q-48); PoC 3 decides |
| DEC-0192 | HTTP and SSE for surfaces, D-Bus for the OS, events as re-read signals, no broker | PROPOSED |
| DEC-0193 | Btrfs on LUKS2; XDG layout; her code in the image, his data in his home, models in /var | PROPOSED |
| DEC-0194 | A fixed-operation helper, each system change confirmed in the OS's own dialog; rules in the image | PROPOSED (Q-50; PoC 5, 6) |
| DEC-0195 | Resources and observability from systemd, the kernel and the journal | PROPOSED |
| DEC-0196 | One browser: MIA's browser becomes his everyday browser | APPROVED (Q-45, Q-52) |

## Proposed by Prompt 06 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0201 | The reference PC as built is MIA OS's first target; nothing to buy for the MVP | PROPOSED |
| DEC-0202 | Grow by nodes, not cards: the next AI hardware is a model-serving machine, when measured | APPROVED (Q-64) |
| DEC-0203 | A capability registry read only from Linux's own sources | PROPOSED |
| DEC-0204 | Linux schedules; MIA places models and orders the GPU queue, conversation first | PROPOSED |
| DEC-0205 | The device family's tiers; nothing depends on a later device | PROPOSED; laptop, tablet and smart display planned (Q-66) |

Full records: `MIA_OS_HARDWARE_TECHNOLOGY_EVALUATION.md` §3.

## Proposed by Prompt 07 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0206 | MIA is the program, not the model: identity, memory and decisions in her code and stores | APPROVED (2026-11-17) |
| DEC-0207 | One provider interface; local first; cloud for her own work only on a per-request yes | APPROVED (2026-11-17) |
| DEC-0208 | Routing in code from measurements, with a fallback chain | APPROVED (2026-11-17) |
| DEC-0209 | MIA's own council on local models of different families; disagreement kept | APPROVED (2026-11-17) |
| DEC-0210 | Memory in her stores, one recall index beside them, provenance on every memory | APPROVED (2026-11-17) |
| DEC-0211 | Voice stays local; whisper.cpp measured for the PC | APPROVED (2026-11-17) |
| DEC-0212 | Three kinds of learning, each with its own gate | APPROVED (2026-11-17) |

Full records: `MIA_OS_INTELLIGENCE_TECHNOLOGY_EVALUATION.md` §3.

## Proposed by Prompt 08 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0213 | The action contract is the one execution boundary, for apps, the system and devices | PROPOSED |
| DEC-0214 | One task model: goals, plans of steps with dependencies, every plan a run | PROPOSED |
| DEC-0215 | Autonomy grows only by grants he gives: Approve Once or Approve From Now On on every card | APPROVED as amended (Q-73) |
| DEC-0216 | Risk computed in code sets each kind's least tier; unknown is highest | PROPOSED |
| DEC-0217 | Proactive help only through the communication gate, triggered by records | APPROVED (Q-74); no quiet hours (Q-75) |
| DEC-0218 | Verification reads effects back; a model's "done" is never evidence | PROPOSED |
| DEC-0219 | Agents propose; the coordinator in code acts | PROPOSED |

Full records: `MIA_OS_AUTONOMY_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 09 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0220 | One capability truth registry | PROPOSED |
| DEC-0221 | Provenance on every self-statement | PROPOSED |
| DEC-0222 | Health and performance from Linux and her own counters | APPROVED (Q-77) |
| DEC-0223 | Quality by code checks, corrections and fixed sets | PROPOSED |
| DEC-0224 | Investigations end in a reproducing test | PROPOSED |
| DEC-0225 | Self-development only through the lab | APPROVED (Q-76, Q-78) |
| DEC-0226 | New capabilities only through one path | PROPOSED |

Full records: `MIA_OS_SELF_AWARENESS_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 10 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0227 | The shell is MIA's web front end in a full-screen window under KWin | APPROVED (Q-79) |
| DEC-0228 | One navigation model | APPROVED as amended (Q-82: the household display for him and his wife) |
| DEC-0229 | Unified search that never executes a change | PROPOSED |
| DEC-0230 | Context only by explicit share; workspaces restored through KWin | PROPOSED |
| DEC-0231 | Ambient, Workspace and Immersive as states of one shell | APPROVED (Q-80; flows to one monitor) |
| DEC-0232 | One notification pipeline | PROPOSED |
| DEC-0233 | Apps stay in the framework that suits them | PROPOSED |

Full records: `MIA_OS_DESKTOP_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 11 (2026-11-17)

| DEC | Title | Status |
|---|---|---|
| DEC-0234 | One design system for every device | PROPOSED |
| DEC-0235 | The identity holds without colour, transparency or motion | APPROVED (Q-85) |
| DEC-0236 | Themes and personalisation are validated data, never code | APPROVED (Q-83) |
| DEC-0237 | The orb: one component, fourteen states | PROPOSED |
| DEC-0238 | Motion in three speeds, meaningful apart from decorative | PROPOSED |
| DEC-0239 | Spatial interfaces are views of the same capabilities | APPROVED as amended (Q-86: an old Android or the Pi 5) |
| DEC-0240 | A small local audio identity | APPROVED (Q-84) |

Full records: `MIA_OS_VISUAL_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 12 (2026-11-18)

| DEC | Title | Status |
|---|---|---|
| DEC-0241 | One MIA per person: the PC the hub, full engines that work alone | APPROVED (Q-87: the Pi first the TV display; Q-89) |
| DEC-0242 | Trust by pairing: one key per device | PROPOSED |
| DEC-0243 | Sync stays the three-way merge by record id | PROPOSED |
| DEC-0244 | HTTP and server-sent events over the home network or Tailscale | APPROVED (Q-88) |
| DEC-0245 | Thinking on the most capable reachable machine | PROPOSED |
| DEC-0246 | Controllers keep their loops and their safety | PROPOSED |
| DEC-0247 | A lost device is unlinked from anywhere | APPROVED (Q-90) |

Full records: `MIA_OS_DISTRIBUTED_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 13 (2026-11-18)

| DEC | Title | Status |
|---|---|---|
| DEC-0248 | Authority comes only from the person | PROPOSED |
| DEC-0249 | Everything read from outside is data | PROPOSED |
| DEC-0250 | Identity in layers; approvals bound and used once | APPROVED as amended (Q-92: two-step offered) |
| DEC-0251 | Four data classes | APPROVED (Q-91) |
| DEC-0252 | Encryption in three layers | PROPOSED |
| DEC-0253 | Least privilege | APPROVED as amended (Q-94: all local when built out) |
| DEC-0254 | Fail closed for changes; safety outside MIA; an audit trail that can't be rewritten | APPROVED (Q-93) |

Full records: `MIA_OS_SECURITY_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 14 (2026-11-18)

| DEC | Title | Status |
|---|---|---|
| DEC-0255 | The OS boots without MIA; readiness in levels | PROPOSED |
| DEC-0256 | Each part its own unit, with restart limits, a watchdog and its own slice | PROPOSED |
| DEC-0257 | Whole-image updates at a restart he allows, rolled back by themselves | APPROVED (Q-95: at night) |
| DEC-0258 | Data reliability in layers | APPROVED (Q-97) |
| DEC-0259 | Backups in two places, restored monthly by a drill | APPROVED (Q-96, Q-98) |
| DEC-0260 | Plasma, safe mode and the previous deployment as the fallbacks | PROPOSED |
| DEC-0261 | Reliability objectives | PROPOSED |

Full records: `MIA_OS_RELIABILITY_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 15 (2026-11-18)

| DEC | Title | Status |
|---|---|---|
| DEC-0262 | One repository, its layers enforced | APPROVED (Q-99: public for now) |
| DEC-0263 | A reproducible setup | PROPOSED |
| DEC-0264 | CI on every push is the gate | APPROVED (Q-100) |
| DEC-0265 | Releases built, signed and recorded; versions by date | APPROVED (Q-101) |
| DEC-0266 | Tests in layers, AI quality included | PROPOSED |
| DEC-0267 | Store formats change additively; otherwise a versioned migration | PROPOSED |
| DEC-0268 | Several models build MIA, reviewed independently; Zac approves decisions | PROPOSED |

Full records: `MIA_OS_DEVELOPMENT_TECHNOLOGY_EVALUATION.md` §2.

## Proposed by Prompt 16 (2026-11-18)

| DEC | Title | Status |
|---|---|---|
| DEC-0269 | Build MIA OS in stages, each usable and reversible | APPROVED (Q-103) |
| DEC-0270 | The MVP is DEC-0182 plus the approved MVP-tier requirements | APPROVED (Q-104: PC first, display, laptop) |
| DEC-0271 | The critical path | PROPOSED |
| DEC-0272 | MIA OS on the new 4 TB drive; the Windows drive kept intact | APPROVED (Q-102) |
| DEC-0273 | Workstreams and work packages on the task board | PROPOSED |
| DEC-0274 | Every milestone has a gate Zac passes | PROPOSED |

Full records: `MIA_OS_IMPLEMENTATION_OPEN_QUESTIONS.md` §3.
