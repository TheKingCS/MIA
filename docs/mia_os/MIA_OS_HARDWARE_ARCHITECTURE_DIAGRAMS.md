# MIA OS: hardware architecture diagrams (Prompt 06 §20)

*Claude (Opus), 2026-11-17. The ten diagrams the prompt asks for, in Mermaid (renders on GitHub).*

## 1. Primary workstation

```mermaid
flowchart LR
  CPU["Ryzen 7 9800X3D<br/>8 cores, iGPU"] --- RAM["32 GB DDR5<br/>2 of 2 slots"]
  CPU --- GPU["RX 7900 XTX 24 GB<br/>the only x16 slot"]
  CPU --- NVME["1 TB NVMe"]
  CPU --- NET["2.5 GbE, Wi-Fi 6E, BT"]
  GPU --- MON1["4K 240 Hz"]
  CPU --- MON2["1080p on the iGPU"]
```

## 2. CPU, GPU and AI acceleration

```mermaid
flowchart TB
  RT["MIA runtime"] --> Q["model queue (DEC-0204)"]
  Q --> OL["Ollama"]
  OL -->|ROCm| GPU["RX 7900 XTX"]
  OL -->|Vulkan fallback| GPU
  OL -->|CPU fallback| CPU["9800X3D"]
  Q -->|over the LAN| NODE["model node (proposed)"]
```

## 3. Discovery and the capability registry

```mermaid
flowchart LR
  SYS["sysfs, udev"] --> R["capability reader"]
  DBUS["UPower, NetworkManager, BlueZ"] --> R
  HELP["helper: read-only ops<br/>(dmidecode, SMART)"] --> R
  PEERS["paired devices' own records"] --> R
  R --> REC[("capability records")]
  REC --> PLACE["model placement"]
  REC --> PAR["features per device"]
  REC --> ADV["hardware advice"]
  REC --> HEALTH["health"]
```

## 4. Resource coordination

```mermaid
flowchart TB
  subgraph Linux
    CG["cgroups per service"] --- OOM["systemd-oomd"] --- PST["power states"]
  end
  subgraph MIA
    PRI["priority: conversation > specialist > Workroom > background"] --> Q["one job per GPU"]
  end
  Q --> CG
```

## 5. Android and the workstation

```mermaid
flowchart LR
  PH["Galaxy A54<br/>MIA app, small model"] <-->|Tailscale| PC["PC runtime"]
  PH --- GL["glasses (BLE)"]
  PH -->|asks the bigger model| PC
```

## 6. Glasses and spatial endpoints

```mermaid
flowchart LR
  GL["Ray-Ban Display<br/>display, camera, mics"] --- NB["Neural Band (EMG)"]
  GL <-->|Wearables toolkit| APP["phone app"] <-->|cards, voice| PC["PC runtime"]
```

## 7. Embedded and homestead

```mermaid
flowchart LR
  MIA["MIA"] -->|adjust within limits| NODE["Pi 5 node<br/>control loop"]
  NODE -->|wire protocol| MCU["ESP32 safety MCU<br/>hard limits"]
  MCU --> ACT["relays, pumps, fans, heater"]
  SEN["sensors"] --> NODE
  NODE -.->|LoRa| RADIO["Meshtastic"]
```

## 8. Distributed device network

```mermaid
flowchart TB
  PC["PC: coordinator, records"] --- NODE["model node"]
  PC --- PI["homestead node"]
  PC --- PH["phone"]
  PC --- PIC["Pi: MIA Core (later)"]
  PH --- GL["glasses"]
```

## 9. Hardware abstraction layers

```mermaid
flowchart TB
  APPS["MIA apps"] --> CAP["capabilities and grants"]
  CAP --> RT["runtime services"]
  RT --> OSS["OS services: PipeWire, BlueZ, NetworkManager, UPower, portals"]
  OSS --> K["Linux kernel and drivers"]
  K --> HW["hardware"]
```

## 10. Failure and degraded operation

```mermaid
flowchart LR
  GPU{"GPU ok?"} -->|no| VK{"Vulkan ok?"}
  GPU -->|yes| FAST["full speed"]
  VK -->|yes| VKP["Vulkan path"]
  VK -->|no| NODE{"model node?"}
  NODE -->|yes| REMOTE["remote model"]
  NODE -->|no| CPUP["CPU, smaller model, said so"]
```
