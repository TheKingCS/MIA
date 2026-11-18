# MIA OS: one MIA across many devices (Prompt 12)

*Claude (Opus), 2026-11-18, on Zac's go ("Lets do prompt 12"). Planning only: no device, link, sync or network
setting was changed. The prompt is `prompts/12_MULTI_DEVICE_DISTRIBUTED_MIA_ARCHITECTURE.md`. Twenty-five documents
sit beside this one (section 9).*

## 1. The headline

1. **MIA is already one MIA on two full engines and several endpoints.** The PC and the phone each run the whole
   engine (the phone through Chaquopy, with its own small model), linked once with his password; the phone uses the
   PC's bigger model whenever it can reach it, on the home Wi-Fi or through Tailscale (DEC-0022), and syncs both ways
   with a three-way merge by record id (`core/sync.py`). The glasses are an endpoint of the phone; sensors post one
   number each with their own key; the greenhouse node exports what it sees, read-only, and keeps its own control and
   safety. **The plan keeps this shape** (DEC-0241).
2. **The PC is the hub, not a server everyone depends on.** It holds the record of truth, the big models and the
   heavy work; every full engine works alone when it can't reach it, and catches up on reconnecting (DEC-0241,
   DEC-0243).
3. **A device is trusted only after he pairs it**, gets its own key, can be seen in Sign-ins and unlinked from any
   trusted device; a sensor's key can do one thing (DEC-0242).
4. **Devices talk over HTTP and server-sent events, on the home network or Tailscale, no open ports and no broker**
   (DEC-0244, extending DEC-0192).
5. **Thinking goes to the most capable reachable machine**: the PC's GPU, then a model node when one exists
   (DEC-0202), then the device's own model; his data never goes to a cloud model without his yes each time
   (DEC-0245, DEC-0207).
6. **Controllers own their loops and their safety.** MIA reads, explains and proposes; a change to a controller is
   an action on the contract, sent to the node's own interface, and "stop everything" never touches the greenhouse
   (DEC-0246, DEC-0185).
7. **A lost device is unlinked from anywhere, its data sealed with its own key, and a new one is paired and filled
   from the PC** (DEC-0247).

## 2. The audit (verified in the code, 2026-11-18)

| Part | Exists | State |
|---|---|---|
| PC engine and server | `core/application.py`, `server/app.py` on port 8765, `core/phone_server.py` (start, stop, Tailscale address) | **Working** |
| Phone engine | the Android app runs the whole Python engine (`Engine.kt`, `mia_phone.py`), its own model (llama.cpp, `OpenAIBackend`), its own server for its web screens | **Working** |
| Phone to PC link | `core/home_link.py`: pair with the person's password once, a device key (the PC keeps its hash), `/api/model/chat`, the level said each turn | **Working** |
| Linked devices | `core/linked_devices.py`: list, last seen (`core/phone_link.py`), unlink one, unlink all on sign out everywhere or a password change | **Working** |
| Sync | `core/sync.py`: phone-driven, the PC answers; per-person and household folders; three-way merge by record id; history merged by event id; XP added; files by fingerprint, both kept on conflict; `expect` versions | **Working** |
| Remote access | Tailscale (`tailscale status --json`), no port forwarding | **Working** |
| Glasses | Meta Display through the phone (`MetaGlasses.kt`, `GlassesService.kt`, `Relay.kt`, `GlassesCamera.kt`), the cards from `core/glasses.py` | **Working** (view, voice, camera) |
| Voice | Vosk and Piper on the PC; the phone's own (`PhoneVoice.kt`, `Voice.kt`); hold to talk | **Working** |
| Sensors | `core/sensors.py`: one series per key, a number at a time, rate-limited | **Working** |
| Greenhouse node | `homestead/` (its own control loop and safety MCU), `core/greenhouse_link.py` (read-only exports, live view on his network) | **Working**, read-only |
| Pi and Core edition | `core/device_profile.py` (Core vs Home by config), `core/device_framework.py` (USB and serial devices), `core/expedition_sync.py` (bundle export/import) | **Partial** |
| Capability registry | Prompt 06's design (DEC-0203); `MIA_OS_DEVICE_CAPABILITY_MATRIX.md` | **Planned** |
| Household display | Prompt 10 (Q-82: for him and his wife) | **Planned** |
| Laptop, tablet | Q-66 (planned) | **Planned** |
| Zeta Astralis | Q-86: an old Android or the Pi 5 first | **Planned** |

**Limits found:** sync is phone-to-PC only (no third full engine yet); a device key can't be scoped (a linked phone is
the person); the PC must be on for a phone's big-model answers; no device beyond phones appears in Sign-ins; the
glasses depend on the phone app being alive.

## 3. Who does what

| Layer | PC (hub) | Phone | Glasses | Pi nodes | Controllers, sensors |
|---|---|---|---|---|---|
| Records of truth | yes | a full copy, synced | none | its own (expeditions), synced or bundled | none |
| Engine and actions | yes | yes | no (the phone's) | yes (Core edition) | no |
| Models | big (GPU) | small, offline | none | small (AI HAT) | none |
| Control loops and safety | no | no | no | the greenhouse node's own | yes, their own |
| Interface | desktop shell | phone screens | cards, voice | kiosk, household display | none |

## 4. Decisions (records in `MIA_OS_DISTRIBUTED_TECHNOLOGY_EVALUATION.md` §2)

| DEC | Decision | Status |
|---|---|---|
| DEC-0241 | One MIA per person: the PC the hub, full engines that work alone, endpoints that don't keep records | PROPOSED |
| DEC-0242 | Trust by pairing: one key per device, listed and revocable from any trusted device; single-purpose keys for sensors | PROPOSED |
| DEC-0243 | Sync stays the three-way merge by record id, driven by the device that travels; history merged by event id | PROPOSED |
| DEC-0244 | HTTP and server-sent events over the home network or Tailscale; no open ports, no broker | PROPOSED |
| DEC-0245 | Thinking on the most capable reachable machine; the device's own model the floor; no cloud for his data without his yes | PROPOSED |
| DEC-0246 | Controllers keep their loops and safety; MIA reads, explains and proposes; changes are actions to the node's own interface | PROPOSED |
| DEC-0247 | A lost device is unlinked from anywhere and its data stays sealed; a new one is paired and filled from the hub | PROPOSED |

## 5. Questions for Zac

`MIA_OS_DISTRIBUTED_OPEN_QUESTIONS.md`: Q-87 (what the Pi 5 does first), Q-88 (away from home only through
Tailscale), Q-89 (the laptop as a full engine like the phone), Q-90 (a lost phone's MIA data erased when it next
connects).

## 6. Boundaries

Prompt 13 designs identity, encryption and permissions in full; Prompt 14 updates and recovery; Prompt 16 the order
of building.

## 7. Sources

The repository, read 2026-11-18 (each module above); DEC-0015, 0019, 0022, 0126, 0150, 0185, 0191, 0192, 0202 to
0208, 0228. Technology sources in the technology evaluation.

## 8. What it means for him

Nothing he uses today changes: the phone keeps working without the PC, and talks to it when it can. What's added is
more devices doing the same: the household display, the Pi, the laptop, a forearm screen, each paired once, each
listed, each able to be taken back.

## 9. The documents

`MIA_OS_MULTI_DEVICE_STRATEGY.md`, `MIA_OS_DEVICE_CLASS_AND_RUNTIME_ARCHITECTURE.md`,
`MIA_OS_DEVICE_IDENTITY_AND_REGISTRATION.md`, `MIA_OS_DEVICE_DISCOVERY_AND_CAPABILITY_REGISTRY.md`,
`MIA_OS_DISTRIBUTED_INTELLIGENCE_ARCHITECTURE.md`, `MIA_OS_DISTRIBUTED_MEMORY_AND_CONTEXT.md`,
`MIA_OS_DEVICE_COMMUNICATION_ARCHITECTURE.md`, `MIA_OS_NETWORK_AND_REMOTE_ACCESS_ARCHITECTURE.md`,
`MIA_OS_OFFLINE_FIRST_AND_DEGRADED_OPERATION.md`, `MIA_OS_DISTRIBUTED_APPLICATION_ARCHITECTURE.md`,
`MIA_OS_CROSS_DEVICE_SESSION_CONTINUITY.md`, `MIA_OS_DISTRIBUTED_AGENT_EXECUTION.md`,
`MIA_OS_HOME_AND_HOMESTEAD_DEVICE_INTEGRATION.md`, `MIA_OS_DATA_SYNCHRONIZATION_AND_CONSISTENCY.md`,
`MIA_OS_DEVICE_RESOURCE_AND_POWER_COORDINATION.md`, `MIA_OS_DISTRIBUTED_VERSIONING_AND_COMPATIBILITY.md`,
`MIA_OS_DISTRIBUTED_OBSERVABILITY.md`, `MIA_OS_DISTRIBUTED_SECURITY_REQUIREMENTS.md`,
`MIA_OS_DEVICE_LIFECYCLE_AND_RECOVERY.md`, `MIA_OS_DEVICE_SUPPORT_MATRIX.md`,
`MIA_OS_DISTRIBUTED_ARCHITECTURE_DIAGRAMS.md`, `MIA_OS_DISTRIBUTED_END_TO_END_SCENARIOS.md`,
`MIA_OS_DISTRIBUTED_TECHNOLOGY_EVALUATION.md`, `MIA_OS_DISTRIBUTED_ACCEPTANCE_CRITERIA.md`,
`MIA_OS_DISTRIBUTED_OPEN_QUESTIONS.md`.

## Security (Prompt 13, 2026-11-18)

Device keys, scopes and the lost-device path are in `MIA_OS_DISTRIBUTED_DEVICE_SECURITY.md`; the household key in `MIA_OS_HOUSEHOLD_PRIVACY_AND_ACCESS_CONTROL.md`.

## Reliability (Prompt 14, 2026-11-18)

Each device's recovery: `MIA_OS_DISTRIBUTED_DEVICE_RELIABILITY.md`.

## Engineering (Prompt 15, 2026-11-18)

The phone app and the Pi image are built and signed in CI (`MIA_OS_BUILD_SYSTEM_ARCHITECTURE.md`).

## Implementation (Prompt 16, 2026-11-18)

After the move the phone re-pairs and resets its sync base (`MIA_OS_USER_DATA_AND_MIGRATION_CONTINUITY.md`, REQ-IMP-005).
