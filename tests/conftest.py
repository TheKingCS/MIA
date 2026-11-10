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

And Qt draws off-screen (2026-11-07): a test that makes a window or
dialog would otherwise flash it onto the PC's real desktop.

This module-level code (not a fixture) runs when pytest loads this
conftest.py, which always happens before any test module is imported —
early enough to win the race against core.module_manager and friends
calling get_logger() at their own module level.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

# Qt draws off-screen (2026-11-07): without this, every test that makes a MIA window or dialog flashed it onto the
# PC's real desktop, hundreds of times a run, and Zac couldn't use his PC while the suite ran. Set before anything
# imports PySide6. Night School's own runs already did this (core/dev_lab.py).
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# The log first (2026-10-21): any core module calls get_logger() when it's
# imported, which opens the log file then. Redirected after the other
# imports, the suite was still writing into the real logs/mia.log.
import core.logger as logger_module

_TEST_LOG_DIR = Path(tempfile.mkdtemp(prefix="mia_test_logs_"))
logger_module._LOG_DIR = _TEST_LOG_DIR
logger_module._LOG_FILE = _TEST_LOG_DIR / "mia.log"

import core.component_manager as component_manager_module  # noqa: E402
import core.config_manager as config_manager_module  # noqa: E402
import core.connectivity as connectivity_module  # noqa: E402
import core.inventory_manager as inventory_manager_module  # noqa: E402
import core.material_manager as material_manager_module  # noqa: E402
import core.product_manager as product_manager_module  # noqa: E402
import core.skill_manager as skill_manager_module  # noqa: E402
import core.profile_manager as profile_manager_module  # noqa: E402
import core.usage_tracker as usage_tracker_module  # noqa: E402

_TEST_PROFILES_DIR = Path(tempfile.mkdtemp(prefix="mia_test_profiles_"))
profile_manager_module._DATA_PROFILES_DIR = _TEST_PROFILES_DIR

# 2026-10-01: core.personal_data moves the formerly shared personal files
# (conversations, journal...) from data/ into the owner's profile folder
# once. In a test run that must never touch real files: point its
# "formerly shared" folder at an empty temp dir. (Its profiles folder is
# ProfileManager's, redirected just above.)
import core.personal_data as personal_data_module  # noqa: E402

personal_data_module._DATA_DIR = Path(tempfile.mkdtemp(prefix="mia_test_shared_"))

_TEST_USAGE_DIR = Path(tempfile.mkdtemp(prefix="mia_test_usage_"))
usage_tracker_module._DATA_DIR = _TEST_USAGE_DIR
usage_tracker_module._USAGE_FILE = _TEST_USAGE_DIR / "module_usage.json"

# 2026-10-20: most tests build `ConfigManager()` with no path, which read
# and saved the real config/config.json. On Zac's PC one `pytest` run
# left 49 test profiles ("Alex", "Faith") there and made one of them the
# active profile, so MIA started as "Faith". The session shares one temp
# config instead (the same thing CI has always had: no config.json at the
# start); the versioned defaults stay the real ones.
# The shared development history (core/dev_history.py, T-0021): agents' briefings read it, so a test reads an
# empty temp one, never the PC's.
import core.dev_history as dev_history_module  # noqa: E402

dev_history_module.HISTORY = Path(tempfile.mkdtemp(prefix="mia_test_history_"))

_TEST_CONFIG_DIR = Path(tempfile.mkdtemp(prefix="mia_test_config_"))
config_manager_module._CONFIG_DIR = _TEST_CONFIG_DIR
config_manager_module._CONFIG_FILE = _TEST_CONFIG_DIR / "config.json"


# core.connectivity's background probe (2026-09-27) would otherwise make a
# real network connection whenever a test builds a full context. Tests
# that exercise the monitor inject their own connect function.
def _no_network(*_args, **_kwargs):
    """Stands in for network calls in tests: always refuses."""
    raise OSError("network disabled in tests")


connectivity_module._default_connect = _no_network

# 2026-11-08 (T-0054): a turn whose local model doesn't answer starts `ollama serve` on the PC
# (core/llm_manager._wake_local). No test may start a real process: here it never starts anything, and the tests
# of the wake itself fake it.
import core.llm_manager as llm_manager_module  # noqa: E402

llm_manager_module._start_ollama = lambda: False


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

# 2026-11-08: the security log (core/security_log.py) is written by every sign-in a server test makes; it defaults to
# this session's temp dir so no test's sign-ins land in the real data/ (a test that wants its own folder says so).
import core.security_log as security_log_module  # noqa: E402

security_log_module._DATA_DIR = _TEST_RUNTIME_DIR

# 2026-11-08: sealed files (core/at_rest.py, DEC-0126): every test seals with a fixed test key, never DPAPI or the
# real data/.keys, so the whole suite writes and reads the most private stores sealed, as MIA does.
import core.at_rest as at_rest_module  # noqa: E402

at_rest_module.KEY_DIR = _TEST_RUNTIME_DIR / ".keys"
at_rest_module.use_key(bytes(range(32)))

# 2026-11-06: tests that run MIA's daily checks (test_communication_gate)
# ran the PC's improvement loops for real: readings into data/dev/ and a
# task opened in work/tasks/ (T-0049). The development platform's records
# default to a temp dir, and the device's loops act as on a computer
# without the repo (they measure nothing, open nothing) unless a test says
# otherwise (tests/test_loops.py patches `_has_repo`).
import core.benchmarks as benchmarks_module  # noqa: E402
import core.council as council_module  # noqa: E402
import core.council_voices as council_voices_module  # noqa: E402
import core.dev_store as dev_store_module  # noqa: E402
import core.dev_usage as dev_usage_module  # noqa: E402
import core.dependency_audit as dependency_audit_module  # noqa: E402
import core.loops as loops_module  # noqa: E402
import core.night_school as night_school_module  # noqa: E402

_TEST_DEV_DIR = Path(tempfile.mkdtemp(prefix="mia_test_dev_"))
for _module in (dev_store_module, benchmarks_module, council_module, council_voices_module, dev_usage_module, loops_module,
                night_school_module, dependency_audit_module):
    _module.DEV_DATA = _TEST_DEV_DIR
council_voices_module.SAMPLES = _TEST_DEV_DIR / "voices"
import core.phone_link as phone_link_module  # noqa: E402

phone_link_module.FILE = _TEST_DEV_DIR / "phone_link.json"  # a test's linked phone never writes the real one
import core.chronicle_issue as chronicle_issue_module  # noqa: E402
import core.good_news as good_news_module  # noqa: E402

good_news_module.DATA = _TEST_DEV_DIR / "good_news"  # never today's real episode
chronicle_issue_module.PANELS = _TEST_DEV_DIR / "chronicles"
import core.inspection as inspection_module  # noqa: E402

inspection_module._DIR = _TEST_DEV_DIR / "inspections"  # a test that runs an inspection never saves into the real data/
loops_module._has_repo = lambda: False


# Guard: the test suite must never touch the real data/ folder. Snapshot
# it at session start and fail the run, naming the files, if anything was
# added or changed by the end.
_REAL_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_REAL_CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "config.json"


def _data_snapshot() -> dict[str, float]:
    """The modification times of everything in the real data folder, the real config and the work record, and the
    names at the top of the repository, to catch a test writing there."""
    snapshot = {}
    if _REAL_DATA_DIR.exists():
        snapshot = {
            str(p.relative_to(_REAL_DATA_DIR)): p.stat().st_mtime
            for p in _REAL_DATA_DIR.rglob("*")
        }
    if _REAL_CONFIG_FILE.exists():
        snapshot["../config/config.json"] = _REAL_CONFIG_FILE.stat().st_mtime
    work = _REAL_DATA_DIR.parent / "work"  # the development record: tasks and the history (2026-11-06, T-0049)
    for p in [work / "activity.jsonl", *sorted((work / "tasks").glob("*.md"))]:
        if p.exists():
            snapshot[f"../work/{p.relative_to(work).as_posix()}"] = p.stat().st_mtime
    # A new file or folder at the top of the repository (2026-11-10: a store given a MagicMock context made a
    # "MagicMock" folder there, which the data/ snapshot never saw). Names only, so it costs one listing.
    for p in _REAL_DATA_DIR.parent.iterdir():
        if p.name not in (".pytest_cache", "__pycache__", "restore_pending.zip", "pytest-report.xml"):  # CI's report
            snapshot[f"../{p.name}"] = 0.0
    return snapshot


def pytest_sessionstart(session):
    """Takes the snapshot before any test runs."""
    session.config._mia_data_snapshot = _data_snapshot()


def pytest_sessionfinish(session, exitstatus):
    """Fails the run when a test wrote into the real data folder, config or work record, naming what changed."""
    before = getattr(session.config, "_mia_data_snapshot", None)
    if before is None:
        return
    after = _data_snapshot()
    touched = sorted(name for name, mtime in after.items() if before.get(name) != mtime)
    if touched:
        reporter = session.config.pluginmanager.get_plugin("terminalreporter")
        message = "Tests wrote into the real data/ folder, config or repository top: " + ", ".join(touched)
        if reporter is not None:
            reporter.write_line(message, red=True)
            if os.environ.get("GITHUB_ACTIONS"):  # shown on the run's page, whose log needs a sign-in
                reporter.write_line("::error title=Tests wrote outside their folders::" + message[:900])
        session.exitstatus = 1
