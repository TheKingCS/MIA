# MIA OS: core technology evaluation (Prompt 05, deliverable 12)

*Claude (Fable), 2026-11-16. Planning only: nothing was installed, built or changed to write this. Technologies
compared for each layer, with evidence, alternatives and what was rejected. Sources checked on 2026-11-16 are listed
in section 9 and cited as [S1]…; a claim marked **(to verify)** rests on standing knowledge of the technology, not on
a source read today, and is checked in the proof of concept named beside it. The recommendations are collected in
[MIA_OS_CORE_ARCHITECTURE.md](MIA_OS_CORE_ARCHITECTURE.md); the decisions are DEC-0189 to DEC-0195 (proposed).*

## 1. Distribution foundation

Judged for one machine first (Zac's PC: Ryzen 7 9800X3D, Radeon RX 7900 XTX 24 GB, 32 GB, 1 TB NVMe), kept for
years by one person with MIA's help, rebuilt from the repository (REQ-ARC-011).

| Candidate | Updates and rollback | GPU compute for the RX 7900 XTX | KDE Plasma | Rebuild from files | Maintenance for one person | Verdict |
|---|---|---|---|---|---|---|
| **Fedora Atomic (Kinoite lineage), as a bootc image** | image-based, atomic, previous deployment kept at boot | ROCm and Ollama's ROCm backend are **in Fedora's own repositories** for Fedora 45 (`ollama-rocm` 0.24.0, ROCm 7.1 in F44) [S4]; Ollama's AMD path on Linux is ROCm 7 [S6]; the card (gfx1100) is on AMD's supported list [S5] | first-class (Kinoite); Plasma 6.7 or 6.8 [S1][S2] | a `Containerfile` deriving from the Fedora image | a new Fedora every 6 months, each supported about 13 months: the image is rebased twice a year | **Recommended** |
| Universal Blue (Aurora) as the base | same mechanism (it is Fedora Atomic plus a build pipeline) | same packages | Aurora is the KDE image | its `image-template` is a ready pipeline with mandatory signing [S8] | adds a volunteer project between Fedora and MIA; its opinions change under us | **Use its template as the pattern, not its image as the base** |
| Ubuntu 26.04 LTS | mutable (apt); snapshots only with extra setup | ROCm is **in the Ubuntu archive** from 26.04 (7.1, moving to 7.2) [S7]; AMD's own support matrix has always listed Ubuntu [S5] | Kubuntu, a community flavour | not image-based: reproducing it means scripts or autoinstall, and drift is possible | five years of updates, no rebase | **Fallback** if GPU compute fails on Fedora |
| Debian 13 | mutable | ROCm 7.11 preview lists Debian 13 [S5] | yes | as Ubuntu | long, slow | The **Pi's** base already (Raspberry Pi OS is Debian 13, DEC-0168); not the PC's: older Mesa and kernel for a 2022 GPU matter less each year, but nothing gained over Ubuntu |
| openSUSE (Kalpa / Aeon) | transactional, Btrfs snapshots | no ROCm in the main repositories **(to verify)** | Kalpa (KDE) is the less finished of the two | partly | small team | Rejected: GPU compute is the deciding factor and it's weakest here |
| NixOS | declarative, atomic, rollbacks | ROCm packaged by the community | yes | best of all | its own language and model; MIA's helpers, Flatpak habits and every guide assume FHS | Rejected for now: the cost falls on every later prompt |
| Arch | rolling, mutable | current packages | yes | no | breaks need hands | Rejected: not reproducible, no rollback |
| Own distribution, Yocto, a custom kernel | | | | | years | Rejected by REQ-ARC-001 and the Master Directive |

**Mutable or image-based.** A mutable system is easier on day one and harder every day after: what's installed
drifts from what's written down, and an update that breaks leaves a half-updated machine. An image-based system is
built from files, swapped whole and rolled back whole, which is REQ-ARC-011, REQ-OPS-001 and REQ-REL-009 almost for
free. Its cost: software that expects to write into `/usr` must go into the image, a container or a Flatpak, and
kernel modules from outside the kernel are awkward. MIA needs none (section 2).

**How finished is bootc for desktops?** Fedora's image-mode initiative targets production readiness with Fedora 45,
around December 2026 [S3]. In Fedora 45 the Atomic Desktops are still composed from ostree, with bootc-native
desktops planned "right after" [S2][S3]; generic `fedora-bootc` base images for 45 exist [S3]. Deriving a custom
image from the Kinoite container and switching a machine to it with `bootc switch` is the path Universal Blue has
shipped for years [S8]. So the mechanism is proven in practice and not yet Fedora's finished product. **This is
proof of concept 2**, and the reason the recommendation names a fallback.

**The sources disagree** on Plasma's version in Fedora 45 (6.8 in the release coverage [S1], 6.7 for Kinoite in the
Atomic Desktops post [S2]). It doesn't change a choice here; the image build will show which.

**A constraint found on the way:** Fedora 45's system Python is 3.15 [S15]; MIA supports 3.10 to 3.14
(`MIA_OS_TECHNOLOGY_STACK.md`). The image must carry MIA's own interpreter and packages (a pinned Python and a
locked virtual environment built into the image), never the system's. That is right anyway: the OS can then update
its Python without touching MIA (REQ-ARC-002).

## 2. Kernel

| Option | Verdict |
|---|---|
| **The distribution's kernel, unmodified** (Fedora 45: Linux 7.2, 7.3 following [S1]) | **Recommended.** amdgpu, the NVMe, network, audio and USB drivers are all in-tree; ROCm since version 6 uses the in-tree amdgpu driver, no out-of-tree module **(to verify, PoC 1)** |
| A long-term-support kernel | Not needed on the PC: Fedora's kernel is tested with its Mesa and firmware. It is what the Pi runs (Raspberry Pi's own kernel line) |
| A custom configuration or MIA kernel code | Rejected. Nothing MIA does needs the kernel; a custom kernel also breaks Secure Boot's stock chain |
| Out-of-tree modules (ZFS, NVIDIA-style drivers, v4l2loopback) | Avoid on the PC: each breaks on kernel updates and complicates the image. None is needed today. The Pi's AI HAT driver is Raspberry Pi OS's own package |

Rollback of a bad kernel is the previous deployment at the boot menu (the kernel is part of the image).

## 3. Boot chain

| Piece | Choice | Why |
|---|---|---|
| Firmware | UEFI, Secure Boot **on** | stock signed shim and kernel work because nothing is custom |
| Boot loader | what bootc installs on Fedora (GRUB 2 managed by bootupd) **(to verify, PoC 2)** | systemd-boot is cleaner but isn't bootc's default on Fedora yet; follow the default |
| Initramfs | dracut, built into the image | unlocks LUKS2 by TPM2 with a PIN (`systemd-cryptenroll`), REQ-SEC-001 |
| Init | systemd (260 or later in Fedora 45 [S14]) | |
| Dual boot | MIA OS on its own drive; chosen from the firmware's boot menu | the Windows drive is never written to; no chain-loading between loaders |

## 4. Graphical stack

| Question | Options | Verdict |
|---|---|---|
| Display protocol | Wayland; X11 | **Wayland.** X11 only through XWayland for old applications. Fedora's KDE has had no X11 session since Fedora 40 **(to verify)** |
| Conventional desktop | KDE Plasma; GNOME; COSMIC | **KDE Plasma** (REQ-FUN-001). Its portal backend advertises global shortcuts [S10], it has service menus, KWin scripting and layer-shell, and Zac's approved requirements name it. GNOME extends less. COSMIC reached stable in 2026 and is still completing accessibility [S13]: too young to build on |
| Compositor for MIA's session | cage; KWin run on its own; a wlroots compositor of ours | **Open, with a provisional recommendation of KWin on the PC** and cage on the Pi: see [MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md](MIA_OS_GRAPHICAL_AND_SESSION_ARCHITECTURE.md) §3. cage is maintained (0.3.1, July 2026, on wlroots 0.20 [S9]) but shows one application at a time, by design. KWin started with a single client is possible and not an officially supported login path [S11]. PoC 3 decides |
| Login screen | Plasma Login Manager (Fedora KDE's default since Fedora 44 [S12]); SDDM; greetd | **The distribution's default** (Plasma Login Manager). It lists sessions from `wayland-sessions/*.desktop`, which is all MIA needs |
| MIA's shell | Chromium in kiosk mode; a small Qt WebEngine host; Firefox kiosk | **Provisional: the Qt WebEngine host.** MIA already has one (`gui/main_window.py` in web mode, DEC-0124); Qt is native to KWin, can be a layer-shell surface and a tray item. Final in Prompt 10 (T-14) |

A known weakness in the chosen stack: KDE's global-shortcuts portal regressed in Plasma 6.7.4 and 6.7.5 [S10].
MIA's capture hotkey must not depend on it alone (in MIA's own session the shell owns the key).

## 5. Services, IPC and privilege

| Need | Options | Verdict |
|---|---|---|
| Service supervision | systemd system and user units; our own supervisor | **systemd.** The runtime's unit exists (`deploy/mia-runtime.service`) |
| Talking to OS services | D-Bus; Varlink; shelling out | **D-Bus**, because logind, NetworkManager, UPower, UDisks2, fwupd, polkit and the portals speak it. Never a shell |
| Surfaces to the runtime | HTTP with server-sent events; gRPC; D-Bus | **HTTP and SSE**, kept: 265 routes exist, every surface on every device uses them, and a browser engine speaks nothing else |
| A privileged helper's API | D-Bus with polkit; Varlink; setuid tool; sudo rules | **D-Bus with polkit**: polkit authorises D-Bus callers natively and KDE supplies the authentication dialog. systemd itself is moving its own interfaces to Varlink [S14]; revisit if polkit gains equal footing there |
| A message broker (MQTT, NATS, Redis) | | **Rejected** for the core: one machine, one writer. The greenhouse's own telemetry channel is Prompt 12's |
| Application sandbox | Flatpak for conventional apps; bubblewrap for MIA extensions; containers (podman) for agents' build work | as decided (DEC-0176, DEC-0177) |
| Mandatory access control | SELinux (Fedora, enforcing); AppArmor (Ubuntu) | **Whatever the base enforces, left on.** A custom policy for the helper is Prompt 13's |
| Restricting MIA's own file reach | Landlock (unprivileged, in the kernel); systemd unit sandboxing; nothing | **Landlock for worker processes, to prove** (PoC 6): it lets a process give up access to everything but the folders he granted, with no root |

## 6. Storage

| Filesystem | Snapshots | Integrity | In the kernel | Verdict |
|---|---|---|---|---|
| **Btrfs** | yes | checksums | yes | **Recommended on the PC**: Fedora's desktop default **(to verify)**, subvolumes for home and the model store, compression |
| ext4 | no | journal only | yes | The Pi (Raspberry Pi OS's default). Fine, simple |
| XFS | no | metadata checksums | yes | No gain here |
| ZFS | yes | best | **no** (out of tree) | Rejected: an out-of-tree module on an image-based system |

Encryption is LUKS2 under the filesystem (REQ-SEC-001), with MIA's own sealing of personal stores on top
(REQ-SEC-002, `core/at_rest.py`): a copied drive and a copied file are both useless.

## 7. Model serving

| Option | Verdict |
|---|---|
| **Ollama with the ROCm backend**, from Fedora's packages | **Recommended**: the runner MIA already uses, now packaged by the distribution [S4] |
| Ollama's Vulkan backend (Mesa RADV) | **Fallback**, same runner, no ROCm needed [S6]. Measured against ROCm in PoC 1 |
| llama.cpp's `llama-server` (Vulkan) | Second fallback; MIA's `OpenAIBackend` already speaks to it |
| vLLM | Not now: built for many parallel users |

Which models and how they're routed is Prompt 07's. Prompt 05 only requires that a model server is a separate
service MIA reaches over loopback HTTP and can live without (REQ-REL-001).

## 8. Experimental, deprecated or unsuitable (named so they aren't picked up later)

- **bootc-native Fedora desktops**: arriving, not finished [S2][S3]. Used through the proven derive-and-switch path.
- **KWin as a single-client compositor**: works by report, unsupported as a login path [S11]. A proof of concept, not a given.
- **KDE's global-shortcuts portal**: present, recently regressed [S10].
- **COSMIC**: stable in name, still filling in accessibility [S13].
- **X11 sessions**: being removed from the desktops MIA would use.
- **System V init scripts**: removed in systemd 260 [S14]; nothing of MIA's uses them.
- **Ollama on ROCm for the newest APUs** (gfx1150) is not yet stable [S6]: irrelevant to this PC, relevant if a laptop is ever a target.
- **`sudo` rules, setuid helpers, a root-running MIA**: rejected outright (DEC-0158).

## 9. Sources (read 2026-11-16)

- [S1] Fedora Linux 45 released 3 November 2026 (kernel 7.2, Plasma 6.8, GNOME 51): <https://fedoramagazine.org/announcing-fedora-linux-45/>, <https://phoronix.com/news/Fedora-45-Released>
- [S2] Atomic Desktops in Fedora 45 (Kinoite, Plasma 6.7; image-builder; bootc "right after"): <https://fedoramagazine.org/whats-new-for-fedora-atomic-desktops-in-fedora-linux-45/>, <https://fedoraproject.org/wiki/Changes/BuildAtomicDesktopsWithImageBuilder>
- [S3] Fedora image mode initiative (production readiness targeted for Fedora 45): <https://pagure.io/Fedora-Council/tickets/issue/549>
- [S4] Fedora packages: `ollama-rocm` for Fedora 45, ROCm 7.1 for Fedora 44: <https://packages.fedoraproject.org/pkgs/ollama/ollama-rocm>, <https://packages.fedoraproject.org/pkgs/rocclr/rocm-hip/fedora-44.html>
- [S5] AMD ROCm system requirements (RX 7900 XTX, gfx1100, supported) and the 7.11 preview's distributions: <https://rocm.docs.amd.com/projects/install-on-linux/en/docs-7.2.4/reference/system-requirements.html>, <https://rocm.docs.amd.com/en/7.11.0-preview/about/release-notes.html>
- [S6] Ollama GPU documentation (AMD on Linux through ROCm 7; Vulkan as the other path): <https://docs.ollama.com/gpu>
- [S7] Canonical: ROCm in the Ubuntu archive from 26.04 LTS: <https://canonical.com/blog/canonical-amd-rocm-ai-ml-hpc-libraries>, <https://ubuntu.com/blog/amd-rocm-on-ubuntu>
- [S8] Universal Blue's image template (custom bootc images, signing required): <https://github.com/ublue-os/image-template>
- [S9] cage 0.3 (April 2026, wlroots 0.20): <https://phoronix.com/news/cage-0.3-released>
- [S10] KDE's global-shortcuts portal: <https://bugs.kde.org/show_bug.cgi?id=523063>, <https://bugs.kde.org/show_bug.cgi?id=498575>
- [S11] KWin with a single client: <https://discuss.kde.org/t/kwin-equivalent-to-gnome-kiosk/17820>, <https://bugs.kde.org/show_bug.cgi?id=440397>
- [S12] Plasma Login Manager as Fedora KDE's default: <https://fedoraproject.org/wiki/Changes/PlasmaLoginManager>
- [S13] COSMIC in 2026: <https://alternativeto.net/news/2026/9/cosmic-epoch-1-9-brings-new-image-viewer-redesigned-app-store-and-on-screen-keyboard/>
- [S14] systemd 260 (March 2026): <https://phoronix.com/news/systemd-260-released>
- [S15] Fedora 45 beta (Python 3.15): <https://linuxjournal.com/content/fedora-linux-45-beta-released-python-315-gcc-162-and-major-security-changes>

Verified in the repository, not on the web: the server listens on `127.0.0.1` by default and reaches the phone
through `tailscale serve` (`core/phone_server.py`); the runtime's systemd user unit and installer exist and have not
yet run on a machine (`deploy/mia-runtime.service`, DEC-0155).
