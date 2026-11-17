# MIA OS: hardware discovery and the capability registry (Prompt 06 §14; DEC-0203)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. The rule

**Discovery reads Linux; MIA reads the records.** Nothing in MIA probes hardware directly. A small reader in the
runtime turns what Linux already knows into one capability record per device, and everything else in MIA (model
placement, the parity of features per device, advice about hardware) reads those records.

## 2. Sources, per kind

| Kind | Linux source |
|---|---|
| Processor, memory | /proc/cpuinfo, /proc/meminfo, `lscpu` |
| PCI devices, slots | `lspci`, /sys/bus/pci; dmidecode for slot counts (root, through the helper) |
| GPU and its compute paths | amdgpu sysfs (VRAM total and used), `rocminfo` (ROCm), `vulkaninfo` (Vulkan) |
| Storage | `lsblk`, udisks2, SMART |
| USB, serial | udev |
| Network | NetworkManager over D-Bus; Tailscale's local API |
| Bluetooth | BlueZ over D-Bus |
| Power | UPower over D-Bus; NUT |
| Displays | KWin's output list |
| Other devices (phone, Pi, model node) | their own record, sent when paired (REQ-HW-015, 021) |

Root-only facts (slot counts, SMART) come through Prompt 05's fixed-operation helper, read-only operations only.

## 3. The record

```json
{"device": "pc", "kind": "workstation", "read": "2026-11-17T04:10:00",
 "cpu": {"model": "AMD Ryzen 7 9800X3D", "cores": 8, "threads": 8},
 "memory": {"total_gb": 32, "slots": 2, "slots_free": 0},
 "gpus": [{"model": "Radeon RX 7900 XTX", "vram_gb": 24, "paths": ["rocm", "vulkan"]},
          {"model": "Radeon (integrated)", "vram_gb": 0, "paths": ["vulkan"]}],
 "pcie_x16_slots_free": 0,
 "storage": [{"model": "Crucial P3 1TB", "free_gb": 524, "health": "ok"}],
 "network": {"ethernet_gbps": 2.5, "wifi": "6E", "tailscale": true},
 "power": {"ups": false, "on_battery": false},
 "sources": {"memory.slots": "dmidecode", "gpus": "amdgpu sysfs, rocminfo"}}
```

Every field says where it came from; a field that couldn't be read is absent, never guessed (the Living System's
epistemic rule, DEC-0173). The record is re-read at boot, on a udev or D-Bus change, and daily.

## 4. Who reads it

| Reader | Uses |
|---|---|
| Model placement (Prompt 07) | which models fit where (REQ-HW-011) |
| Parity and features | what this device can offer now (REQ-DEV-005) |
| Hardware advice | never recommends what can't be fitted (REQ-HW-009) |
| Health | thresholds and warnings (REQ-HW-024 to 026) |
| "What's in my computer?" | answered from the record, sources named |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-HW-027 | Every device shall have a capability record built only from its OS's own sources, each field with its source and time, and no field guessed. | Must | R1 | All | New | T: a record from fixture outputs; a missing source leaves the field absent | DEC-0203, DEC-0173 → 06 |
| REQ-HW-028 | Asked about its hardware, MIA shall answer from the record and name the source. | Should | R1 | All | Partial (`core/model_registry.py` does this for models) | T | DEC-0203 → 06 |
