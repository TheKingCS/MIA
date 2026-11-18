# MIA OS: building the Linux image (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only. The image: DEC-0189; updates: DEC-0257.*

| Step | How |
|---|---|
| Base | `quay.io/fedora/fedora-kinoite` (Fedora Atomic KDE) at a pinned version |
| Layers | MIA's packages from Fedora (verified by the PoC: everything MIA needs is packaged), her code into `/usr/lib/mia`, systemd units, default config, Plymouth theme, SDDM sessions |
| Build | `podman build` in CI on every push to `master` touching `os/`, `core/`, `server/`, `web/`, `deploy/` |
| Test | boot the image in a VM (`mia-os-vm.yml`): reaches login, the runtime reaches core ready, the suite passes inside |
| Sign | cosign, keyless (GitHub's OIDC) or a key in secrets |
| Publish | GitHub Container Registry (ghcr.io), tagged by version and `stable` |
| Install | an ISO from the image (`bootc-image-builder`) for a new machine |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-015 | Each image shall be booted in a VM and reach MIA's core readiness before it's published. | Must | R1 | PC | Partial (the VM workflow) | T | DEC-0264, DEC-0257 → 15, 14 |
