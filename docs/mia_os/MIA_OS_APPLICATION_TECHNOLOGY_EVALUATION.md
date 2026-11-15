# MIA OS: application technologies evaluated (Prompt 03 §18)

*Claude (Opus), 2026-11-15. Research from current documentation (sources at the end), checked against MIA's code.
Planning; nothing built or installed.*

| Technology | What it does | Why relevant | Strengths | Limits | Security | Ops cost | Resources | Fits MIA? | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| **Flatpak** | sandboxed desktop apps with shared runtimes | the GUI-app channel on Fedora Atomic | Fedora Atomic's primary way to install GUI apps; per-app sandbox; updates and rollback; Flathub | GUI-oriented; runtimes are large; permissions can be over-broad if an app asks | default sandbox: no host files beyond its own data, no network, no devices, unless granted; portals for the rest | low: the OS's own | runtimes shared, disk-heavy | for external GUI apps | **adopt** for external GUI apps |
| **XDG desktop portals** | D-Bus services safe to expose to sandboxed apps (files, screenshots, notifications, camera, global shortcuts...) | how sandboxed apps reach the desktop; Send to MIA's capture | standard across GNOME and KDE; user-mediated | a portal per kind of access | portals are designed for untrusted callers; prefer them to filesystem grants | none extra | small | for capture and later a MIA portal | **adopt** |
| **D-Bus** | the desktop's IPC | notifications, portals, global shortcuts | universal on Linux desktops | not ideal for MIA's own app traffic (HTTP/JSON already exists) | system bus access must be avoided by apps | low | small | desktop integration only | **use for desktop integration**, not as MIA's app API |
| **systemd user services** | per-user services, sandbox directives | the MIA Runtime already ships as one (`deploy/mia-runtime.service`) | restart, logs, lingering, `ProtectSystem`, `PrivateNetwork`, cgroup limits | per-unit configuration | strong sandbox directives | low | small | yes | **adopt** (runtime, extension host processes) |
| **Wayland integration** | the display protocol | the cage MIA session and KDE (DEC-0157) | security by design (no global input snooping) | no universal right-click hook; global shortcuts via portal | good | — | — | yes | **constraint**, already in the UAL plan |
| **Linux namespaces / bubblewrap** | process isolation without root | the extension sandbox | what Flatpak uses; fine-grained; unprivileged | needs a careful profile | strong with seccomp | medium | small | extensions | **adopt** for the extension host (prototype first) |
| **SELinux / AppArmor** | mandatory access control | defence in depth | Fedora ships SELinux enforcing | policy writing is specialised | strong | high to customise | small | the OS default stays on | **keep Fedora's SELinux defaults**; no custom policy now (Prompt 13) |
| **Containers (podman, OCI)** | isolated services and images | bootc images are OCI; heavy services (SearXNG, model servers) | rootless podman; same format as the OS image | heavier than a process | good | medium | moderate | services, not apps | **use for heavy separate services** |
| **Web runtimes** | MIA's screens run in a browser engine | the web front end is MIA's UI (DEC-0017) | one UI on every device | the window host (Qt WebEngine today; a browser in the cage session later) | content from MIA's own server only | low | moderate | yes | **keep** |
| **Android compatibility (Waydroid)** | Android in a container on Linux | Android apps on the PC | works on Wayland; Intel and AMD GPUs best; NVIDIA weaker | Wayland only; image is older Android | container isolation | medium | heavy | not needed: MIA on Android stays on the phone | **optional**, not part of the framework |
| **AppImage** | single-file Linux apps | — | portable | no sandbox, no updates | weak | — | — | no | **reject** |
| **rpm-ostree layering** | adding packages to the image | — | works | Fedora advises layering sparingly; bootc's local layering isn't settled | — | — | — | build into the image instead | **avoid** |
| **Signing: cosign / Sigstore** | sign OCI artifacts | the bootc image | key or keyless; offline verification bundles | needs key care | strong | low | — | the OS image | **adopt** for the image |
| **Signing: GPG (Flatpak/OSTree repos)** | repository signatures | Flathub | the existing standard there | key management | strong | low | — | GUI apps | **use as is** |
| **WebAssembly components** | sandboxed portable modules | an alternative extension host | strong isolation, small | Python support immature | strong | medium | small | maybe later | **prototype later** |
| **Event/message architecture** | async messages between processes | out-of-process events | decoupling | delivery guarantees to design | — | medium | small | the local API's live channel | **Prompt 05** |
| **API versioning and service discovery** | stable contracts | the local API and capabilities | — | discipline | — | low | — | yes | **path versions + per-capability versions** |

## Rejected alternatives, briefly

- **A MIA package format and store:** duplicates Flatpak and the image (DEC-0119: no marketplace).
- **Each first-party app as its own service:** costs every cross-app join a network hop for isolation MIA doesn't need
  between its own parts (DEC-0175).
- **In-process third-party plugins:** no isolation at all (R-04).

## Sources

- Flatpak, Sandbox Permissions and the Permissions Reference: https://docs.flatpak.org/en/latest/sandbox-permissions.html ,
  https://docs.flatpak.org/en/latest/sandbox-permissions-reference.html
- Matthias Clasen, "Flatpak – a look behind the portal": https://blogs.gnome.org/mclasen/2018/07/19/flatpak-a-look-behind-the-portal/
- Fedora Atomic Desktops, Getting Started (Flatpak primary, layering sparingly): https://docs.fedoraproject.org/gl/atomic-desktops/getting-started/
- "What's new for Fedora Atomic Desktops in Fedora 42" (bootable containers next): https://planet.kde.org/siosms-blog-2025-04-14-whats-new-for-fedora-atomic-desktops-in-fedora-42
- Fedora bootc local layering tracker: https://gitlab.com/fedora/bootc/tracker/-/issues/4
- Waydroid on the Arch Wiki: https://wiki.archlinux.org/title/Waydroid ; Waydroid 1.6.2 Vulkan on Intel Xe:
  https://ubuntuhandbook.org/index.php/2026/02/waydroid-1-6-2-added-vulkan-support-for-intel-xe-graphics-driver/
- Cosign (Sigstore): https://sources.debian.org/src/cosign/2.6.2-1/README.md
