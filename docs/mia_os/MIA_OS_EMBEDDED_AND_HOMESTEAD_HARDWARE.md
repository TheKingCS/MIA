# MIA OS: embedded and homestead hardware (Prompt 06 §9)

*Claude (Opus), 2026-11-17. Planning only. Built on `homestead/` (DEC-0145, DEC-0150, DEC-0185) and
`docs/HARDWARE.md`.*

## 1. The layers (verified in the repository; the node is built and simulated, not yet installed)

```
MIA (PC or Pi)  ──snapshots, adjustments──▶  Homestead node (Raspberry Pi 5)  ──wire protocol──▶  ESP32 safety MCU
   asks, proposes,                              its own control loop, its own          enforces hard limits:
   explains                                     database and scenarios                 heater, pumps, vents
```

| Layer | Hardware | Owns | Never |
|---|---|---|---|
| MIA | the PC (or a Pi running MIA Core) | understanding, plans, adjustments within limits | drives a relay, a pump or a heater directly |
| Homestead node | Raspberry Pi 5 | the control loop, schedules, sensors, its own records | depends on MIA to keep the greenhouse safe |
| Safety MCU | ESP32 (firmware in `homestead/firmware/`, PlatformIO) | the hard limits; fails safe | trusts anything above it past its limits |
| Sensors and actuators | temperature, humidity, water, light; relays, pumps, fans | — | — |

A stop of MIA never touches the greenhouse (DEC-0185); the node keeps running when MIA is off or the PC is down.

## 2. Hardware by role

| Role | Recommended | Why |
|---|---|---|
| Node computer | Raspberry Pi 5 (8 GB) with active cooling and an NVMe or high-endurance storage | the homestead code targets it; mainline Linux |
| Safety controller | ESP32 (as in the firmware) | Wi-Fi/BLE, cheap, its own watchdog |
| Sensors | I2C and 1-Wire sensors (temperature, humidity), analog through an ADC, water level by float or ultrasonic | open buses, no vendor cloud |
| Long-range links | Meshtastic LoRa radios (US 915 MHz) | works without internet; already in MIA's plans |
| Local AI on the node | AI HAT+ 2 (Hailo-10H) only for MIA Core's small model | the node's control never depends on it |
| Power | a UPS HAT or a small UPS for the node; the MCU on its own supply | the greenhouse outlives a blip |

**Protocols:** the node's own wire protocol to the MCU (`MCU_PROTOCOL.md`), MQTT or HTTP to MIA, Modbus RTU over
RS-485 where an industrial controller is used. No device that only works through a vendor's cloud.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-017 | Physical hard limits (temperatures, run times, levels) shall live in the controller nearest the hardware; MIA's adjustments are checked there and refused past them. | Must | MVP | Pi | Exists (the safety MCU, simulated) | T: homestead's scenarios | DEC-0185 → 06 |
| REQ-HW-018 | The homestead shall keep running its last good settings with MIA, the PC or the network gone. | Must | MVP | Pi | Exists (simulated) | T: scenarios | DEC-0150 → 06 |
