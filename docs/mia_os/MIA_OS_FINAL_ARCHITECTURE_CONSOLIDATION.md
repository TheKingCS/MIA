# MIA OS: the final architecture consolidation (Prompt 17 §3)

*Claude (Opus), 2026-11-18. Version 1.0. One authoritative description per domain. Each cites the decisions that govern
it and the detailed document. Status uses the three evidence levels (DEC-0276): **code** (built and tested on
Windows or in CI), **Linux** (run on Linux), **image** (run on the MIA OS image).*

## 3.1 The Linux foundation

| Aspect | Authoritative design | Governs |
|---|---|---|
| Distribution | Fedora Kinoite 45, the ostree-native container run with bootc, pinned by digest; Ubuntu 26.04 the fallback if PoC 1 fails | DEC-0189 (conditional), DEC-0279 |
| Kernel | Fedora's, unmodified, never rebuilt | DEC-0189 |
| Boot | UEFI, Secure Boot, Fedora's signed shim, GRUB and kernel | DEC-0252, DEC-0277 |
| Init | systemd; MIA's units only Want, never Require | DEC-0255 |
| Graphics | Wayland; KWin; Plasma Login Manager with "MIA" and "Plasma" | DEC-0191, DEC-0227, DEC-0278 |
| Filesystem | Btrfs on LUKS2; `/var/home` his; the image read-only | DEC-0193 |
| Networking | NetworkManager; Tailscale only away from home | DEC-0244 |
| Hardware | the kernel's drivers; Fedora's ROCm for the GPU | DEC-0203 |
| Resources | systemd slices; the GPU queue ordered by MIA | DEC-0204 |
| Conventional desktop | Plasma, one choice at login, untouched by MIA's failures | DEC-0260 |
| **Status** | the image builds and passes lint (Linux); installs, boots, updates and rolls back headless (image, VM run 43872077107); graphical session, Secure Boot, encryption not yet | |
| **Uncertain** | the GPU under Fedora (HW-01); KWin as a one-app session (FW-03) | |

## 3.2 The runtime and services

| Aspect | Design | Governs |
|---|---|---|
| Responsibility | one runtime per person owns their stores, schedules their jobs, serves every surface | DEC-0155, REQ-ARC-004 |
| Boundaries | modular inside one process: apps through manifests and capabilities; out-of-process only for code that isn't MIA's | DEC-0175, DEC-0176, DEC-0190 |
| Communication | HTTP and SSE to surfaces; D-Bus to the OS; the event bus inside | DEC-0192 |
| Configuration | default config plus his overrides; per-person settings | CLAUDE.md |
| Lifecycle | a systemd user service; ready at "core"; watchdog | DEC-0256, DEC-0278 |
| Capability registry | the app registry and manifests; the capability truth registry at Alpha | DEC-0178, DEC-0220 |
| Observability | the journal; her counters; `/api/runtime/health` | DEC-0195, DEC-0222 |
| Errors | a broken module is skipped, never crashes; fail closed for changes | DEC-0254 |
| **Status** | code; Linux (up in the VM with 95 services, 434 tools, 11 jobs) | |
| **Not a monolith?** | one process, but apps are separable by manifest, and nothing outside MIA's own code runs in it | |

## 3.3 Intelligence and memory

| Aspect | Design | Governs |
|---|---|---|
| Identity vs models | MIA is the program (her stores, history, rules); models are replaceable settings | DEC-0206 |
| Providers | one interface; local first; cloud only per request with consent, never for sensitive data | DEC-0207, DEC-0251 |
| Local inference | Ollama: qwen2.5:14b everyday, 32k context, flash attention and the 8-bit cache | DEC-0206 to 0212, Q-68 |
| Routing | in code, from measurements | DEC-0208 |
| Council | MIA's own, local models of different families | DEC-0209 |
| Memory | his stores; one recall index beside them; memories kept only on "keep it" | DEC-0210, DEC-0054 |
| Context | facts assembled in code; the model only phrases | CLAUDE.md |
| Voice | local: Vosk now, whisper.cpp if measured better; Kokoro, Piper the fallback | DEC-0211 |
| Quality and learning | fixed sets, code checks, corrections; three kinds of learning, each gated | DEC-0212, DEC-0223 |
| **Status** | code (on Windows); the recall index a first slice built differently from its design (C-12) | |

## 3.4 Autonomy and agents

| Aspect | Design | Governs |
|---|---|---|
| Intent | the message's kind sorted in code | `core/message_kind.py` |
| Planning and tasks | one task model; agents propose, the coordinator acts | DEC-0214, DEC-0219 |
| Authorization | five tiers per action kind; grants learned or approved; Approve Once / From Now On | DEC-0156, DEC-0181, DEC-0215 |
| Execution | the action contract is the one execution boundary: propose, approve, execute, record, undo | DEC-0213 |
| Verification | done means read back | DEC-0218 |
| Failure | fail closed; say what was attempted and what's left | DEC-0254, REQ-TRU-005 |
| **Status** | code; the separation of intelligence, authorization and execution is enforced in code, not by prompts | |

## 3.5 Applications

| Aspect | Design | Governs |
|---|---|---|
| Model | capability-first: MIA's apps in the runtime, each with a manifest | DEC-0175, DEC-0178 |
| Lifecycle and discovery | discovered from `apps/` and `modules/`; status in the registry | DEC-0178 |
| Packaging | in the image (MIA's); Flatpak (others); no marketplace | DEC-0177 |
| Permissions | tiers in the manifest; a test fails on one without | DEC-0156 |
| App to app | only through capabilities, events, links and the history | REQ-FUN-041 |
| Extensions | ours only, sandboxed, out of process; later | DEC-0176, Q-94 |
| **Status** | code (57 manifests, 485 action kinds) | |

## 3.6 The desktop

| Aspect | Design | Governs |
|---|---|---|
| Shell | her web front end full screen under KWin, ordinary windows beside it | DEC-0227 |
| Navigation and search | one navigation model; search never executes a change | DEC-0228, DEC-0229 |
| Modes | Ambient, Workspace, Immersive as states of one shell | DEC-0231 |
| Notifications | one pipeline through the gate | DEC-0217, DEC-0232 |
| Settings | MIA's own, opening KDE's page for each system setting | REQ-DSK-023 |
| Fallback | Plasma; the recovery page | DEC-0260 |
| Accessibility | keyboard and Orca, text size, contrast, reduced motion (Alpha gate) | REQ-DSK-026, REQ-ACC-004 |
| Household | the Pi on the TV, a shared view he chooses (Beta) | DEC-0228, DEC-0241 |
| **Status** | code (the web front end, the ambient view); image: not yet (FW-03) | |

## 3.7 Visual identity

| Aspect | Design | Governs |
|---|---|---|
| Identity | glass; Aquatic the default; one cyan accent, gold accents, rewards legendary orange | DEC-0183, DEC-0186 |
| Themes | theme, colour scheme and layout as validated data, never code; the Theme Studio | DEC-0184, DEC-0236 |
| Holds without effects | the identity survives no colour, no transparency, no motion; a Light theme | DEC-0235 |
| The orb | one component, fourteen states | DEC-0237 |
| Motion | three speeds; never blocks input | DEC-0238 |
| Spatial | views of the same capabilities | DEC-0239 |
| Sound | a small local audio identity | DEC-0240 |
| Personalisation | cyberpunk and early-web self-expression through themes, inside the tier ranges | DEC-0236 |
| **Status** | code (themes, tokens, glass tiers); the orb's states and sounds planned (WP-06, WP-07) | |

## 3.8 Devices

| Aspect | Design | Governs |
|---|---|---|
| Model | one MIA per person; the PC the hub; full engines that work alone | DEC-0241 |
| Identity and trust | one key per device, its hash on the hub, paired on a trusted device | DEC-0242 |
| Sync | three-way merge by record id; unknown fields kept | DEC-0243, DEC-0267 |
| Transport | HTTP and SSE over the home network, Tailscale away | DEC-0244 |
| Inference placement | the most capable reachable machine | DEC-0245 |
| Controllers | keep their own loops and safety | DEC-0246 |
| Loss | revoked at once on the hub; erase best effort on reconnect | DEC-0247, Codex F-08 |
| **Status** | code (phone, glasses); per-device records and scopes partial (WP-10) | |

## 3.9 Security and privacy

See `MIA_OS_FINAL_SECURITY_AND_RELIABILITY_REVIEW.md`. Authority only from the person (DEC-0248); everything read from
outside is data (DEC-0249); identity in layers, approvals bound and used once (DEC-0250); four data classes, sensitive
never to a cloud (DEC-0251); encryption in three layers (DEC-0252, corrected by DEC-0277); least privilege (DEC-0253);
fail closed, safety outside MIA, the lockdown, an audit trail (DEC-0254).

## 3.10 Reliability and recovery

See the same review. The OS boots without MIA, readiness in levels (DEC-0255, four levels per C-07); each part its own
unit with limits and a watchdog (DEC-0256); night updates with automatic rollback (DEC-0257 as answered); data in
layers (DEC-0258); two backups, a monthly restore drill (DEC-0259); Plasma, safe mode and the previous deployment as
fallbacks (DEC-0260); the objectives (DEC-0261).

## 3.11 Development and release

One repository with its layers enforced (DEC-0262); a reproducible setup (DEC-0263, built by FW-01); CI as the gate
(DEC-0264, FW-02); signed monthly releases Zac approves (DEC-0265, FW-08); tests in layers (DEC-0266); additive store
formats (DEC-0267); several models, independent review, Zac decides (DEC-0268). Claude Code builds, Codex reviews,
ChatGPT plans and challenges (17b §6); no agent approves its own consequential change.

## 3.12 The roadmap

`MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` and `MIA_OS_FINAL_MVP_AND_RELEASE_DEFINITION.md`.
