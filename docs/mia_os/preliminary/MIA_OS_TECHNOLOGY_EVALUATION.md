# MIA OS technology evaluation

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Options weighed for each layer against Zac's
principles: preserve, no needless rewrites, local-first, security
central, reproducible. Versions and support change; verify before
building.*

## 1. Base operating system

| Option | For | Against | Verdict |
|---|---|---|---|
| **Fedora Atomic / bootc** | image built from a Containerfile in the repo; atomic updates and rollback; recent kernel and Mesa (good for RDNA3); ROCm packaged | newer paradigm; layering packages is different | **Recommended** |
| Ubuntu LTS | familiar; ROCm officially supported | mutable; harder to rebuild exactly; snaps | Fallback |
| NixOS | fully declarative | steep learning curve; unusual for helpers | Not now |
| Arch | current | rolling, hand-built, not reproducible | No |
| Own distribution / Yocto | full control | years of work; the directive excludes it | No |

## 2. Session and compositor

| Option | Verdict |
|---|---|
| **cage** (Wayland kiosk) + Chromium on the MIA shell | **Recommended** for the MIA session: tiny, proven |
| KDE Plasma as the second session | **Recommended** for conventional desktop work |
| A custom compositor (wlroots, Smithay) | Later, only if MIA needs window control cage can't give |
| GNOME | Fine, but harder to extend for MIA's tray and overlays |

## 3. Runtime and services

- **systemd user services** for the runtime (already the Pi pattern) and
  a system service for Ollama.
- **D-Bus + polkit** for the System Manager. This is the standard Linux
  way to give an unprivileged process narrow root actions.
- Python stays the runtime language: the engine is ~150k lines of tested
  Python, and nothing in the OS work needs another language. A rewrite in
  Rust or Go has no technical reason now (principle 2).

## 4. Models and GPU (RX 7900 XTX, 24 GB)

| Option | Verdict |
|---|---|
| **Ollama on ROCm** | **Recommended**: same backend MIA uses now |
| llama.cpp `llama-server` with Vulkan | Fallback, already supported (`OpenAIBackend`) |
| vLLM on ROCm | Later, for heavier parallel use |

## 5. Security pieces

- **LUKS2 + TPM2 (systemd-cryptenroll)** for the disk.
- **systemd-creds** (TPM2-bound) as the Linux key backend for
  `core/at_rest.py`, matching DPAPI on Windows. libsecret is an
  alternative but depends on a desktop session.
- **Flatpak** for apps; **bubblewrap / podman** for agents and untrusted
  modules.
- **SELinux** is on by default in Fedora; keep it on.
- Signed images: **bootc** pulls signed images (cosign/sigstore).

## 6. Phone

| Option | Verdict |
|---|---|
| **MIA's Android app as the default assistant (RoleManager ASSISTANT) and optionally as launcher (HOME)** | **Recommended**: no ROM, keeps updates and banking apps |
| A custom ROM (LineageOS, GrapheneOS fork) | No: breaks banking apps and updates, and Meta's toolkit |

## 7. Pi

Raspberry Pi OS with today's kiosk service. Revisit a bootc-style image
only after the PC image is proven.

## 8. Not needed (no new dependencies without a reason)

- no message broker (the API and `/api/live` suffice for one machine);
- no database migration (JSON stores work and are tested);
- no container orchestration;
- no Electron (Chromium in cage does the same job).
