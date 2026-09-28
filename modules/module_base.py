"""
modules.module_base
====================

Defines ModuleBase, the contract every MIA module must implement.

This file lives at the top of `modules/` (not inside any single module
folder) because it's shared infrastructure that every module package
imports from. Keeping it here, alongside its siblings, makes the
"modules/" package self-contained: everything needed to write a new
module is either in this file or in docs/ADDING_MODULES.md.

To add a new module:
    1. Create a folder under modules/, e.g. modules/weather/
    2. Add an __init__.py (can be empty)
    3. Add a module.py containing exactly one class that subclasses
       ModuleBase and sets module_id, display_name, icon, description
    4. Implement get_widget()
    5. That's it — ModuleManager will discover it automatically.

See docs/ADDING_MODULES.md for a full walkthrough.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from core.app_context import AppContext


class ModuleBase(ABC):
    """
    Base class for all MIA modules.

    Class attributes (override these in your subclass):
        module_id     -- unique, stable, snake_case identifier (e.g. "notes")
        display_name  -- human-readable name shown on its button (e.g. "Notes")
        description   -- one-line description shown as a tooltip
        icon          -- a short emoji/glyph placeholder until real icon
                          assets exist in assets/icons/
        version       -- module's own version, independent of app version

    Instance contract:
        get_widget()  -- must return a GUI-toolkit widget representing the
                          module's screen. This is the ONLY point of contact
                          between a module and the GUI layer, which keeps
                          module logic testable without a GUI event loop.
        on_load()     -- optional hook called once when the module is
                          first activated (lazy init, not at discovery time)
        on_unload()   -- optional hook called if the module is torn down
    """

    module_id: str = "base"
    display_name: str = "Base Module"
    description: str = ""
    icon: str = "\U0001F4E6"  # package emoji placeholder
    version: str = "0.1.0"

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._loaded = False

    @abstractmethod
    def get_widget(self) -> Any:
        """
        Return the widget (e.g. a QWidget) representing this module's
        screen. Called lazily the first time the user opens the module,
        not at application startup, so unopened modules cost nothing.
        """
        raise NotImplementedError

    def on_load(self) -> None:
        """Called once, right before get_widget() is first used. Optional override."""
        self._loaded = True

    def on_unload(self) -> None:
        """Called if the module is being torn down. Optional override."""
        self._loaded = False

    def refresh(self) -> None:
        """
        Re-read this screen's data (2026-09-28). Called by the main window
        when records changed somewhere else, e.g. the owner told MIA from
        the phone to add milk to the grocery list while Kitchen was open
        (event "records.changed", core/main_thread.py). Only called once
        get_widget() has built the screen. Default: the module's own
        no-argument `_refresh()`, if it has one; modules with several
        lists override this.
        """
        own = getattr(self, "_refresh", None)
        if callable(own):
            own()

    def focus_record(self, record_id: str) -> None:
        """
        Cross-module deep-linking (2026-09-13) — called right after
        get_widget()/on_load() when something asked to open this module
        already pointed at a specific record (gui/main_window.py's
        open_module(module_id, record_id=...)). Default no-op, same
        "modules degrade gracefully, no ABC requirement" stance every
        other optional hook here takes — most modules have no concept
        of a single focusable record and simply ignore this.
        """
