"""
tests.conftest
================

Session-wide test setup.

Redirects core.logger's log file into a scratch temp directory before
any test runs. core/logger.py's root logger is configured once per
process (guarded by a module-level flag) and its file path is a
hardcoded module-level constant, not something individual tests can
isolate the way test_config_manager.py isolates ConfigManager's paths.
Without this, running the suite appends real log lines (including
expected-but-noisy module_manager rescan output) straight into the
developer's actual logs/mia.log — which is exactly what an in-app log
viewer (Diagnostics, see modules/diagnostics/module.py) would then
surface as confusing clutter.

Same reasoning for core.profile_manager's `_DATA_PROFILES_DIR`
(2026-09-14, found while building the Rewards system's tests) — every
`ProfileManager.create_profile()` call does a real `mkdir()` for that
profile's reserved data directory against this hardcoded module
constant, which no individual test file (including
tests/test_profile_manager.py itself) has ever isolated. Left alone,
every test-created profile across the whole history of this suite
leaks one empty orphan directory into the real data/profiles/ — found
at 10,033 accumulated directories against a single real profile.

Same reasoning again for core.usage_tracker's `_DATA_DIR`/`_USAGE_FILE`
(2026-09-14, found the same day the module shipped) — any test that
builds a full context via core.core_runtime.build_core_context() or
core.application.MIAApplication (e.g. tests/test_core_runtime.py's own
`context` fixture) constructs a real UsageTracker, which writes a real
data/module_usage.json the moment any "module.opened" event fires,
unless that specific test file happens to isolate this one manager's
paths itself — which none did, since the manager didn't exist when
they were written. Isolating it here, globally, is the fix this
project already learned to reach for instead of patching every
individual fixture one at a time.

This module-level code (not a fixture) runs when pytest loads this
conftest.py, which always happens before any test module is imported —
early enough to win the race against core.module_manager and friends
calling get_logger() at their own module level.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import core.component_manager as component_manager_module
import core.connectivity as connectivity_module
import core.inventory_manager as inventory_manager_module
import core.material_manager as material_manager_module
import core.product_manager as product_manager_module
import core.skill_manager as skill_manager_module
import core.logger as logger_module
import core.profile_manager as profile_manager_module
import core.usage_tracker as usage_tracker_module

_TEST_LOG_DIR = Path(tempfile.mkdtemp(prefix="mia_test_logs_"))
logger_module._LOG_DIR = _TEST_LOG_DIR
logger_module._LOG_FILE = _TEST_LOG_DIR / "mia.log"

_TEST_PROFILES_DIR = Path(tempfile.mkdtemp(prefix="mia_test_profiles_"))
profile_manager_module._DATA_PROFILES_DIR = _TEST_PROFILES_DIR

_TEST_USAGE_DIR = Path(tempfile.mkdtemp(prefix="mia_test_usage_"))
usage_tracker_module._DATA_DIR = _TEST_USAGE_DIR
usage_tracker_module._USAGE_FILE = _TEST_USAGE_DIR / "module_usage.json"

# core.connectivity's background probe (2026-09-27) would otherwise make a
# real network connection whenever a test builds a full context. Tests
# that exercise the monitor inject their own connect function.
def _no_network(*_args, **_kwargs):
    raise OSError("network disabled in tests")


connectivity_module._default_connect = _no_network


# 2026-09-27: the real data/ folder was found holding test-written usage
# logs and a skill XP log (entries from ordinary `pytest` runs). Not every
# test that triggers them isolates these runtime files, so they default to
# a temp dir for the whole session; tests that set their own paths still
# override this. Tracked seed files (skill_definitions.json,
# mission_pathways.json) are deliberately left pointing at the real ones.
_TEST_RUNTIME_DIR = Path(tempfile.mkdtemp(prefix="mia_test_runtime_"))
for _module in (inventory_manager_module, component_manager_module, material_manager_module, product_manager_module):
    _module._USAGE_LOG_FILE = _TEST_RUNTIME_DIR / _module._USAGE_LOG_FILE.name
skill_manager_module._SKILL_XP_LOG_FILE = _TEST_RUNTIME_DIR / "skill_xp_log.json"
skill_manager_module._SKILL_PROGRESS_FILE = _TEST_RUNTIME_DIR / "skill_progress.json"


# Guard: the test suite must never touch the real data/ folder. Snapshot
# it at session start and fail the run, naming the files, if anything was
# added or changed by the end.
_REAL_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _data_snapshot() -> dict[str, float]:
    if not _REAL_DATA_DIR.exists():
        return {}
    return {
        str(p.relative_to(_REAL_DATA_DIR)): p.stat().st_mtime
        for p in _REAL_DATA_DIR.rglob("*")
    }


def pytest_sessionstart(session):
    session.config._mia_data_snapshot = _data_snapshot()


def pytest_sessionfinish(session, exitstatus):
    before = getattr(session.config, "_mia_data_snapshot", None)
    if before is None:
        return
    after = _data_snapshot()
    touched = sorted(name for name, mtime in after.items() if before.get(name) != mtime)
    if touched:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        message = "Tests wrote into the real data/ folder: " + ", ".join(touched)
        if reporter is not None:
            reporter.write_line(message, red=True)
        session.exitstatus = 1
