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

This module-level code (not a fixture) runs when pytest loads this
conftest.py, which always happens before any test module is imported —
early enough to win the race against core.module_manager and friends
calling get_logger() at their own module level.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import core.logger as logger_module
import core.profile_manager as profile_manager_module

_TEST_LOG_DIR = Path(tempfile.mkdtemp(prefix="mia_test_logs_"))
logger_module._LOG_DIR = _TEST_LOG_DIR
logger_module._LOG_FILE = _TEST_LOG_DIR / "mia.log"

_TEST_PROFILES_DIR = Path(tempfile.mkdtemp(prefix="mia_test_profiles_"))
profile_manager_module._DATA_PROFILES_DIR = _TEST_PROFILES_DIR
