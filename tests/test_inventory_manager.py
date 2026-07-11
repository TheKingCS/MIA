"""
tests.test_inventory_manager
===============================

Unit tests for core.inventory_manager. Isolates _DATA_DIR/_ITEMS_FILE
into a tmp_path scratch area (same monkeypatch pattern as
test_calendar_manager.py's isolated_paths).
"""

from __future__ import annotations

import pytest

import core.inventory_manager as inventory_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    items_file = data_dir / "inventory_items.json"
    monkeypatch.setattr(inventory_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(inventory_manager_module, "_ITEMS_FILE", items_file)
    return data_dir, items_file


def _make_manager() -> InventoryManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return InventoryManager(context)


def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_items() == []


def test_add_item_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_item(name="Duct Tape", quantity=3, category="Tools", location="Shelf A")

    reloaded = _make_manager()
    items = reloaded.all_items()
    assert len(items) == 1
    assert items[0].item_id == added.item_id
    assert items[0].name == "Duct Tape"
    assert items[0].quantity == 3
    assert items[0].category == "Tools"
    assert items[0].location == "Shelf A"
    assert items[0].updated_at


def test_add_item_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    added = manager.add_item(name="Widget", quantity=-5)
    assert added.quantity == 0


def test_update_item_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Original", quantity=1)
    item.updated_at = "2020-01-01T00:00:00"

    manager.update_item(item.item_id, name="Renamed", quantity=5)

    assert item.name == "Renamed"
    assert item.quantity == 5
    assert item.updated_at != "2020-01-01T00:00:00"


def test_update_item_clamps_negative_quantity_to_zero(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=5)
    manager.update_item(item.item_id, quantity=-10)
    assert item.quantity == 0


def test_update_item_rejects_updated_at(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="X")
    with pytest.raises(ValueError):
        manager.update_item(item.item_id, updated_at="hacked")


def test_update_item_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_item("does-not-exist", name="X")


def test_update_item_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="X")
    with pytest.raises(ValueError):
        manager.update_item(item.item_id, bogus_field="X")


def test_adjust_quantity_increments_and_decrements(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=5)

    manager.adjust_quantity(item.item_id, 1)
    assert item.quantity == 6

    manager.adjust_quantity(item.item_id, -2)
    assert item.quantity == 4


def test_adjust_quantity_clamps_at_zero(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Widget", quantity=1)
    manager.adjust_quantity(item.item_id, -5)
    assert item.quantity == 0


def test_adjust_quantity_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.adjust_quantity("does-not-exist", 1)


def test_delete_item_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    item = manager.add_item(name="Gone soon")

    manager.delete_item(item.item_id)
    assert manager.get_item(item.item_id) is None

    manager.delete_item(item.item_id)  # already gone — must not raise


def test_get_item_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_item("does-not-exist") is None


def test_all_items_sorted_alphabetically_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_item(name="Zebra Clamp")
    manager.add_item(name="apple crate")
    manager.add_item(name="Multimeter")

    ordered = [i.name for i in manager.all_items()]
    assert ordered == ["apple crate", "Multimeter", "Zebra Clamp"]


def test_search_matches_name_category_location_and_notes(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_item(name="Soldering Iron")
    by_category = manager.add_item(name="Widget", category="Electronics")
    by_location = manager.add_item(name="Gadget", location="Electronics Bin")
    by_notes = manager.add_item(name="Thing", notes="Used for electronics repair.")
    manager.add_item(name="Unrelated", category="Kitchen")

    results = manager.search("electronics")
    result_ids = {i.item_id for i in results}
    assert result_ids == {by_category.item_id, by_location.item_id, by_notes.item_id}

    name_results = manager.search("SOLDERING")
    assert [i.item_id for i in name_results] == [by_name.item_id]


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_item(name="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, items_file = isolated_paths
    data_dir.mkdir(parents=True)
    items_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_items() == []
