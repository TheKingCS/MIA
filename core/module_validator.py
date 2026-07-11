"""
core.module_validator
=======================

Validates a candidate module folder against the compatibility contract
in docs/MODULE_SPEC.md, before it's installed into modules/.

This actually imports and instantiates the candidate module.py to
verify it — that's the only reliable way to confirm a real ModuleBase
subclass with a working get_widget() implementation exists; static
text inspection alone can't catch a broken __init__ or an unimplemented
abstract method. This is not a new security boundary: any module that
ends up in modules/ already runs with the full privileges of the rest
of the app once installed — core/module_manager.py's discover() does
exactly the same import-and-instantiate for every real module at every
boot. Only validate/install module code you trust, the same judgment
you'd apply to running any other local Python script — see
docs/MODULE_SPEC.md's security note.
"""

from __future__ import annotations

import importlib.util
import inspect
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger
from modules.module_base import ModuleBase

log = get_logger(__name__)

_MODULE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
_RESERVED_MODULE_IDS = {"base"}


@dataclass
class ValidationResult:
    passed: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    module_id: Optional[str] = None
    display_name: Optional[str] = None


def validate_module_folder(
    folder_path: Path, existing_module_ids: set[str], context: AppContext
) -> ValidationResult:
    """
    Run every check from docs/MODULE_SPEC.md's "What the automated
    validator checks" section, in the same order they're documented
    there, so the two stay in sync.
    """
    folder_path = Path(folder_path)

    if not folder_path.is_dir():
        return ValidationResult(passed=False, errors=[f"'{folder_path}' is not a folder."])

    init_path = folder_path / "__init__.py"
    module_py_path = folder_path / "module.py"

    errors: list[str] = []
    if not init_path.exists():
        errors.append("Missing required file: __init__.py (can be empty).")
    if not module_py_path.exists():
        errors.append("Missing required file: module.py")
    if errors:
        return ValidationResult(passed=False, errors=errors)

    # Import under a throwaway name so it can't collide with anything
    # already loaded under the real modules.* package.
    temp_name = f"_mia_candidate_{uuid.uuid4().hex[:8]}"
    try:
        spec = importlib.util.spec_from_file_location(temp_name, module_py_path)
        if spec is None or spec.loader is None:
            return ValidationResult(passed=False, errors=["Could not load module.py — invalid Python file."])
        candidate_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(candidate_module)
    except Exception as exc:
        return ValidationResult(passed=False, errors=[f"module.py raised an error while importing: {exc}"])

    found_classes = [
        obj
        for _, obj in inspect.getmembers(candidate_module, inspect.isclass)
        if issubclass(obj, ModuleBase) and obj is not ModuleBase and obj.__module__ == candidate_module.__name__
    ]

    if not found_classes:
        return ValidationResult(passed=False, errors=["No class subclassing ModuleBase was found in module.py."])
    if len(found_classes) > 1:
        names = ", ".join(c.__name__ for c in found_classes)
        return ValidationResult(
            passed=False,
            errors=[f"module.py must contain exactly one ModuleBase subclass, found {len(found_classes)}: {names}"],
        )

    module_class = found_classes[0]
    module_id = getattr(module_class, "module_id", None)
    display_name = getattr(module_class, "display_name", None)
    warnings: list[str] = []

    if not module_id or not isinstance(module_id, str):
        errors.append("module_id must be a non-empty string.")
    elif module_id in _RESERVED_MODULE_IDS:
        errors.append(f"module_id '{module_id}' is reserved — did you forget to set module_id on your class?")
    elif not _MODULE_ID_PATTERN.match(module_id):
        errors.append(
            f"module_id '{module_id}' must be lowercase, start with a letter, "
            "and contain only letters, numbers, and underscores."
        )
    elif module_id in existing_module_ids:
        errors.append(f"module_id '{module_id}' is already used by another installed module.")

    if not display_name or not isinstance(display_name, str):
        errors.append("display_name must be a non-empty string.")

    if not getattr(module_class, "description", ""):
        warnings.append("No description set — this will show as a blank tooltip.")
    if not getattr(module_class, "icon", ""):
        warnings.append("No icon set — a default will be used.")

    if errors:
        return ValidationResult(passed=False, errors=errors, warnings=warnings, module_id=module_id, display_name=display_name)

    # Actually instantiate it — the same thing ModuleManager.discover()
    # does for every real module — to catch a broken __init__ or an
    # unimplemented abstract method before anything is installed.
    try:
        instance = module_class(context)
    except TypeError as exc:
        return ValidationResult(
            passed=False,
            errors=[f"Could not instantiate the module class (often means get_widget isn't implemented): {exc}"],
            module_id=module_id,
            display_name=display_name,
        )
    except Exception as exc:
        return ValidationResult(
            passed=False,
            errors=[f"Module raised an error during __init__: {exc}"],
            module_id=module_id,
            display_name=display_name,
        )

    if not callable(getattr(instance, "get_widget", None)):
        return ValidationResult(
            passed=False,
            errors=["get_widget must be defined and callable."],
            module_id=module_id,
            display_name=display_name,
        )

    return ValidationResult(passed=True, errors=[], warnings=warnings, module_id=module_id, display_name=display_name)
