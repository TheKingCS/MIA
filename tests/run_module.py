#!/usr/bin/env python3
"""
tests/run_module.py
=====================

Standalone test harness: boots just enough of M.I.A. to display a
single module's widget, without the splash screen, setup wizard, or
main menu. This is the fast feedback loop for module development —
see docs/ADDING_MODULES.md.

Usage:
    python tests/run_module.py <module_id>
    python tests/run_module.py --list          (show all discovered module ids)

Example:
    python tests/run_module.py notes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow running this script directly (python tests/run_module.py) by
# ensuring the project root is on sys.path, since it's not a package
# entry point like main.py.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtWidgets import QApplication, QMainWindow  # noqa: E402

from core.app_context import AppContext  # noqa: E402
from core.config_manager import ConfigManager  # noqa: E402
from core.event_bus import EventBus  # noqa: E402
from core.module_manager import ModuleManager  # noqa: E402
from gui.styles import DARK_FIELD_THEME  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a single M.I.A. module in isolation.")
    parser.add_argument("module_id", nargs="?", help="The module_id to load, e.g. 'notes'")
    parser.add_argument("--list", action="store_true", help="List all discovered module ids and exit.")
    args = parser.parse_args()

    context = AppContext(config=ConfigManager(), events=EventBus())
    manager = ModuleManager(context)
    manager.discover()

    if args.list or not args.module_id:
        print("Discovered modules:")
        for module in manager.all():
            print(f"  {module.module_id:20s} {module.display_name}")
        if not args.module_id:
            return 0
        return 0

    module = manager.get(args.module_id)
    if module is None:
        print(f"No module with id '{args.module_id}' was discovered.")
        print("Run with --list to see available module ids.")
        return 1

    app = QApplication(sys.argv)
    module.on_load()

    window = QMainWindow()
    window.setWindowTitle(f"M.I.A. Module Test — {module.display_name}")
    window.setStyleSheet(DARK_FIELD_THEME)
    window.resize(700, 500)
    window.setCentralWidget(module.get_widget())
    window.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
