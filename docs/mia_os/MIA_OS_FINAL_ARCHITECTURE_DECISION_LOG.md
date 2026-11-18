# MIA OS: the final architecture decision log (Prompt 17 §12)

*Claude (Opus), 2026-11-18. Version 1.0. Generated from the records in `docs/DECISIONS.md`, which **govern** a
decision's status (DEC-0275). This log classifies every MIA OS decision (DEC-0154 onward), marks what is superseded,
and names what blocks the first milestone. `MIA_OS_DECISIONS.md` is the short index. Nothing here changes a
status: a recommendation becomes approved only by Zac.*

## 1. Summary

**Approved, revisable with evidence**: 68, **Recommended, awaiting Zac's approval**: 53, **Approved; open technical investigation**: 4, **Approved and fixed (foundational)**: 1.

**The five foundational decisions** (the Master Directive §3, DEC-0159) are fixed and were not reopened: Linux; MIA
first with a conventional desktop; hybrid, local-first intelligence; controlled autonomy; independent recovery.
Nothing in Prompt 17's review showed a technical constraint against any of them.

**Awaiting approval (53).** Many decisions from Prompts 05 to 16 were never put to Zac as their own
question. His answers approved the questions they were tied to, not each decision. They are listed as recommended
here, not silently treated as approved. Q-110 asks him to settle them as one batch.

## 2. Decisions that block the first milestone

| Decision | Blocks | Status |
|---|---|---|
| DEC-0263 | FW-01 | Recommended, awaiting Zac's approval |
| DEC-0275 | every package | Recommended, awaiting Zac's approval |
| DEC-0276 | the MVP gate | Recommended, awaiting Zac's approval |
| DEC-0279 | FW-01 | Recommended, awaiting Zac's approval |
| DEC-0277 | FW-05 | Recommended, awaiting Zac's approval |
| DEC-0278 | FW-03, FW-04 | Recommended, awaiting Zac's approval |
| DEC-0271 | the roadmap's order | Recommended, awaiting Zac's approval |

## 3. Superseded, in whole or in part

| Decision | Superseded |
|---|---|
| DEC-0157 | in part: the cage session by DEC-0191 and DEC-0227; dual boot by DEC-0272; SDDM by DEC-0278 |
| DEC-0168 | in part: the PC's dual boot by DEC-0272 |
| DEC-0164 | absorbed into DEC-0165 |
| DEC-0257 | its text: Zac's Q-95 answer (updates install by themselves at night) governs; corrected in REQ-OPS-001 and REQ-REL-023 |

## 4. Every MIA OS decision

| Decision | Title | Class | Status as recorded |
|---|---|---|---|
| DEC-0154 | MIA OS — the intelligence stays OS-independent; the OS is an environment for it | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16, answering Q-47: "yes") |
| DEC-0155 | The MIA Runtime — a long-running service, extracted first, on Windows | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Let's do the runtime extraction first. I want MIA OS asap"); next build step |
| DEC-0156 | Capabilities and grants for every tool and action | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-31: "Yes") |
| DEC-0157 | The PC image — Fedora Atomic (bootc), a cage MIA session plus KDE, dual boot first | Approved, revisable with evidence; superseded in part: the cage session by DEC-0191 and DEC-0227; dual boot by DEC-0272; SDDM by DEC-0278 | APPROVED (Zac, 2026-11-16, answering Q-47: "yes"), with its MIA session's compositor amended by DEC-0191 (test |
| DEC-0158 | System management only through a narrow privileged helper | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16, answering Q-47: "yes"); refined by DEC-0194 |
| DEC-0159 | MIA OS's five foundations, and who it's for | Approved and fixed (foundational) | APPROVED (Zac, MIA OS Master Directive §3; logging approved 2026-11-15: "Yes and yes") |
| DEC-0160 | Retire the Companion app; the phone app's signing key comes from secrets | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Yes we can retire the older phone app"; the signing change: "Yes") |
| DEC-0161 | The Life Enrichment Protocol is a major MIA subsystem | Approved, revisable with evidence | APPROVED as direction (Zac's handoff, 2026-11-15); the design comes through MIA OS Prompt 02 and its own plan |
| DEC-0162 | Smart Closet | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "an inventory of my clothes ... suggest outfits, let me rate them ... think of |
| DEC-0163 | MIA tells who's talking when two people speak to her | Approved, revisable with evidence | APPROVED as a requirement (Zac, 2026-11-15: "My wife and I might both speak to MIA at the same time and it |
| DEC-0164 | MIA's tools on anything you select, in any app | Recommended, awaiting Zac's approval; superseded absorbed into DEC-0165 | PROPOSED (Zac's idea, 2026-11-15: "highlight a section and right click it and be able to assign MIA to |
| DEC-0165 | The Universal Action Layer is a foundational MIA OS subsystem | Approved, revisable with evidence | APPROVED as direction (Zac's handoff, 2026-11-15: "a foundational MIA OS subsystem"); the build plan |
| DEC-0166 | Which Claude model does which work | Approved, revisable with evidence | APPROVED as direction (Zac, 2026-11-15: "lets designate those tasks going forward and we will switch models |
| DEC-0167 | One skills system, for the person and for MIA; "Build a skill" extends it | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "shouldn't this be an extension of the skills system she already has? ... yes to |
| DEC-0168 | MIA OS as soon as possible, on two machines: the PC (dual boot) and the Pi 5 | Approved, revisable with evidence; superseded in part: the PC's dual boot by DEC-0272 | APPROVED |
| DEC-0169 | On Linux, the system keeps the key to MIA's sealed files (the TPM where there is one) | Recommended, awaiting Zac's approval | PROPOSED (built 2026-11-15 so the dual boot isn't blocked; Zac to approve or change) |
| DEC-0170 | World Intelligence, a thin subsystem over what MIA already has | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Dec 0170 yes"), with DEC-0171's changes |
| DEC-0171 | Zac's answers on World Intelligence and MIA's own messages | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "There shouldn't be a limit on messages she starts herself for her os. But |
| DEC-0172 | Procurement & Opportunity Intelligence, World Intelligence's listings half | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Yes I approve lets build") |
| DEC-0173 | The Living System doctrine, adopted as invariants on what MIA already is | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Yes, copilot, Claude, ChatGPT and muse should be fine to use as independent checke |
| DEC-0174 | Who checks the work: Fable reviews Opus's; four others as independent checkers where it fits | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15: "Yes, copilot, Claude, ChatGPT and muse should be fine to use as independent checke |
| DEC-0175 | Capability-first application model; MIA's own apps stay in the runtime | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15), as the direction of his handoff "MIA Runtime-Owned Application Ecosystem & |
| DEC-0176 | Code that isn't MIA's runs out of process, sandboxed, through the capability contract | Approved; open technical investigation; the sandbox's proof of concept | APPROVED (Zac, 2026-11-15: "0176 yes"); the proof of concept approved for when grants exist (Q-28: "yes") |
| DEC-0177 | MIA in the OS image, Flatpak for GUI apps, signed extensions, no marketplace | Approved, revisable with evidence | APPROVED with Zac's clarification (2026-11-15, verbatim in prompt 22): MIA ships as an integrated, |
| DEC-0178 | Application manifests as JSON in apps/<id>/, a registry that reads them, code moved app by app later | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-30: "Yes") |
| DEC-0179 | What MIA OS is | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-32: "Yes") |
| DEC-0180 | How MIA OS requirements are judged | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-33: "Yes") |
| DEC-0181 | The autonomy model: five tiers, plus reversibility, reach and one stop | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-34: "We need to specify what stopping everything really means"; |
| DEC-0182 | The first MIA OS (the MVP) | Approved, revisable with evidence | APPROVED (Zac, 2026-11-15, answering Q-35: "Yes") |
| DEC-0183 | Glass is MIA OS's visual identity | Approved, revisable with evidence | APPROVED as direction (Zac's handoff, 2026-11-15: "Status: Approved Design Direction"; prompt 24). Which |
| DEC-0184 | The appearance engine: theme, colour scheme and layout on the existing engine | Recommended, awaiting Zac's approval | PROPOSED (the default preset and Muse's part answered: Q-37, Q-38) |
| DEC-0185 | MIA adjusts the greenhouse's controllers; a stop never touches the greenhouse | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16, answering Q-40: "MIA absolutely should be able to adjust greenhouse controllers but |
| DEC-0186 | Gold is allowed as an accent; rewards are legendary orange | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16, answering Q-41: "Allow gold") |
| DEC-0187 | Each app gets its own atmosphere colour, outside the meaning colours | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16, answering Q-42: "I like your proposed colors"); Muse may refine the values |
| DEC-0188 | Prompt 23 (Universal Intelligence) is built by growing what exists; the run record first | Recommended, awaiting Zac's approval | PROPOSED (Claude on Fable, 2026-11-16; Zac's handoff of 2026-11-15, prompt 23) |
| DEC-0189 | The Linux foundation: Fedora Atomic (KDE) as a bootc image from the repository; the distribution's kernel | Approved; open technical investigation; conditional on PoC 1 (the GPU under Fedora) | APPROVED (Zac, 2026-11-16, answering Q-47: "yes"), conditional on proofs of concept 1 and 2 as written; Ubuntu |
| DEC-0190 | MIA on the OS is a modular platform with one coordinator | Recommended, awaiting Zac's approval | PROPOSED; its one question to Zac answered (Q-51, 2026-11-16: "yes": MIA keeps running on the PC when he's sig |
| DEC-0191 | Wayland; two sessions at login; on the PC one compositor technology for both | Approved; open technical investigation; the compositor settled by PoC 3 | APPROVED as a direction (Zac, 2026-11-16, Q-48: "go with your recommendations"): test KDE's compositor and cag |
| DEC-0192 | Communication: HTTP and SSE for surfaces, D-Bus for the OS, events as "re-read" signals, no broker | Recommended, awaiting Zac's approval | PROPOSED (Claude on Fable, 2026-11-16, Prompt 05). New recommendation; answers T-02 and T-06. |
| DEC-0193 | Storage: Btrfs on LUKS2; XDG layout; her code in the image, his data in his home, models in /var | Recommended, awaiting Zac's approval | PROPOSED (Claude on Fable, 2026-11-16, Prompt 05). New recommendation. |
| DEC-0194 | Privilege: a helper only for what Linux would ask an administrator for, confirmed in the OS's own dialog | Recommended, awaiting Zac's approval | PROPOSED (Claude on Fable, 2026-11-16, Prompt 05). Refines DEC-0158. **Needs proofs of concept 5 and 6.** |
| DEC-0195 | Resources and observability from Linux's own mechanisms | Recommended, awaiting Zac's approval | PROPOSED (Claude on Fable, 2026-11-16, Prompt 05). New recommendation. |
| DEC-0196 | One browser: MIA's browser becomes Zac's everyday browser | Approved, revisable with evidence | APPROVED (Zac, 2026-11-16: Q-45, "My browser and MIAs browser should be the same i think"; Q-52, the four |
| DEC-0197 | The specialists run on local models able to do the engineering; MIA knows what he's working on | Approved, revisable with evidence | APPROVED |
| DEC-0198 | Teams as recommended (Q-54 to Q-58); growing the specialist roster stays a priority | Approved, revisable with evidence | APPROVED |
| DEC-0199 | MIA adds and refines her own specialists, learns online and works offline, and runs agents in parallel | Approved, revisable with evidence | APPROVED |
| DEC-0200 | Claude inspects MIA's models and specialists before they're used | Approved, revisable with evidence | APPROVED (his request); the split of who approves what is Claude's reading of it, for him to correct |
| DEC-0201 | The reference PC as built is MIA OS's first target | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0202 | Grow by nodes, not cards | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-64: "yes") |
| DEC-0203 | A hardware capability registry from Linux's own sources | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0204 | Linux schedules; MIA places models and orders the GPU queue | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0205 | The device family's tiers | Recommended, awaiting Zac's approval | PROPOSED; amended by Zac's answer to Q-66 ("yes all of the above", 2026-11-17): a laptop, a tablet and a |
| DEC-0206 | MIA is the program, not the model | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0207 | One provider interface; local first; cloud only on a per-request yes | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0208 | Routing in code from measurements | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0209 | MIA's own council on local models of different families | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0210 | Memory in her stores, one recall index beside them | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0211 | Voice stays local; whisper.cpp measured for the PC | Approved; open technical investigation; whisper.cpp measured on his voice before it replaces Vosk | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0212 | Three kinds of learning, each with its own gate | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17: "Yes to all your recommendations, however I am not too concerned about MIA knowing  |
| DEC-0213 | The action contract is the one execution boundary | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0214 | One task model | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0215 | Autonomy grows only by grants he gives | Approved, revisable with evidence | APPROVED as amended (Zac, 2026-11-17, Q-73: "MIA should offer an approve for now or Approve going forward opti |
| DEC-0216 | Risk computed in code sets the least tier | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0217 | Proactive help only through the gate | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-74 yes); no quiet hours (Q-75: "I don't need quiet hours.") |
| DEC-0218 | Done means read back | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0219 | Agents propose; the coordinator acts | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0220 | One capability truth registry | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0221 | Provenance on every self-statement | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0222 | Health and performance from Linux and her own counters | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-77 yes): she may restart her own services, reload a model or re-run a failed job  |
| DEC-0223 | Quality by code checks, corrections and fixed sets | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0224 | Investigations end in a reproducing test | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0225 | Self-development only through the lab | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-76 and Q-78 yes): her merged changes reach him as a daily summary, each with an U |
| DEC-0226 | New capabilities only through one path | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0227 | The shell is MIA's web front end in a full-screen window under KWin | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-79 yes): ordinary windows in MIA's session are switched from her own strip; KDE's |
| DEC-0228 | One navigation model | Approved, revisable with evidence | APPROVED as amended (Zac, 2026-11-17, Q-82: "the display is important and is for me and my wife to use"): the  |
| DEC-0229 | Unified search that never executes a change | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0230 | Context only by explicit share; workspaces restored through KWin | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0231 | Ambient, Workspace and Immersive as states of one shell | Approved, revisable with evidence | APPROVED (Zac, 2026-11-17, Q-80 yes): the second monitor shows the ambient view; "MIA should be adaptable and  |
| DEC-0232 | One notification pipeline | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0233 | Apps stay in the framework that suits them | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0234 | One design system for every device | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0235 | The identity holds without colour, transparency or motion | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-85 yes): a Light theme now; Graffiti and a Neon theme later. |
| DEC-0236 | Themes and personalisation are validated data, never code | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-83 "sure"): the Theme Studio may start from one of his pictures, with a readable  |
| DEC-0237 | The orb: one component, fourteen states | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0238 | Motion in three speeds, meaningful apart from decorative | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0239 | Spatial interfaces are views of the same capabilities | Approved, revisable with evidence | APPROVED as amended (Zac, 2026-11-18, Q-86: "I was thinking either an old android or the pi5"): the Zeta Astra |
| DEC-0240 | A small local audio identity | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-84 yes): listening on and off, "needs you" and errors on by default; done and mes |
| DEC-0241 | One MIA per person: the PC the hub, full engines that work alone | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-87 and Q-89): the Pi 5's first job is the household display on the TV (HDMI); the |
| DEC-0242 | Trust by pairing: one key per device | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0243 | Sync stays the three-way merge by record id | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0244 | HTTP and server-sent events over the home network or Tailscale | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-88 yes): away from home only through Tailscale, never an open port. |
| DEC-0245 | Thinking on the most capable reachable machine | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0246 | Controllers keep their loops and their safety | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0247 | A lost device is unlinked from anywhere | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-90 yes): an unlinked phone erases its MIA data when it next reaches the PC. |
| DEC-0248 | Authority comes only from the person | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0249 | Everything read from outside is data | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0250 | Identity in layers; approvals bound and used once | Approved, revisable with evidence | APPROVED as amended (Zac, 2026-11-18, Q-92: "no but it should offer it"): two-step sign-in is offered, never r |
| DEC-0251 | Four data classes | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-91 yes): sensitive data never to a cloud model, even on a yes. |
| DEC-0252 | Encryption in three layers | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0253 | Least privilege | Approved, revisable with evidence | APPROVED as amended (Zac, 2026-11-18, Q-94: "yes but should all be able to run locally by the time she is buil |
| DEC-0254 | Fail closed for changes; safety outside MIA; an audit trail that can't be rewritten | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-93 yes): the lockdown phrase included. |
| DEC-0255 | The OS boots without MIA; readiness in levels | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0256 | Each part its own unit, with restart limits, a watchdog and its own slice | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0257 | Whole-image updates at a restart he allows, rolled back by themselves | Approved, revisable with evidence; superseded its text: Zac's Q-95 answer (updates install by themselves at night) governs; corrected in REQ-OPS-001 and REQ-REL-023 | APPROVED (Zac, 2026-11-18, Q-95 as recommended): updates install by themselves at night when nothing's running |
| DEC-0258 | Data reliability in layers | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-97 as recommended): a UPS when convenient. |
| DEC-0259 | Backups in two places, restored monthly by a drill | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-96 and Q-98 as recommended): the second copy on an external drive and the laptop; |
| DEC-0260 | Plasma, safe mode and the previous deployment as the fallbacks | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0261 | Reliability objectives | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0262 | One repository, its layers enforced | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-99): the repository stays public for now, revisited when MIA OS ships. |
| DEC-0263 | A reproducible setup | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0264 | CI on every push is the gate | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-100): her merged changes are pushed with the daily summary, so CI tests them. |
| DEC-0265 | Releases built, signed and recorded; versions by date | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-101): a monthly release he approves, fixes sooner. |
| DEC-0266 | Tests in layers, AI quality included | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0267 | Store formats change additively; otherwise a versioned migration | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0268 | Several models build MIA, reviewed independently; Zac approves decisions | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0269 | Build MIA OS in stages, each usable and reversible | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-103): the approved features are built on Windows alongside the OS work. |
| DEC-0270 | The MVP is DEC-0182 plus the approved MVP-tier requirements | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-104, changed): R1 does every PC piece first, then the household display, then the |
| DEC-0271 | The critical path | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0272 | MIA OS on the new 4 TB drive; the Windows drive kept intact | Approved, revisable with evidence | APPROVED (Zac, 2026-11-18, Q-102): the Windows drive goes untouched into a USB enclosure. |
| DEC-0273 | Workstreams and work packages on the task board | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0274 | Every milestone has a gate Zac passes | Recommended, awaiting Zac's approval | PROPOSED |
| DEC-0275 | One hierarchy of authority for MIA OS documents | Recommended, awaiting Zac's approval | PROPOSED (Prompt 17) |
| DEC-0276 | The release ladder and a narrower MVP gate, with evidence levels | Recommended, awaiting Zac's approval | PROPOSED (Prompt 17) |
| DEC-0277 | Disk unlock: LUKS2, the TPM bound to PCR 7 with a PIN, and a recovery key | Recommended, awaiting Zac's approval | PROPOSED (Prompt 17) |
| DEC-0278 | The PC's login, MIA's session and what greenboot checks | Recommended, awaiting Zac's approval | PROPOSED (Prompt 17) |
| DEC-0279 | A reproducible, signed image build | Recommended, awaiting Zac's approval | PROPOSED (Prompt 17) |

## 5. The new decisions (records in `docs/DECISIONS.md`)

| Decision | Context | Recommendation | Consequence | Reversible |
|---|---|---|---|---|
| DEC-0275 | Codex F-01: nobody could tell which document governs | The blueprint, then the decision records, the requirement register, the domain specifications, the roadmap, research, history (`MIA_OS_ARCHITECTURE_DOCUMENT_INDEX.md` §1). A status changes in its record first; a superseded text gets a note pointing to what governs | One place to look | Yes |
| DEC-0276 | Codex F-03: an MVP gate of 254 Must requirements couldn't be audited | Releases MVP, Alpha, Beta, Stable; 67 of the 97 open Must · MVP requirements stay at the MVP gate, 26 move to Alpha and 4 to Beta, each with a work package; evidence recorded as in code, on Linux, on the image | A first install that can actually be proven | Yes |
| DEC-0277 | systemd-cryptenroll binds no PCRs by default; boot-chain PCRs break on every update | LUKS2; the TPM bound to PCR 7 (Secure Boot on, Fedora's keys) with a PIN; a printed LUKS recovery key; MIA's data key keeps its own name | A PIN at each boot (Q-106); no recovery prompt after updates | Yes (re-enrol) |
| DEC-0278 | Fedora 44 and later use Plasma Login Manager; the runtime isn't enabled; greenboot can't check a user service | Two login entries (MIA: `kwin_wayland` with her shell; Plasma). The runtime enabled at first sign-in. greenboot requires the OS's own checks and wants MIA's self-test run as a system one-shot on a throwaway folder. Four readiness levels | The default experience is testable in a VM | Yes |
| DEC-0279 | Codex F-04 and the technology check | The base pinned by digest; Python locked with hashes; `PySide6<6.12` until the WebEngine wheel ships; greenboot-rs added; Tailscale from its own repository; cosign with a key pair (bootc's policy can't match keyless identities reliably); Fedora's Ollama with upstream's build as the fallback | Two builds of a commit match | Yes |
