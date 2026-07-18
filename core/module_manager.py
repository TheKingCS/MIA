"""
core.module_manager
====================

Discovers and manages MIA modules.

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
import shutil
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
        # Package (folder) names already successfully loaded — lets
        # discover() be called again (via rescan()) without re-importing
        # and re-flagging every already-known module as a "duplicate".
        # See discover()'s docstring for why this matters.
        self._discovered_package_names: set[str] = set()

    def discover(self) -> None:
        """
        Scan modules/ for module.py files and instantiate any ModuleBase
        subclasses found. Safe to call more than once (rescan() relies on
        this) — a package name already successfully loaded by a previous
        call is skipped rather than re-imported, so re-scanning doesn't
        spuriously log every already-known module as a "duplicate
        module_id". A real duplicate (two different package names
        claiming the same module_id) is still caught and warned about.
        Errors in one module (bad import, missing class) are logged and
        skipped rather than crashing the whole application — a broken
        module should never take down the rest of the system.
        """
        modules_path = Path(modules.__file__).parent

        for finder, name, is_pkg in pkgutil.iter_modules([str(modules_path)]):
            if not is_pkg:
                continue  # skip loose .py files like module_base.py

            if name in self._discovered_package_names:
                continue  # already loaded by a previous discover()/rescan() call

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
            self._discovered_package_names.add(name)
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

    def resolve(self, requested: str) -> ModuleBase | None:
        """
        Like get(), but falls back to a case-insensitive match on
        module_id or display_name if the exact module_id lookup misses.
        Added for docs/ROADMAP.md milestone 5.5's `open_module` assistant
        action — verified against a real Ollama server that the model
        naturally tends to say the human-readable name ("Notes") rather
        than the internal snake_case module_id ("notes"), so a strict
        get() rejected a perfectly clear, valid request.
        """
        exact = self.get(requested)
        if exact is not None:
            return exact

        requested_lower = requested.strip().lower()
        if not requested_lower:
            return None
        for module in self._modules.values():
            if module.module_id.lower() == requested_lower or module.display_name.lower() == requested_lower:
                return module
        return None

    def all(self) -> list[ModuleBase]:
        """Return all discovered modules, sorted by display name for stable menu order."""
        return sorted(self._modules.values(), key=lambda m: m.display_name)

    def enabled_modules(self) -> list[ModuleBase]:
        """Return only the modules that are currently enabled — what the main menu grid should show."""
        return [m for m in self.all() if self.is_enabled(m.module_id)]

    # ------------------------------------------------------------------
    # Enable / disable
    # ------------------------------------------------------------------

    def is_enabled(self, module_id: str) -> bool:
        disabled_ids = self.context.config.get("modules.disabled", [])
        return module_id not in disabled_ids

    def set_enabled(self, module_id: str, enabled: bool) -> bool:
        """
        Enable or disable a module. The Modules screen itself
        (module_id "module_browser") can never be disabled — doing so
        would leave no way back in without hand-editing config.json.
        Returns False if the request was refused for that reason.
        """
        if module_id == "module_browser" and not enabled:
            log.warning("Refusing to disable 'module_browser' — it's the only way to re-enable modules.")
            return False

        disabled_ids = list(self.context.config.get("modules.disabled", []))
        if enabled:
            if module_id in disabled_ids:
                disabled_ids.remove(module_id)
        else:
            if module_id not in disabled_ids:
                disabled_ids.append(module_id)

        self.context.config.set("modules.disabled", disabled_ids)
        self.context.config.save()
        self.context.events.publish("modules.enabled_changed", module_id=module_id, enabled=enabled)
        log.info("Module '%s' %s", module_id, "enabled" if enabled else "disabled")
        return True

    # ------------------------------------------------------------------
    # Rescan (detect new module folders without a full restart)
    # ------------------------------------------------------------------

    def rescan(self) -> int:
        """
        Re-scan modules/ for module folders added since the last
        discover() call, without restarting the app.

        Scope, deliberately: this does NOT reload changed code in an
        already-loaded module. That would mean re-importing a module
        whose class Python has already cached, swapping it under a
        widget that might already be on screen, with no guarantee the
        old and new versions agree on state — a real correctness risk
        for very little benefit at this stage. Detecting brand-new
        module folders is safe (nothing references them yet) and covers
        the actual common case: a developer adds a new module while the
        kiosk app is already running and wants it to show up without a
        full restart.

        Returns the number of newly discovered modules.
        """
        before = set(self._modules.keys())
        self.discover()
        new_ids = set(self._modules.keys()) - before

        if new_ids:
            log.info("Rescan found %d new module(s): %s", len(new_ids), ", ".join(sorted(new_ids)))
        else:
            log.info("Rescan found no new modules.")

        self.context.events.publish("modules.rescanned", new_module_ids=list(new_ids))
        return len(new_ids)

    # ------------------------------------------------------------------
    # Installing new modules (from the "Add Module" UI)
    # ------------------------------------------------------------------

    def install_module_from_folder(self, source_path: Path):
        """
        Validate and install a module from an external folder (e.g. a
        USB drive, or a zip extracted by the GUI layer) into modules/.
        See core/module_validator.py and docs/MODULE_SPEC.md for
        exactly what's checked and why.

        On success: copies the folder into modules/<module_id>/ and
        calls rescan() so it appears immediately, no restart needed.
        On failure: nothing is copied; the returned ValidationResult's
        `errors` explain exactly why.
        """
        from core.module_validator import validate_module_folder

        source_path = Path(source_path)
        existing_ids = set(self._modules.keys())
        result = validate_module_folder(source_path, existing_ids, self.context)

        if not result.passed:
            log.warning("Module install rejected for '%s': %s", source_path, "; ".join(result.errors))
            return result

        modules_dir = Path(modules.__file__).parent
        destination_path = modules_dir / result.module_id

        if destination_path.exists():
            result.passed = False
            result.errors.append(f"A folder named '{result.module_id}' already exists in modules/.")
            return result

        try:
            shutil.copytree(source_path, destination_path)
        except Exception as exc:
            result.passed = False
            result.errors.append(f"Validation passed, but copying the module failed: {exc}")
            return result

        log.info("Installed new module '%s' from %s", result.module_id, source_path)
        self.rescan()
        return result
