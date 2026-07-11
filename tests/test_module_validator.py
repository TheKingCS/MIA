"""
tests.test_module_validator
=============================

Unit tests for core.module_validator.validate_module_folder.

Covers every check listed in docs/MODULE_SPEC.md's "What the automated
validator checks" section, in the same order they're documented there,
so the two stay in sync. Each candidate module is written into a
pytest tmp_path folder, never into the real modules/ directory.
"""

from __future__ import annotations

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.module_validator import validate_module_folder

VALID_MODULE_SOURCE = """
from modules.module_base import ModuleBase

class ValidTestModule(ModuleBase):
    module_id = "valid_test_module"
    display_name = "Valid Test Module"
    description = "A valid module for testing."
    icon = "\\u2728"

    def get_widget(self):
        return None
"""


def _context() -> AppContext:
    return AppContext(config=ConfigManager(), events=EventBus())


def _write_module(tmp_path, source: str, with_init: bool = True, folder_name: str = "candidate"):
    folder = tmp_path / folder_name
    folder.mkdir()
    if with_init:
        (folder / "__init__.py").write_text("")
    (folder / "module.py").write_text(source)
    return folder


def test_valid_module_passes(tmp_path):
    folder = _write_module(tmp_path, VALID_MODULE_SOURCE)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is True
    assert result.errors == []
    assert result.module_id == "valid_test_module"
    assert result.display_name == "Valid Test Module"


def test_missing_folder_is_rejected(tmp_path):
    result = validate_module_folder(tmp_path / "does_not_exist", existing_module_ids=set(), context=_context())
    assert result.passed is False
    assert "not a folder" in result.errors[0]


def test_missing_init_py_is_rejected(tmp_path):
    folder = _write_module(tmp_path, VALID_MODULE_SOURCE, with_init=False)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("__init__.py" in e for e in result.errors)


def test_missing_module_py_is_rejected(tmp_path):
    folder = tmp_path / "candidate"
    folder.mkdir()
    (folder / "__init__.py").write_text("")
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("module.py" in e for e in result.errors)


def test_module_py_that_raises_on_import_is_rejected(tmp_path):
    folder = _write_module(tmp_path, "raise RuntimeError('boom')\n")
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert "raised an error while importing" in result.errors[0]


def test_no_module_base_subclass_is_rejected(tmp_path):
    folder = _write_module(tmp_path, "x = 1\n")
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert "No class subclassing ModuleBase" in result.errors[0]


def test_multiple_module_base_subclasses_are_rejected(tmp_path):
    source = VALID_MODULE_SOURCE + """
class AnotherTestModule(ModuleBase):
    module_id = "another_test_module"
    display_name = "Another"

    def get_widget(self):
        return None
"""
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert "exactly one ModuleBase subclass" in result.errors[0]


def test_reserved_module_id_base_is_rejected(tmp_path):
    source = VALID_MODULE_SOURCE.replace('module_id = "valid_test_module"', 'module_id = "base"')
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("reserved" in e for e in result.errors)


def test_invalid_module_id_format_is_rejected(tmp_path):
    source = VALID_MODULE_SOURCE.replace('module_id = "valid_test_module"', 'module_id = "Not-Valid"')
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("lowercase" in e for e in result.errors)


def test_duplicate_module_id_is_rejected(tmp_path):
    folder = _write_module(tmp_path, VALID_MODULE_SOURCE)
    result = validate_module_folder(folder, existing_module_ids={"valid_test_module"}, context=_context())

    assert result.passed is False
    assert any("already used" in e for e in result.errors)


def test_missing_display_name_is_rejected(tmp_path):
    source = VALID_MODULE_SOURCE.replace('display_name = "Valid Test Module"', 'display_name = ""')
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("display_name" in e for e in result.errors)


def test_missing_description_produces_warning_not_error(tmp_path):
    # icon is omitted too, but ModuleBase already supplies a non-empty
    # default icon, so only the description warning should fire here.
    source = """
from modules.module_base import ModuleBase

class BareTestModule(ModuleBase):
    module_id = "bare_test_module"
    display_name = "Bare Test Module"

    def get_widget(self):
        return None
"""
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is True
    assert result.warnings == ["No description set — this will show as a blank tooltip."]


def test_explicit_empty_icon_produces_warning(tmp_path):
    source = VALID_MODULE_SOURCE.replace('icon = "\\u2728"', 'icon = ""')
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is True
    assert any("No icon set" in w for w in result.warnings)


def test_uninstantiable_module_is_rejected(tmp_path):
    source = """
from modules.module_base import ModuleBase

class BrokenInitTestModule(ModuleBase):
    module_id = "broken_init_test_module"
    display_name = "Broken Init Test Module"

    def __init__(self, context, extra_required_arg):
        super().__init__(context)

    def get_widget(self):
        return None
"""
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("Could not instantiate" in e for e in result.errors)


def test_missing_get_widget_is_rejected(tmp_path):
    source = """
from modules.module_base import ModuleBase

class NoWidgetTestModule(ModuleBase):
    module_id = "no_widget_test_module"
    display_name = "No Widget Test Module"
"""
    folder = _write_module(tmp_path, source)
    result = validate_module_folder(folder, existing_module_ids=set(), context=_context())

    assert result.passed is False
    assert any("Could not instantiate" in e for e in result.errors)
