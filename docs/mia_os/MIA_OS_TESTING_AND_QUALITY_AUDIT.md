# MIA OS: testing and quality audit (Prompt 01 §12)

*Claude, 2026-11-15, at `c0a71610`. Every result below comes from a
real run in this session. Nothing is copied from an earlier report.*

## 1. Environment and commands

- **Machine:** Linux cloud container, 4 CPUs, 15 GB RAM. No GPU, no Ollama, no audio devices, outbound network limited.
- **Python:** 3.13 (`/usr/bin/python3`); the image's default `python3` 3.11 had no packages.
- **Setup steps that a fresh Linux machine needed:**
  1. `pip install -U --ignore-installed wheel setuptools`, because the image's old `wheel` couldn't build the sdists for `plaid-python`, `http-ece` and `srt`.
  2. `pip install -r requirements.txt`.
  3. `apt-get install libegl1 libgl1 libxkbcommon0 libfontconfig1 libdbus-1-3 libportaudio2 libglib2.0-0`. Without them, 58 test files failed to import PySide6 (`libEGL.so.1` missing).
- **Command:** `QT_QPA_PLATFORM=offscreen TZ=UTC python3 -m pytest -q -p no:cacheprovider`. `pytest.ini` limits collection to `tests/`.

## 2. Result (full MIA suite, `tests/`)

**6,284 passed, 8 failed, 5 skipped, 12 warnings in 163.75 s.**

The 8 failures fall into three groups.

| Group | Tests | Cause (verified) | Real defect? |
|---|---|---|---|
| Order-dependent: sealing at rest | `test_life_events::…sealed_json_record`, `test_living_worlds::test_the_store_is_sealed_on_disk`, `test_seasons::…sealed_on_disk…`, `test_your_data::…whether_it_s_sealed` | `tests/conftest.py` gives the whole run a test key (`at_rest.use_key`). `tests/test_id_wallet.py` resets it with `use_key(None)` ("go back to the real one"), and on Linux the real one is "no DPAPI, files stay plain". Every sealing test after it fails. Reproduced: `pytest tests/test_id_wallet.py tests/test_life_events.py …` gives 4 failed, 33 passed; each file passes alone. Windows CI hides it because DPAPI exists there. | **Yes, test isolation.** It will fail on any Linux runner, so it must be fixed before Linux CI (R-07) |
| Order-dependent, cause not isolated | `test_response_style::test_a_pick_moves_the_preferred_value_and_persists`, `test_server_app::test_the_recovery_key_is_shown_only_on_this_pc…` | Both pass alone (`test_response_style.py` 7 passed; `test_server_app.py` 70 passed). Probably the same reset or another shared-state leak; not isolated in this audit | Yes (test isolation), unconfirmed cause |
| Environment-dependent | `test_navigation_module::test_sun_moon_summary_for_real_coordinates_has_sensible_shape` | Assumes a US time zone: passes with `TZ=America/Chicago` (6 passed), fails with `TZ=UTC` | Test assumes a time zone |
| Environment-dependent | `test_dashboard_week::test_the_weather_card_asks_for_a_town_then_shows_the_forecast` | `core/weather.py` `_do(..., fetch=_fetch_json)` binds the fetcher as a default argument, so the test's `monkeypatch.setattr(weather, "_fetch_json", …)` doesn't reach it, and the test makes a **real network call**. It fails offline | Yes: the test isn't hermetic |

**Not run here:**
- `homestead/` (its own suite of 245 scenarios, run from inside `homestead/`);
- `tests/live_model_check.py` (needs the model);
- `tools/page_check.py` (needs Playwright browsers);
- the Android build;
- the Windows installer job.

So **this result is "the MIA suite on Linux"**, not "everything".

## 3. Test infrastructure

- **Unit and integration:**
  - pytest, 479 files;
  - fixtures in `tests/conftest.py`;
  - a guard against tests writing into the real `data/` (added after K-0224).
- **API:** `tests/test_server_app.py` (70 tests, Starlette TestClient).
- **The assistant:**
  - a scripted-model turn harness;
  - `tests/live_model_check.py`, with person cases and a dead-end pattern, run by `model-check.yml` or by hand on the PC.
- **UI:**
  - Qt widgets offscreen;
  - `tools/page_check.py` opens every web page (Playwright).
- **Rules that tests enforce:**
  - documentation for every definition (`test_documentation.py`, baselines);
  - loop coverage;
  - parity;
  - Life State schema;
  - no secrets in logs.
- **CI** (`.github/workflows/`):
  - Windows: installer and tests;
  - both Android apps;
  - Pages preview;
  - model check;
  - food table.
  - There is **no Linux test job**.
- **Hardware tests:** none automated. The Pi, audio, GPU, glasses and greenhouse are checked by hand, per `docs/KNOWN_ISSUES.md`.
- **Results recorded:** in CI logs and hub notes. There is no stored test-history dashboard.
- **Coverage:** no coverage tool is configured, so no percentage is claimed.

## 4. Quality gaps

1. **There is no Linux CI.** The order-dependent failures above show what that hides.
2. **Hardware-dependent paths have no automated checks:** voice, GPU, Pi, glasses and the greenhouse nodes.
3. **Live-model quality isn't continuous.** The dead-end check needs a manual PC run.
4. **No build is reproducible** (no lockfile, R-08).
5. **Some tests depend on the network or the time zone** (above).
6. **`docs/KNOWN_ISSUES.md` contains stale "Open" entries.** For example, "MIA Home's move onto Windows is unverified" is still open, while the hub says the PC is used daily.
