# MIA OS: the final technology stack (Prompt 17 §7 and §8)

*Claude (Opus), 2026-11-18. Version 1.0. Every choice was rechecked against primary sources on 2026-11-18 (§3). The
labels are **V** verified from a primary source or by running it, **R** an engineering recommendation, **A** an
assumption a proof of concept must settle. Where this document and an older evaluation disagree, this one governs
(DEC-0275).*

## 1. The stack, by domain

| Domain | Choice | Alternatives | Release | Evidence | Licence | Notes |
|---|---|---|---|---|---|---|
| Distribution | **Fedora Atomic KDE (Kinoite) 45**, the ostree-native container run with bootc | Ubuntu 26.04 with an image tool (the fallback if PoC 1 fails) | MVP | V: F45 released; Kinoite 45 ships Plasma 6.7. A: Fedora's bootc-native desktops are "in transition" | various free | Pin the base by digest (DEC-0279) |
| Kernel | Fedora's, unmodified, never rebuilt in the image | — | MVP | V: kernel 7.2 in F45 | GPL-2.0 | Rebuilding it would break Secure Boot |
| Boot and Secure Boot | Fedora's signed shim, GRUB and kernel | sealed UKI images (experimental in bootc, test keys only) | MVP | V | — | Out-of-tree modules would need MOK signing: none planned |
| Init and services | systemd, with MIA's runtime as a **user** service (`Type=notify`, `WatchdogSec`) | — | MVP | V | LGPL-2.1 | A user unit's watchdog restarts the service; it can't reboot the machine |
| Image updates | **bootc** (`upgrade`, `switch`, `rollback`) | — | MVP | **V by execution**: VM run 43872077107 (install, boot, switch, rollback) | Apache-2.0 / MIT | /etc returns to the old deployment's copy on rollback |
| Automatic rollback | **greenboot-rs** (Fedora package `greenboot` 0.16.4), added to the image | none | MVP | V: package; A: rollback on this boot loader setup, including a failure before userspace | LGPL-2.1 | Proven in FW-04 |
| Login | **Plasma Login Manager** (Fedora 44 and later's default for KDE, Kinoite included) | SDDM (kept on upgraded systems) | MVP | V | GPL | Replaces "SDDM" throughout (DEC-0278). Custom session entries: A |
| Desktop | KDE Plasma 6 on Wayland, KWin | — | MVP | V: Plasma is Wayland-only since 6.8, and Fedora has had no Plasma X11 session since F40 | GPL/LGPL | |
| MIA's session | `kwin_wayland` running her shell full screen | **cage** 0.3.1 (Fedora 45) if PoC 3 fails | MVP | A: KWin has no supported kiosk mode (community practice only) | GPL / MIT | PoC 3 in FW-03 |
| Her shell | Qt WebEngine host (PySide6) showing her web front end | Chromium in kiosk mode | MVP | V: PySide6 6.12 split WebEngine into its own wheel | LGPL-3.0 | Pin `PySide6<6.12` until `PySide_WebEngine` ships, then add it |
| Filesystem and disk | Btrfs on LUKS2; `/var/home` for his data | ext4 | MVP | V: the VM installs with Btrfs | GPL | Snapshots before updates (REQ-REL-024) |
| Disk unlock | `systemd-cryptenroll --tpm2-pcrs=7 --tpm2-with-pin=yes`, plus a recovery key | TPM only | MVP | V: the default binds no PCRs; PCRs 4, 8 and 9 change on bootc updates | LGPL | DEC-0277; Q-106 |
| Privileged operations | polkit and a MIA helper with fixed operations over D-Bus | — | MVP | V (standard) | LGPL | PoC 5 in FW-06 |
| Sandboxing | systemd unit hardening; **Landlock** for workers | bubblewrap | MVP / Alpha | V: ABI 10 in kernel 7.2; **by execution**: PoC 6 passes in CI | GPL-2.0 | Probe the ABI at runtime; check `/sys/kernel/security/lsm` |
| Languages | Python 3.13 (MIA), JavaScript (web), Kotlin (phone) | — | MVP | V: python3.13 3.13.18 in F45 | PSF | Windows CI uses 3.12: aligned in FW-02 |
| MIA's core | the existing runtime (`core/`), FastAPI server (`server/`) | — | MVP | V by execution: the runtime up in the VM | — | Not rewritten (17b §2) |
| Model server | **Ollama** on ROCm | upstream Ollama's own Linux build (bundled runners); llama.cpp | MVP | V: the RX 7900 XTX is in Ollama's supported list; Fedora's `ollama-rocm` is 0.24, upstream 0.35 | MIT | Q-68 kept qwen2.5:14b |
| GPU compute | ROCm from **Fedora's packaging** (rocm-hip 7.2.2 in F45) | Ollama's Vulkan backend | MVP | V: AMD lists gfx1100 but supports only Ubuntu and RHEL; A: Fedora's ROCm on his card (PoC 1) | MIT | |
| Models | qwen2.5:14b everyday (32k context), the strong and specialist models (DEC-0206 to 0212) | — | MVP | V on Windows: flash attention and the q8_0 cache measured | various | Models are settings, never in the image |
| Memory and data | his JSON stores with atomic writes, sealed at rest; the history (`life_events`); links; the recall index | sqlite-vec for recall at R1 (DEC-0210) | MVP | V: 56 sealed names | — | |
| Communication | HTTP and server-sent events for surfaces; D-Bus to the OS; the event bus inside | gRPC (rejected: nothing needs it) | MVP | V | — | DEC-0192 |
| Voice in | Vosk (current) | **whisper.cpp** (active, ROCm and Vulkan builds) | MVP: Vosk; Alpha: whisper.cpp if measured better | V: Vosk's last PyPI release is 2022 | Apache-2.0 / MIT | DEC-0211 |
| Voice out | Kokoro (main) | Piper (fallback, the Pi) | MVP | V: Piper moved to `OHF-Voice/piper1-gpl`, GPL-3.0, looking for maintainers | Apache-2.0 / GPL-3.0 | Q-108 (licence) |
| Her browser | Playwright with Chromium in the image | Edge (pinned in the image if kept) | Alpha | V: Edge works on Linux but starts a CPU-heavy model service after launch | Apache-2.0 | DEC-0117's gate unchanged |
| Devices | the phone app, the glasses through it; pairing keys (hash only on the hub) | — | MVP | V by execution on Windows | — | WP-10 adds device records |
| Remote access | **Tailscale** from its own RPM repository, only away from home | WireGuard by hand | MVP | V: Fedora's own package has lagged with a security issue | BSD | DEC-0244 |
| Smart home and homestead | MIA Homestead over snapshots; controllers keep their loops | Home Assistant (not planned) | Beta | V (its own suite) | — | DEC-0246 |
| Conventional apps | Flatpak (Flathub) | layered RPMs (avoided) | MVP | V: Fedora Atomic's primary app path | LGPL-2.1 | |
| Build | Podman and `bootc container lint`; `bootc install to-disk` for disk images | bootc-image-builder (couldn't mount its storage on GitHub's runners) | MVP | V by execution | Apache-2.0 | |
| Locking | `uv pip compile --generate-hashes`, installed with `--require-hashes` | pip-tools | MVP | V | MIT / Apache | FW-01 |
| Signing | **cosign** 3.0.4 or later with a key pair; `containers-policy.json` `sigstoreSigned`; `bootc switch --enforce-container-sigpolicy` | keyless (reported not matched by containers/image) | Alpha (the first signed release) | V | Apache-2.0 | FW-08 |
| SBOM | syft (SPDX) | — | Alpha | V | Apache-2.0 | |
| Testing | pytest (6,828 tests); the VM test under QEMU/KVM | — | MVP | V | MIT | KVM on GitHub's runners works but isn't a documented guarantee |
| CI | GitHub Actions on Linux and Windows | — | MVP | V | — | Actions pinned by SHA (FW-02) |
| Observability | the journal, `systemd-analyze`, her own counters and `/api/runtime/health` | Prometheus (not planned) | MVP | V | — | DEC-0195 |

## 2. By release

| Release | Adds |
|---|---|
| **MVP** | Kinoite 45 by digest, bootc, greenboot-rs, Plasma Login Manager entries, KWin session (cage fallback), the WebEngine shell, LUKS2 with TPM on PCR 7 and a PIN, the helper, Ollama on Fedora's ROCm, Vosk, Kokoro, Flatpak, Tailscale, uv locks, the VM test |
| **Alpha** | cosign-signed images, syft SBOMs, whisper.cpp if measured better, Chromium for her browser, Landlock on workers |
| **Beta** | the Pi with cage and the household key; the laptop as a full engine; homestead actions through the action contract |
| **Stable** | nothing new: three monthly releases with no rollback |
| **Later, optional** | sqlite-vec recall at scale, a model-serving node, WebXR spatial views, sealed UKI images when bootc's composefs leaves experimental |

## 3. Corrections from the 2026-11-18 check

| Claim in earlier documents | Finding | Correction |
|---|---|---|
| "a changed boot chain asks for the recovery key" | systemd-cryptenroll binds no PCRs unless told; boot-chain PCRs change on every bootc update | DEC-0277: PCR 7 with a PIN |
| "Fedora's GPU stack AMD supports" | AMD's matrix lists no Fedora | Support comes from Fedora's packaging; PoC 1 decides |
| SDDM as the login manager | Plasma Login Manager is Fedora 44 and later's default for KDE | DEC-0278 |
| "a bootc image" | Kinoite is ostree-native, run with bootc; bootc-native desktops are in transition | Wording changed |
| greenboot checks give rollback | greenboot isn't in Kinoite by default | Added to the image; proven in FW-04 |
| `OLLAMA_MAX_LOADED_MODELS` "default 1" | default is 3 per GPU | Our 2 is a reduction |
| ROCm 7.1 | Fedora 45 has 7.2.2 (7.1 was Fedora 44) | Corrected |
| Piper (MIT) | the maintained fork is GPL-3.0, looking for maintainers | Fallback only; Q-108 |
| PySide6 `<7.0` is safe | 6.12 split WebEngine into its own wheel | `<6.12` for now |
| cosign keyless | keyless identities are reportedly not matched by bootc's policy | a key pair |

Sources (all read 2026-11-18): Fedora Magazine on Atomic Desktops in Fedora 45; the bootc and bootc-install-to-disk
manual pages; github.com/fedora-iot/greenboot-rs; the KDE blog on the Wayland-only Plasma 6.8; Fedora's Plasma Login
Manager change page; packages.fedoraproject.org for cage, python3.13, ollama-rocm and rocm-hip; the systemd 262
systemd-cryptenroll manual; docs.kernel.org Landlock for 7.2; docs.ollama.com GPU and FAQ; AMD's ROCm system
requirements; github.com/OHF-Voice/piper1-gpl; pypi.org/project/vosk; playwright.dev browsers; tailscale.com's RPM
install guide; the Sigstore cosign 3.0 announcement and containers-policy.json(5); github.com/anchore/syft;
docs.astral.sh/uv; the GitHub changelog of 2024-04-02 on KVM on hosted runners; the Qt for Python development notes.
