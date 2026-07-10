"""
core.module_manager
====================

Discovers and manages M.I.A. modules.

Design decision: modules are discovered automatically by scanning the
`modules/` package for subpackages containing a `module.py` that defines
a ModuleBase subclass, rather than requiring manual registration in a
central list. This is the mechanism that makes adding a new module a
"drop a folder in and go" operation, per the project's requirement that
it be "convenient to add and test new modules."

Trade-off, noted deliberately: automatic discovery via importlib is a
little more "magic" than an explicit registry. We accept that because
the alternative — a growing hand-maintained list of imports — is exactly
the kind of friction that discourages adding modules over a multi-year
project. If dynamic discovery ever becomes a real debugging problem,
switching to explicit registration is a contained, backward-compatible
change (ModuleManager's public interface would not need to change).
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

import modules
from core.app_context import AppContext
from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)


class ModuleManager:
    """
    Discovers ModuleBase subclasses under modules/ and holds instantiated
    module objects, keyed by module_id.
    """

    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._modules: dict[str, ModuleBase] = {}

    def discover(self) -> None:
        """
        Scan modules/ for module.py files and instantiate any ModuleBase
        subclasses found. Safe to call once at startup. Errors in one
        module (bad import, missing class) are logged and skipped rather
        than crashing the whole application — a broken module should
        never take down the rest of the system.
        """
        modules_path = Path(modules.__file__).parent

        for finder, name, is_pkg in pkgutil.iter_modules([str(modules_path)]):
            if not is_pkg:
                continue  # skip loose .py files like module_base.py

            module_py_path = modules_path / name / "module.py"
            if not module_py_path.exists():
                continue  # not every subfolder is necessarily a module

            dotted_path = f"modules.{name}.module"
            try:
                mod = importlib.import_module(dotted_path)
            except Exception:
                log.exception("Failed to import module package '%s' — skipping.", name)
                continue

            found_class = self._find_module_class(mod)
            if found_class is None:
                log.warning(
                    "Package 'modules.%s' has module.py but no ModuleBase "
                    "subclass — skipping.", name
                )
                continue

            try:
                instance = found_class(self.context)
            except Exception:
                log.exception("Failed to instantiate module '%s' — skipping.", name)
                continue

            if instance.module_id in self._modules:
                log.warning(
                    "Duplicate module_id '%s' from package '%s' — "
                    "keeping the first one found.", instance.module_id, name
                )
                continue

            self._modules[instance.module_id] = instance
            log.info("Discovered module: %s (%s)", instance.display_name, instance.module_id)

    @staticmethod
    def _find_module_class(mod) -> type[ModuleBase] | None:
        """Find the single ModuleBase subclass defined directly in `mod`."""
        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if issubclass(obj, ModuleBase) and obj is not ModuleBase:
                if obj.__module__ == mod.__name__:
                    return obj
        return None

    def get(self, module_id: str) -> ModuleBase | None:
        return self._modules.get(module_id)

    def all(self) -> list[ModuleBase]:
        """Return all discovered modules, sorted by display name for stable menu order."""
        return sorted(self._modules.values(), key=lambda m: m.display_name)
