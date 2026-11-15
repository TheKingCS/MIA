# MIA OS: preliminary migration readiness (Prompt 01 §16)

*Claude, 2026-11-15. This is preliminary: no technology or migration
decisions are made here (they belong to Prompts 05 and 16).*

*Classes (from Prompt 01):*
1. *Reusable with minimal changes.*
2. *Reusable with adaptation.*
3. *Needs significant refactoring.*
4. *Needs replacement.*
5. *Not suitable for migration.*
6. *Not enough information.*

*Column key:*
- *Indep. UI: works without the current interface.*
- *Win: depends on Windows.*
- *Cloud: depends on a cloud service.*
- *Svc: needs a persistent service.*
- *HW: needs hardware access.*
- *Tests: has meaningful tests.*

| Component | Indep. UI | Win | Cloud | Svc | HW | Tests | Class | Reasoning |
|---|---|---|---|---|---|---|---|---|
| Action contract, undo, life events, links | yes | no | no | no | no | yes | **1** | pure Python, tested, the core of authorisation |
| Stores and atomic writes | yes | no | no | no | no | yes | **1** | file-based; runs on Linux in this audit |
| Assistant turn, tools, modes, safety floor | yes | no | no | no | no | yes | **1** | ran headless here; needs grants for system tools later |
| Web front end | yes (it is a UI) | no | no | needs server | no | yes | **1** | runs in any browser |
| API server | yes | no | no | yes | no | yes | **2** | needs a host other than the Qt process |
| Scheduler (QTimers) | no | no | no | yes | no | partial | **3** | Qt-bound; must become a runtime scheduler |
| Headless runtime | yes | no | no | yes | some | some | **2** | the seed of a runtime; lacks server and scheduler |
| Encryption at rest | yes | **yes (DPAPI)** | no | no | no | yes | **2** | needs a Linux key backend and a re-key path |
| Backups | yes | no | no | scheduled | no | yes | **1** | file-based |
| Sync, home link | yes | no | no (Tailscale optional) | yes | no | yes | **1** | same code on Linux |
| LLM backends | yes | no | no | Ollama | GPU | yes (mocked) | **1** | Ollama exists on Linux; ROCm on the 7900 XTX is **6 (unverified)** |
| Voice backends | yes | no | no | audio | yes | partial | **2** | Vosk, Piper and Kokoro run on Linux; audio routing through PipeWire untested |
| Browser (Edge + Playwright) | yes | Edge is | no | no | no | yes | **2** | switch to Chromium on Linux |
| Qt classic view | n/a | no | no | no | no | yes | **2** | PySide6 runs on Linux; becomes a client |
| Desktop host window (web view) | n/a | no | no | no | no | some | **4** | replaced by an OS session on MIA OS |
| Windows installers and stay-up | n/a | yes | no | — | — | CI | **5** | stay for Windows; don't migrate |
| Module system (Qt) | yes | no | no | no | no | yes | **2** | needs sandboxing before third-party use |
| Development platform (council, lab) | yes | no | yes (council) | no | no | yes | **2** | worktree lab works on Linux; sandboxing upgrade |
| Android apps | n/a | no | no | yes | yes | CI builds | **1** (`android-phone`), **6** (`android/` future) | stay Android apps |
| Glasses, relay | n/a | no | Cloudflare, Meta | — | yes | some | **1** | unaffected by the PC's OS |
| Homestead | yes | no | no | yes | yes | own suite | **1** | Linux-first already (rsync scenarios pass on Linux) |
| Device framework, cameras, serial | yes | no | no | no | yes | some | **2** | udev permissions and HAL wrapping |
| Pi kiosk deploy | n/a | no | no | yes | yes | no | **2** | systemd user-service pattern reusable for the PC image |

**Needs more investigation:**
- ROCm or Vulkan inference on the RX 7900 XTX under Linux.
- Kokoro and PipeWire latency.
- Whether the PC has TPM2.
- Uncommitted PC edits.
- The Companion app's future.
- The API thread's restart behaviour.
