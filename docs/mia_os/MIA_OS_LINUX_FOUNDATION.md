# MIA OS: the Linux foundation (Prompt 05, deliverable 2)

*Claude (Fable), 2026-11-16. Planning only. The distribution, the kernel, the boot foundation, hardware
compatibility and what it costs to keep. Evidence and the full comparison are in
[MIA_OS_CORE_TECHNOLOGY_EVALUATION.md](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md) (sources [S1]…). Decision: DEC-0189
(proposed), which keeps the base DEC-0157 proposed and Zac named ("Fedora for the PC", DEC-0168).*

## 1. The recommendation

1. **Foundation, the PC:** Fedora's Atomic desktop with KDE (the Kinoite lineage), consumed as a **bootc image built
   from a `Containerfile` in this repository**. MIA OS is *a customised image of a distribution*, never a
   distribution of its own: Fedora supplies the kernel, drivers, security updates and every package; the repository
   adds MIA, her session and her configuration on top.
2. **Foundation, the Pi:** Raspberry Pi OS (Debian 13), as decided (DEC-0168): the AI HAT's drivers are official only
   there. It is an ordinary mutable install with the runtime as a user service. The MIA platform is identical on both
   (DEC-0154); only the layer under it differs.
3. **Alternatives kept open:**
   - **Ubuntu 26.04 LTS** on the PC, if GPU compute can't be made to work well on Fedora (proof of concept 1). It
     gives up image-based updates and rollback, so REQ-ARC-011, REQ-OPS-001 and REQ-REL-009 would need another answer
     (Btrfs snapshots before each update).
   - **Universal Blue's Aurora** as the base image, if deriving directly from Fedora's own KDE image proves rough
     before Fedora finishes bootc desktops. Same packages, one more project in the chain.
4. **Why Fedora:** it is the only candidate that has both things the PC needs most at once: image-based updates with
   rollback, and the GPU compute stack for this card in its own repositories, including the model runner MIA already
   uses ([S4], [S6]). Zac also chose it.
5. **Major limitations:**
   - bootc desktops are arriving in Fedora, not finished ([S2], [S3]): the build path is proven by others, not yet
     Fedora's own product. Proof of concept 2 tests it before anything depends on it.
   - A Fedora release is supported about 13 months: the image moves to a new Fedora roughly twice a year. On an
     image-based system that is a changed line in the `Containerfile`, a rebuild and a test, with the old deployment
     kept; it is still work that never ends.
   - AMD's own support matrix names Ubuntu and enterprise distributions, not Fedora ([S5]): on Fedora the ROCm
     packages are Fedora's, built from AMD's sources. If AMD's and Fedora's builds differ, Fedora's maintainers are
     who we depend on.
6. **Long-term distribution strategy:** none. MIA is for Zac alone (DEC-0119). The image is published nowhere but
   his own registry or drive; nothing in the design depends on other people installing it. If that ever changes it
   is a new decision, and the same `Containerfile` approach is how others would get it.

## 2. Kernel and hardware abstraction strategy

- **The distribution's kernel, unmodified.** No MIA kernel configuration, no MIA kernel code, no out-of-tree modules
  on the PC (REQ-ARC-001). Every driver the reference PC needs is in the mainline kernel.
- **Firmware** comes from the distribution's `linux-firmware` and from `fwupd` (device firmware through the vendor
  service, each update shown and approved like any system change).
- **Kernel security updates** arrive with the image: a new image is built when Fedora publishes, tested, then
  offered (REQ-OPS-001). A bad kernel is undone by booting the previous deployment.
- **What stays in user space, always:** everything of MIA's. Model inference, audio processing, the camera
  pipeline, device protocols (serial boards, the greenhouse link, the glasses' relay), sensors' interpretation.
- **How hardware reaches MIA:** never as device files handed to "MIA", always as a service's API reached by a
  platform adapter behind a capability ([MIA_OS_HARDWARE_ABSTRACTION_ARCHITECTURE.md](MIA_OS_HARDWARE_ABSTRACTION_ARCHITECTURE.md)):

| Hardware | The OS piece that owns it | MIA's way in |
|---|---|---|
| Microphone, speakers | PipeWire and WirePlumber | the audio adapter (today `sounddevice` on PortAudio, which PipeWire serves) |
| Cameras, webcam | the kernel's V4L2, PipeWire's camera node | the camera adapter, one frame or one clip per request (Sight never leaves a camera running) |
| GPU | amdgpu, Mesa, ROCm | only through the model server; MIA itself never opens the GPU |
| AI accelerator (the Pi's HAT) | Raspberry Pi OS's driver | through its inference service, as a model backend |
| Sensors, serial and USB boards | udev, the tty and hid drivers | `core/device_framework.py` drivers, with udev rules that give the signed-in person access to known boards |
| Bluetooth | BlueZ | BlueZ's D-Bus API, through an adapter |
| Network adapters | NetworkManager | read-only state through its D-Bus API; changes are system actions |
| Displays, input | the compositor | never directly: MIA's shell is a client like any other |
| Battery, power, thermal | UPower, logind, hwmon | the power adapter (today `core/power_manager.py` on psutil) |

## 3. Boot and initialisation

Order, and what each stage depends on. The detail of the boot experience, recovery and updates is Prompt 14's; this
fixes the structure.

| # | Stage | Provided by | Fails → |
|---|---|---|---|
| 1 | Firmware, Secure Boot | the PC | firmware's own recovery |
| 2 | Boot loader, with the current and previous deployments listed | Fedora (bootc's default) | pick the previous deployment |
| 3 | Kernel and initramfs | Fedora, in the image | previous deployment |
| 4 | Unlock the disk (TPM2 and a PIN) | systemd-cryptsetup | the recovery key |
| 5 | Root mounted read-only from the image; `/etc` and `/var` writable | bootc, composefs **(to verify)** | previous deployment |
| 6 | System services (`multi-user.target`): logind, NetworkManager, the model server, the firewall | systemd | each restarts alone; none waits for MIA |
| 7 | Login screen (`graphical.target`): MIA's session selected, Plasma beside it | Plasma Login Manager | a text console is still there |
| 8 | The person's services (`user@.service`): PipeWire, portals, **the MIA Runtime** | systemd's user manager | the session still starts; the shell shows the recovery page (REQ-UX-022) |
| 9 | The session: the compositor, then MIA's shell (or Plasma) | the session's own target | fall back to Plasma; see the session document §6 |
| 10 | The model loaded | the model server, on first use or kept warm (Prompt 07) | Home works from records with no model (REQ-UX-021) |

**The rule that makes a broken MIA harmless:** nothing in stages 1 to 7 has a dependency on anything of MIA's. The
runtime is `WantedBy=default.target` of the *user* manager, the model server is an ordinary system service that
nothing else requires, and the login screen offers Plasma whether MIA's packages work or not (REQ-ARC-002,
REQ-PER-002). A test for it: mask the runtime's unit, reboot, and the machine reaches a working Plasma.

## 4. Hardware compatibility

| Part | Expectation on Fedora 45 | Proven by |
|---|---|---|
| Ryzen 7 9800X3D | supported by current kernels **(to verify)** | PoC 1 (a live session) |
| Radeon RX 7900 XTX: display | in-tree amdgpu and Mesa; the best-supported class of GPU on Linux | PoC 1 |
| Radeon RX 7900 XTX: compute | ROCm from Fedora's repositories; Vulkan as the fallback ([S4], [S6]) | **PoC 1, the deciding test** (HW-002, T-10, T-11) |
| NVMe, USB, Ethernet, audio | in-tree | PoC 1 |
| Wi-Fi and Bluetooth (the motherboard's) | unknown until read from the machine | PoC 1 (P-03 extended) |
| TPM2 | must be enabled in firmware (P-03) | PoC 1 |
| The Pi 5, AI HAT+ | Raspberry Pi OS, official drivers | the Pi session (DEC-0168) |

The fuller hardware evaluation, device classes and the minimum profile are Prompt 06's.

## 5. Maintenance implications (what keeping this costs)

| Recurring work | How often | Who or what does it |
|---|---|---|
| Rebuild the image on Fedora's updates | weekly, or on a security notice | a build job (Prompt 15); offered to Zac, never forced |
| Move to the next Fedora | twice a year | change the base tag, rebuild, run the acceptance list in a VM, then offer |
| Keep MIA's Python environment locked | with each dependency change | the lockfile (risk R-08 from Prompt 01 is closed by this) |
| Watch bootc's desktop support settle | until Fedora ships it | drop workarounds as they stop being needed |
| The Pi: `apt` upgrades | as Raspberry Pi OS publishes | proposed system actions through the helper |

## 6. Migration implications for what exists

- **MIA's code changes very little.** The runtime, its unit, the key store for Linux (`core/key_unlock.py`), `MIA_HOME`
  and the installer exist (DEC-0155, DEC-0169). What is new is the image around them and the adapters named in the
  architecture.
- **The data moves by copy**, re-sealed under the Linux key from the recovery key (REQ-CMP-002; `tools/move_home.py`
  already copies and verifies).
- **Windows keeps working** until Zac retires it (REQ-CMP-001): dual boot on a separate drive, the same data copied,
  never two MIAs writing the same folder (`core/instance_lock.py`).
- **The Qt desktop app** isn't part of MIA OS as it stands: its web mode becomes the shell's host; its classic
  screens stay a Windows concern (DEC-0168: fixes only).
- **Edge is her browser on Windows** (Playwright). On Linux the same code drives Chromium: an adapter choice, tested
  in PoC 4.
