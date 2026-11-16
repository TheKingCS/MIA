# MIA OS: build versus reuse (Prompt 05, deliverable 11)

*Claude (Fable), 2026-11-16. Planning only. For every system capability: use a Linux component as it is, configure
it, extend it, write an integration layer, or build something new. The bias is stated in the Master Directive and
kept here: build only where MIA adds something Linux doesn't have.*

## 1. The scale

1. **Use** an existing component directly.
2. **Configure** an existing component (files in the image).
3. **Extend** an existing component (a plug-in, a rule, a service menu).
4. **Integrate**: a MIA-specific layer that talks to an existing component.
5. **Build** a new component.

## 2. Capability by capability

| Capability | Level | Component | What MIA writes | Why not more, or less |
|---|---|---|---|---|
| Kernel, drivers, firmware | 1 Use | the distribution's kernel, linux-firmware, fwupd | nothing | REQ-ARC-001 |
| Boot, disk unlock | 2 Configure | the boot loader, dracut, systemd-cryptenroll | kernel arguments and the TPM enrolment step | |
| OS delivery, updates, rollback | 2 Configure | bootc; a `Containerfile` | the `Containerfile` and a build job | the alternative is a distribution of our own |
| Service supervision | 2 Configure | systemd | unit files, slices | a supervisor of our own would duplicate it |
| Login, sessions, lock | 2 Configure | Plasma Login Manager, logind, the compositor's locker | one session entry file and its start script | |
| Conventional desktop | 1 Use | KDE Plasma | nothing | it must stay a stock desktop |
| Compositor for MIA's session | 2 Configure (KWin) or 1 Use (cage) | pending PoC 3 | a session start script | a compositor of our own is level 5 for no requirement |
| MIA's shell | 5 Build (small), reusing what exists | the Qt web host, cut down; `web/` unchanged | the host, the recovery page, panel and notification surfaces | this is MIA's face: the one place level 5 is plainly justified |
| Notifications | 4 Integrate | the desktop notification interface | the adapter; in MIA's session, serving that interface from the shell | the gate (her pacing) is MIA's value; the transport is standard |
| Audio, camera | 4 Integrate | PipeWire | adapters' Linux halves | |
| Network, Bluetooth, power, devices | 4 Integrate | NetworkManager, BlueZ, UPower, logind, udev | adapters; udev rules for his boards (level 3) | |
| Files | 4 Integrate | the filesystem, UDisks2, the portals | the files adapter with grants; Landlock setup for workers | no storage service of our own |
| Conventional app install and launch | 4 Integrate | Flatpak, desktop entries | the applications adapter; plain-words permission display | DEC-0177: never MIA's registry |
| Capturing from other apps | 5 Build (small) | portals, AT-SPI, the clipboard protocol underneath | the capture agent; file-manager service menus (level 3); a browser extension | the Universal Action Layer's front door: MIA's own idea |
| His records, actions, grants, schedule, registry, gate | Existing MIA | the runtime | already built; a readiness and watchdog signal to add | this *is* MIA |
| System changes by MIA | 5 Build (small) | polkit, D-Bus, the services each operation calls | the helper and its polkit actions | "controlled AI-to-system operations" is the other place level 5 is justified; kept as small as possible |
| Logging, crash capture | 2 Configure | journald, systemd-coredump | log to standard output with fields | no log system of our own on Linux |
| Health and diagnostics | 4 Integrate | systemd, the kernel's pressure and hwmon files, the update mechanism's status | the system-state adapter; the diagnostic snapshot | no monitoring stack |
| Resource control | 2 Configure | cgroups through systemd, systemd-oomd | slice files; homeostasis reading pressure | homeostasis (her own pacing) exists and is MIA's value |
| Model serving | 1 Use | Ollama (ROCm or Vulkan) | nothing; `core/llm_manager.py` exists | |
| Sandboxing extensions | 3 Extend | bubblewrap, seccomp, systemd transient units | the sandbox profile and launcher (DEC-0176) | |
| Sandboxing conventional apps | 1 Use | Flatpak | nothing | |
| Disk encryption, sealing | 2 Configure and Existing MIA | LUKS2; `core/at_rest.py`, `core/key_unlock.py` | the enrolment step | |
| Firewall, remote reach | 2 Configure | firewalld, Tailscale | zone defaults; one helper operation | |
| Mandatory access control | 1 Use, later 3 Extend | SELinux as shipped | later, a policy module for the helper | |
| Search and indexing of his data | Existing MIA, extended | the stores; `core/meaning.py` | the index (prompt 23's review) | the desktop's indexer stays the desktop's |
| Image signing and verification | 2 Configure | the registry's signing (cosign) and bootc's verification | a key, a policy file | |

## 3. Where MIA-specific development earns its place

Counting level 4 and 5 rows, MIA writes: **adapters** (about ten small Linux halves of interfaces that already
exist for other hosts), **the shell's host** (cut down from existing code), **the capture agent**, **the system
helper**, **a session start script and unit files**, and **the image definition**. Nothing else. In the prompt's
terms: platform integration, session and system coordination, service interfaces, application discovery (the
registry, built), the capability registry (built), shell integration, and controlled AI-to-system operations.

## 4. What is deliberately not built

| Tempting | Why not |
|---|---|
| A MIA compositor or window manager | KWin or cage exists; no requirement needs ours |
| A MIA package manager or app store | DEC-0177; Flatpak and the image exist |
| A MIA init or supervisor | systemd |
| A MIA configuration daemon for the system | the image is the declaration; `/etc` stays Linux's |
| A MIA logging or metrics stack | the journal and the kernel's accounting |
| A MIA storage or database service | the filesystem and the stores |
| A message broker | one machine, one writer |
| A MIA network manager, firewall or VPN | NetworkManager, firewalld, Tailscale |
| A MIA kernel module or custom kernel | REQ-ARC-001 |
| A general "run this command as root" facility | it would undo the whole privilege design |
| Our own model server | Ollama and llama.cpp exist behind an interface already |

## 5. Size of the new work, roughly

So Zac can weigh it (estimates, to be replaced by Prompt 16's plan):

| Piece | New code | Risk |
|---|---|---|
| The image (`Containerfile`, units, slices, session entry, polkit actions, udev rules) | hundreds of lines of configuration | bootc's desktop path (PoC 2) |
| Adapters' Linux halves | small each; the interfaces exist | low |
| The shell's host | a cut-down of existing code plus the recovery page | the compositor choice (PoC 3) |
| The capture agent | small | portals' behaviour (PoC 3) |
| The system helper, read-only first | small, and must stay small | it is root: review and tests matter more than size |
| Runtime changes (readiness, watchdog, journal logging, socket, worker processes) | small to medium | low |
