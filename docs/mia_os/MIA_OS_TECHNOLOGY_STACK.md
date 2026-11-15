# MIA OS: technology stack inventory (Prompt 01 §5)

*Claude, 2026-11-15, at `c0a71610`. Where the versions come from:*
- *declared versions are from `requirements.txt` and the Gradle and npm files;*
- *installed versions are what `pip install -r requirements.txt` resolved in this Linux cloud session (Python 3.13) on 2026-11-15.*

*The PC's installed versions weren't checked. CI's Windows job pins Python 3.10–3.14 (`deploy/find_python.ps1`).*

**Foundational** means MIA doesn't run without it. **Incidental** means a single feature uses it.

| Component | Technology | Declared | Installed here | Purpose | Status | Role |
|---|---|---|---|---|---|---|
| Language | Python | 3.10–3.14 (CI) | 3.13 | engine, server, Qt app | Verified | Foundational |
| API server | FastAPI | ≥0.141,<1 | 0.163.0 | `server/app.py`, 265 routes | Verified (tests) | Foundational |
| ASGI server | uvicorn | ≥0.52,<1 | 0.54.0 | hosts the API | Verified | Foundational |
| Crypto | cryptography | ≥50.0.2,<51 | 50.0.2 | AES-GCM at rest, vault, tokens | Verified (tests) | Foundational |
| Desktop UI | PySide6 (Qt 6) | ≥6.6,<7 | 6.12.0 | Qt shell and web view | Implemented | Foundational on PC; absent from the engine |
| Web UI | plain HTML, CSS and JS; no framework or build step | — | — | `web/`: 102 pages, tokens and themes | Verified (page check, tests) | Foundational |
| Local LLM | Ollama (HTTP) | external | not here | PC model server | Documented / implemented | Foundational on PC |
| Local LLM | llama.cpp `llama-server` (OpenAI-compatible) | external | — | phone model | Implemented | Foundational on phone |
| Speech to text | Vosk | ≥0.3.45,<0.4 | 0.3.45 | offline recognition | Implemented | Incidental |
| Text to speech | Piper, Kokoro (onnx) | piper ≥1.4; kokoro-onnx ≥0.4 | 1.8.0; 0.6.1 | voices (Kokoro on PC, DEC-0051) | Implemented | Incidental |
| Audio I/O | sounddevice / PortAudio | ≥0.5,<0.6 | 0.5.6 | microphone and speaker | Implemented | Incidental |
| Numeric | numpy | ≥1.26,<3 | 2.5.3 | audio, calculations | Verified | Incidental |
| Imaging | Pillow | ≥10,<14 | 12.3.0 | photos, thumbnails | Verified | Incidental |
| Offline reference | libzim | ≥3.7,<4 | 3.13.1 | `.zim` reference library | Implemented | Incidental |
| Push | pywebpush | ≥2.5,<3 | 2.5.0 | web push to the phone | Implemented | Incidental |
| Bank | plaid-python | ≥44,<45 | 44.0.0 | read-only bank data | Implemented | Incidental (cloud service) |
| Browser automation | Playwright (Edge on PC) | ≥1.45,<2 | 1.65.2 | her browser (DEC-0117) | Implemented | Incidental |
| System info | psutil | ≥6,<8 | 7.2.2 | power, processes | Verified | Incidental |
| Serial | pyserial | ≥3.5,<4 | 3.5 | devices, greenhouse | Implemented | Incidental |
| Metadata | mutagen | ≥1.48,<2 | 1.48.1 | music tags | Implemented | Incidental |
| Sun times | astral | ≥3.2,<4 | 3.2 | sunrise and sunset | Verified (TZ-dependent test) | Incidental |
| Test client | httpx2 | ≥2.12,<3 | 2.13.1 | needed by Starlette's TestClient for `tests/test_server_app.py`; not imported by the app | Verified | Development only |
| Tests | pytest | ≥7.4 | 9.2.0 | suite | Verified | Foundational (development) |
| Storage | JSON / JSONL files, atomic writes | — | — | nearly every store | Verified | Foundational |
| Storage | SQLite (stdlib) | — | — | development platform (`council.py`, `dev_store.py`), two device stores | Implemented | Incidental |
| Android | Kotlin 2.2.21, AGP; compileSdk 36, minSdk 29, targetSdk 34 | `android-phone/*.gradle.kts` | — | phone app | Verified by CI builds (per hub) | Foundational on phone |
| Android Python | Chaquopy 17.0.0, Python 3.13 | gradle | — | engine on the phone | Implemented | Foundational on phone |
| Glasses SDK | Meta Wearables DAT 1.0.1 (core, display, camera) | gradle | — | glasses | Implemented | Foundational for glasses |
| Android HTTP | OkHttp 4.12.0, coroutines 1.10.2 | gradle | — | relay, network | Implemented | Incidental |
| Relay | Cloudflare Workers, wrangler 4.156.1 | `relay/package.json` | — | sealed glasses relay | Implemented | Foundational for glasses display |
| Remote access | Tailscale (`tailscale serve`) | external | — | phone ↔ PC away from home | Documented / implemented | Foundational for reach |
| Homestead | pyyaml (plus optional anthropic) | `homestead/requirements.txt` | — | homestead subproject | Implemented | Self-contained |
| CI | GitHub Actions: `windows.yml`, `android.yml`, `android-phone.yml`, `pages.yml`, `model-check.yml`, `food-table.yml` | — | — | build, test, publish APKs, preview | Verified (files); results per hub | Foundational (development) |
| Pi deployment | systemd **user** service, kiosk | `deploy/` | — | Pi | Implemented, unverified on hardware | Later (DEC-0015) |
| Windows deployment | PowerShell installers, Task Scheduler stay-up, autologon | root `*.ps1` | — | PC | Implemented | Foundational on PC |

**What to watch:**
- **httpx2** is test-only (Starlette's TestClient). Its package metadata names the httpx author; keep watching it, since it's a newer package name.
- **The Plaid SDK** is pinned to one major version; Plaid moves often.
- **Meta's toolkit 1.0.1** is early and its terms are controlled by Meta.
- **There is no lockfile or hash pinning for Python** (ranges only), so builds aren't reproducible. This is risk R-08.
- **Building in a fresh Linux container** needs current `setuptools`/`wheel` (sdists for plaid-python, http-ece and srt) and the system libraries `libegl1` and `libgl1` for PySide6. Both were found the hard way in this audit.
