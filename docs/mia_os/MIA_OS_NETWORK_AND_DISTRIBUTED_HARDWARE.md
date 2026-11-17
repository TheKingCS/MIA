# MIA OS: network and distributed hardware (Prompt 06 §11)

*Claude (Opus), 2026-11-17. Planning only. The distributed architecture is Prompt 12's; this sets the hardware it
runs on. Networking foundation: Prompt 05's hardware abstraction §5.*

## 1. What exists (verified on the PC)

2.5 GbE wired (connected), Wi-Fi 6E (off), Bluetooth, and Tailscale (connected) joining the PC, the phone and later
the Pis privately (REQ-DEV-003). The glasses reach MIA through the phone.

## 2. The node network

```
            Tailscale (encrypted, his own)                     home LAN (2.5 GbE / Wi-Fi)
 Phone ◀──────────────────────────────▶ PC (the coordinator) ◀──────────▶ Model node (proposed, DEC-0202)
   ▲ glasses (BLE, Meta toolkit)          ▲                                  ▲
                                           │ MQTT/HTTP                         │ asks only for inference
                                    Homestead node (Pi 5) ── wire ── ESP32 safety MCU
                                           ▲ LoRa (Meshtastic), off-grid
```

| Link | Carries | Bandwidth needed | Notes |
|---|---|---|---|
| PC ↔ model node | prompts and answers (text), occasionally images | tiny; latency matters more | wired 2.5 GbE; never through the internet |
| PC ↔ phone | sync, voice, questions to the PC's model | small | Tailscale when away |
| PC ↔ homestead node | snapshots and adjustments | tiny | LAN, or Tailscale |
| Node ↔ LoRa | short messages | very low | works with no internet |

**The PC stays the coordinator** (DEC-0190: one writer). A model node holds no records; it answers inference
requests from the PC's runtime and is listed in the capability registry like any device.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-021 | A model node shall be added by pairing (as a device is, REQ-DEV-002), hold none of his records, and serve inference only to paired devices over the LAN or Tailscale. | Should | R1 | All | New | T: an unpaired request refused | DEC-0202, → 12, 13 |
| REQ-HW-022 | Losing any node (model node, Pi, phone) shall leave the others working, with the work it did placed elsewhere or said to be waiting. | Must | MVP | All | Partial | T | DEC-0204, → 12 |
