# MIA OS central risk register

*Central register. Each risk's detail and evidence are in the prompt
report that found it. Rated H, M or L.*

| ID | Risk | Sev | Like | Source | Must be dealt with before | Owner |
|---|---|---|---|---|---|---|
| R-01 | Runtime lives in the Qt process | H | H | Prompt 01 | any OS work | Claude (engine) |
| R-02 | No Linux or Android key backend for at-rest sealing | H | H | Prompt 01 | data on Linux | Claude |
| R-05 | No capability or grant model for system actions | H | H | Prompt 01 | any system action | Prompt 08/13 |
| R-07 | No Linux CI | H | H | Prompt 01 | OS work | Prompt 15 **Partly met 2026-11-16:** the suite runs on Linux in `.github/workflows/mia-os-poc.yml` (on changes to the OS files) |
| R-06 | Test isolation: the at-rest key reset leaks between tests | M | H | Prompt 01 | Linux CI | Claude |
| R-04 | Unsandboxed modules and scripts | H | M | Prompt 01 | third-party apps | Prompt 03 proposes out-of-process extensions (DEC-0176); Prompt 13 designs the sandbox |
| R-08 | Builds aren't reproducible | M | H | Prompt 01 | image builds | Prompt 15 |
| R-12 | Docs drift, and a conflict over who MIA is for | M | H | Prompt 01 | Prompt 04 | Zac (Q-01) |
| R-19 | A release-signing weakness | M | L | Prompt 01 | soon | **mitigated by DEC-0160 once Zac adds the secrets** |
| R-03, R-09–R-11, R-13–R-18, R-20 | see `MIA_OS_TECHNICAL_DEBT_AND_RISK_REGISTER.md` | | | Prompt 01 | | |
| R-03 | Two Android apps | — | — | Prompt 01 | — | **closed: Companion app retired (DEC-0160)** |
| R-22 | LEP background discovery goes online routinely; scraping is fragile; sources change | M | H | Prompt 02 | building LEP discovery | Zac (Q-08), then adapters with tests |
| R-23 | Speaker identification errors could expose one partner's data to the other | H | M | Prompt 02 | shared conversation | MU-4/MU-5: ask when unsure; no approvals on an unidentified voice |
| R-24 | A process per sandboxed extension costs memory on the Pi | M | M | Prompt 03 | the extension host | the proof of concept measures it (Q-28) |
| R-25 | Each new app touches about fifteen files that tests check; without a scaffold this slows every addition | L | H | Prompt 03 | the next new app | `tools/new_app.py` (proposed) |
| R-26 | Scope grows faster than one person and his agents can build and maintain | H | H | Prompt 04 | each prompt's plan | Prompt 16 |
| R-27 | GPU compute on the chosen Linux base is worse than on Windows, or breaks on update | H | M | Prompt 04 | the switch | Prompt 06 |
| R-28 | Moving his data to Linux loses or corrupts something | H | M | Prompt 04 | the switch | Prompt 16 |
| R-29 | The MIA session quietly becomes the only practical way in | M | M | Prompt 04 | each release | Prompt 10/14 |
| R-30 | Performance targets set before the image prove wrong | M | H | Prompt 04 | R1 | Prompt 14 |
| R-31 | The small everyday model's mistakes reach actions | H | M | Prompt 04 | any new autonomy | Prompt 07/08 |
| R-32 | Requirements and code drift apart | M | H | Prompt 04 | each prompt | Prompt 17 |
| R-33 | Accessibility left to the end | M | M | Prompt 04 | R1 | Prompt 10 |
| R-34 | GPU compute on Fedora underperforms or breaks for the RX 7900 XTX | H | M | Prompt 05 | choosing the base | Prompt 06 (PoC 1); fallback Ubuntu 26.04 |
| R-35 | Fedora's bootc desktop path isn't finished; deriving from today's image changes under us | M | M | Prompt 05 | the image | PoC 2; Aurora's base as a stopgap |
| R-36 | KDE's compositor as a single-client session is unsupported and may break between releases | M | M | Prompt 05 | MIA's session on the PC | PoC 3; cage or an existing small compositor as fallbacks; Prompt 10 |
| R-37 | The root helper grows a general-purpose operation | H | L | Prompt 05 | every helper change | Prompt 13: a fixed list, reviewed; tests with hostile arguments |
| R-38 | A program he runs as himself can reach what MIA can (the limit of running as the person) | M | M | Prompt 05 | storing anything more sensitive | Prompt 13: sealing, credential binding, Flatpak, workers |
| R-39 | A Fedora rebase twice a year becomes a chore that gets skipped | M | M | Prompt 05 | each Fedora release | Prompt 15: an automated build and the acceptance list in a VM |
| R-21 | Scope: 17 prompts asking for ~300 documents could bury the engineering | M | M | review of the library | throughout | Claude: keep documents small, and merge where the directive allows ("avoid duplicating") |
| R-40 | The 7900 XTX underperforms or breaks under Fedora's ROCm | H | M | Prompt 06 | installing Fedora on the PC | PoC 1; Vulkan fallback; Ubuntu (DEC-0189) |
| R-41 | The 1 TB drive fills with models, packs and snapshots | M | H | Prompt 06 | dual boot | Q-65; REQ-HW-013 |
| R-42 | The one-slot PC can't hold a specialist and an independent reviewer at once | M | H | Prompt 06 | relying on independent review | DEC-0202; a different-family model that fits (benched first) |
| R-43 | Heat in a small case during long model runs | M | M | Prompt 06 | unattended overnight work on Linux | REQ-HW-024; measure on the image |
| R-44 | Hardware advice that doesn't fit the machine (happened 2026-11-17) | M | M | Prompt 06 | any recommendation | REQ-HW-009: advice reads the capability record |
| R-45 | Local models fall short and pressure grows to send his data to the cloud | H | M | Prompt 07 | any cloud use | DEC-0207's consent token; the model node first |
| R-46 | An Ollama or model update changes behaviour silently | M | H | Prompt 07 | every update | REQ-INT-027, 032 |
| R-47 | The recall index leaks a deleted or private record | H | L | Prompt 07 | UI-5 | refs only, re-read from stores; exclusions |
| R-48 | Reviews look independent but share a model family | M | H | Prompt 07 | relying on review | labelled; non-Qwen reviewers benched |
| R-49 | Context grows until answers slow and blur | M | M | Prompt 07 | the recall index | budgets; the trace |
