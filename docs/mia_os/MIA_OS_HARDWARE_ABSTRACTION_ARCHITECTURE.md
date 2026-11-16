# MIA OS: hardware abstraction and connectivity (Prompt 05, deliverable 7, with §16 networking)

*Claude (Fable), 2026-11-16. Planning only. How hardware is discovered, who drives it, how MIA and her apps reach
it, how that reach is recorded and taken back, and the network foundation under MIA's devices. Target hardware and
device classes are Prompt 06's; the distributed design is Prompt 12's; the full permission model is Prompt 13's.*

## 1. The rule

**MIA never drives hardware. Linux does; MIA asks the service that owns it.** There are four steps between a device
and anything of MIA's, and MIA's code starts at the third:

```
hardware → kernel driver → the owning OS service → MIA's adapter → a capability (tiered, granted, recorded) → an app or tool
```

No MIA component opens a raw device node except the device framework's drivers for boards that have no OS service
(a serial microcontroller), and those open only devices udev has marked as his.

## 2. Who owns what

| Hardware | Discovery | Driver | Owning service | MIA's adapter and state today |
|---|---|---|---|---|
| Microphones, speakers, headsets | udev → PipeWire | ALSA in the kernel | PipeWire with WirePlumber (policy: which device, which volume) | audio adapter: `sounddevice` on PortAudio, which PipeWire serves. Exists; device choice by name is to add |
| Cameras, webcams | udev | V4L2, libcamera | PipeWire's camera nodes; the camera portal for sandboxed apps | camera adapter: one frame or clip per request for Sight. Linux half new |
| Displays | the kernel's mode setting | amdgpu | the compositor | none: the shell is a client |
| Keyboard, mouse, touch | udev, libinput | in the kernel | the compositor | none; a global hotkey through the compositor or the portal |
| GPU (graphics) | | amdgpu, Mesa | the compositor and applications | none |
| GPU (compute) | | amdgpu; ROCm or Vulkan in user space | **the model server** | `core/llm_manager.py` over HTTP. MIA never loads a model into the GPU herself |
| AI accelerator (the Pi's HAT) | udev | Raspberry Pi OS's driver | its inference runtime | a model backend, Prompt 07 |
| Bluetooth devices | BlueZ | in the kernel | BlueZ | adapter over D-Bus. New |
| USB storage | udev → UDisks2 | in the kernel | UDisks2, mounted by the desktop | files adapter, when he grants a folder on it |
| Serial and USB boards (microcontrollers, the greenhouse's) | udev | tty and hid drivers | **none: this is where MIA's own drivers live** | `core/device_framework.py`, `pyserial`. Exists; needs udev rules instead of group membership |
| Sensors (network ones) | they report in | | | `core/sensors.py`: each has a key and posts readings. Exists |
| Network adapters | udev | in the kernel | NetworkManager | network adapter: read state over D-Bus. Today `core/connectivity.py` probes; the D-Bus half is new |
| Battery, AC, lid | udev | ACPI | UPower, logind | power adapter: `core/power_manager.py` on psutil today; UPower signals to add |
| Temperatures, fans | | hwmon | the kernel's files; `power-profiles` for policy | system-state adapter: read. `core/system_health.py` exists |
| Firmware | | | fwupd | read; updates are system actions |
| The phone, the glasses, the Pi | pairing | | the runtime's own server and relay | exists (Prompt 12 owns the design) |

## 3. Permission, mediation, logging, revocation

Three layers, each doing a different job:

| Layer | What it controls | Mechanism |
|---|---|---|
| The OS | which *user* and which *sandboxed app* may touch a device at all | udev's seat access (the signed-in person, not a broad group), PipeWire's and the portals' per-app permissions for Flatpak apps, the firewall |
| MIA's capability | which *tool or app of MIA's* may use a device, and at what tier | the manifest's tier and device permission; `grants.require` for anything she starts herself; a camera or microphone is never left running (Sight looks once; voice listens only when addressed or while he holds the control) |
| The record | that it happened | the action history for anything that commands a device; a note per look for the camera (kind and time, never the picture); the gate's log for anything she then said |

**Examples the prompt asks for.** The greenhouse app reads sensor readings through the greenhouse link's capability
(`observe`) and adjusts a controller through a device-command capability that asks him unless he granted that kind
(REQ-FUN-103); the node keeps its own safety limits whatever MIA sends. The glasses' interface reaches the camera
and microphone through the phone's permissions and Meta's toolkit, then MIA's own capabilities; the PC's webcam is a
separate device with its own grant.

**Revocation** is at any layer: remove the grant in MIA (the list on the Apps page), revoke the app's portal
permission in the desktop's settings, or unplug it. A revoked device shows as "not allowed", never as "not found".

**Indicators belong to the OS.** While a camera or microphone is open, the compositor's or Plasma's own indicator
shows it; MIA's shell shows her listening state too, but the trustworthy indicator is the one MIA can't draw over.
In MIA's own session that indicator must come from the shell's host or the compositor, not from a web page (a
requirement on Prompt 10).

## 4. What needs building

| Piece | Kind | Why |
|---|---|---|
| The adapters' Linux halves (UPower, logind, NetworkManager, BlueZ, PipeWire device lists, notifications) | New MIA integration | the same interfaces Windows and Android already implement differently (DEC-0154) |
| udev rules for his boards | Configuration in the image | access for the person at the keyboard, by device identity, instead of adding him to `dialout` |
| A device permission in the manifest schema (`devices.use:<class>`) | Small extension | network and device permissions per app are the registry's remaining undeclared part (noted when M4 was built) |
| Nothing else | | every other row is an existing Linux service |

## 5. Networking and connectivity foundation (§16)

| Need | Choice | Notes |
|---|---|---|
| Network configuration, Wi-Fi, Ethernet, VPN | **NetworkManager** | Fedora's and KDE's default; D-Bus API; systemd-networkd suits servers and has no desktop integration |
| Name resolution | systemd-resolved | the distribution's default |
| Firewall | firewalld | default zone closed to inbound; MIA's API port is opened only on networks he marks as home, by a system action |
| MIA's server | loopback by default; the home network when phone access is on (verified: `core/phone_server.py`, `server.host`) | never a public interface (REQ-SEC-004) |
| Remote reach | **Tailscale, optional** (verified in use: MIA reads `tailscale status` and tells him the `tailscale serve` command; she doesn't run it) | forwards to loopback; no port opened to the internet. On MIA OS `tailscaled` is in the image, off until he signs in |
| Finding devices on the home network | pairing by code today; mDNS (Avahi or resolved) is Prompt 12's choice | |
| Bluetooth networking | not used | |
| Device to device | HTTPS to the runtime over the home network or the tailnet; the glasses through the sealed relay | Prompt 12 |

**Requirements on the foundation:**

- **Local operation:** everything on the machine works with no network at all; nothing waits for the network at
  boot (the runtime *wants* the network, never *requires* it).
- **Disconnection and restoration:** the network adapter tells the runtime as it happens (NetworkManager's
  signals, instead of today's probing); online jobs wait and say so once (REQ-REL-011); on return they run at their
  next turn, with no burst.
- **Metered connections:** NetworkManager knows; heavy downloads (models, the image) wait unless he says go.
- **Secure device communication:** pairing keys and TLS as today; identity and revocation are Prompt 12 and 13's
  (T-04).
- **Diagnostics:** "why can't the phone reach the PC?" is answered from facts: the server's state, the firewall
  zone, the tailnet's status, the last successful sync. `core/service_map.py` and `core/connectivity.py` already
  gather most of it.
