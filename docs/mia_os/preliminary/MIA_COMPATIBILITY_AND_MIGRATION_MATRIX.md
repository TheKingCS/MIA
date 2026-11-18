# MIA OS compatibility and migration matrix

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. For each part of MIA:*
- *does it work on each host today;*
- *what happens to it in the migration;*
- *which stage it changes in.*

*✓ = works, ~ = partly, ✗ = not yet, — = not applicable.*

| Component | Windows PC | Linux (MIA OS) | Android | Pi | Migration | Stage |
|---|---|---|---|---|---|---|
| MIA Core (`core/`) | ✓ | ✓ (headless, CI) | ✓ (Chaquopy) | ✓ | unchanged | — |
| Stores (JSON/JSONL) | ✓ | ✓ | ✓ | ✓ | unchanged; moved by backup/restore | 5 |
| Sealed stores | ✓ DPAPI | ✗ | ✓ Keystore | ✗ | key-backend interface, TPM2 backend, re-key | 2 |
| Scheduler | ✓ in Qt | ✗ | ~ (app's own) | ✗ | runtime scheduler | 1 |
| API server | ✓ in Qt | ✗ | ✓ | ✗ | hosted by the runtime | 1 |
| Web front end | ✓ | ✓ (Chromium) | ✓ WebView | ✓ | unchanged | — |
| Qt classic view | ✓ | ✓ (PySide6 runs on Linux) | — | ✓ | becomes a client | 1 |
| Desktop host window | ✓ | replaced by the cage session | — | kiosk | session replaces window | 4 |
| Ollama / models | ✓ (7900 XTX) | ✓ ROCm (to verify) | llama-server | small models | same backend | 5 |
| Kokoro / Piper / Vosk | ✓ | ✓ | Android voice | ✓ | audio through PipeWire | 5 |
| Browser (Edge + Playwright) | ✓ | ~ (Chromium instead) | — | ~ | browser choice per host | 2 |
| Phone sync and home link | ✓ | ✓ (same code) | ✓ | — | re-pair to the Linux runtime | 5 |
| Tailscale serve | ✓ | ✓ | ✓ | ✓ | install in the image | 4 |
| Glasses (toolkit, relay) | via phone | via phone | ✓ | — | unchanged | — |
| Autofill | — | — | ✓ | — | unchanged | — |
| Plaid (finances) | ✓ | ✓ | ✓ | — | unchanged | — |
| Homestead / greenhouse | ✓ (3 rsync scenarios fail on Windows) | ✓ | — | ✓ | unchanged | — |
| Cameras, serial devices | ✓ | ✓ (udev rules) | — | ✓ | HAL wrapper | 6 |
| Council / dev lab | ✓ | ✓ (git worktree, podman sandbox) | — | — | sandbox upgrade | 6 |
| Windows scripts (`install.ps1`, stay-up) | ✓ | — | — | — | kept for Windows | — |
| Kiosk deploy | — | pattern reused | — | ✓ | unchanged | — |
| Tests (~4,600) | ✓ (CI) | ✓ (cloud) | — | — | Linux CI job added | 2 |

## Data migration (Windows → MIA OS)

1. Nightly encrypted backup (already exists).
2. On MIA OS: restore, then re-key the sealed stores from the backup
   passphrase into the TPM2 backend.
3. The phone re-pairs; sync reconciles.
4. Windows MIA is set to read-only (store lock) until Zac retires it.

Nothing is converted. The files are the same files.

## What could break, and the guard

| Risk | Guard |
|---|---|
| Data unreadable after re-key | backup first; restore drill in tests |
| Two MIAs writing the same data | store lock and hand-over procedure |
| A Windows-only path in core | Linux CI fails on it |
| Phone loses the PC | home link falls back to the phone's model (already does) |
| GPU driver on Linux | llama-server Vulkan fallback; Windows still there |
