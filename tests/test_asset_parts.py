"""
tests.test_asset_parts
========================

Parts per asset (core/asset_parts.py and its voice tools): the parts an asset uses are stated links to the
household's inventory and materials, listed with what's on hand, out and low first; adding and removing go through
the same actions the asset page uses.
"""

from types import SimpleNamespace

import pytest

from core.actions import ACTION_TYPES, ActionError
from core.asset_parts import choices, parts_for, stock_state
from core.assistant_asset_part_actions import _add, _list, _remove
from core.event_bus import EventBus
from core.inventory_manager import InventoryManager
from core.links import LinkStore
from core.maintenance_manager import MaintenanceManager
from core.material_manager import MaterialManager


@pytest.fixture
def garage(tmp_path):
    """A mower, oil (a material, low), a blade and an air filter (inventory, none left), all in a temporary folder."""
    context = SimpleNamespace(events=EventBus(), config=None, profiles=None)
    context.links = LinkStore(context, data_dir=tmp_path)
    context.maintenance = MaintenanceManager(context, data_dir=tmp_path)
    context.materials = MaterialManager(context, data_dir=tmp_path)
    context.inventory = InventoryManager(context, data_dir=tmp_path)
    mower = context.maintenance.add_asset("Mower", "Power Equipment")
    oil = context.materials.add_material("10W-30 oil", unit="qt", quantity_on_hand=0.5, reorder_threshold=1)
    blade = context.inventory.add_item("Mower blade", quantity=2, location="Shed")
    filt = context.inventory.add_item("Air filter", quantity=0)
    return context, mower, oil, blade, filt


def test_stock_words_for_materials_and_items():
    assert stock_state("material", SimpleNamespace(quantity_on_hand=0.5, reorder_threshold=1, unit="qt")) == (0.5, "qt", "low")
    assert stock_state("material", SimpleNamespace(quantity_on_hand=3, reorder_threshold=1, unit="qt"))[2] == "ok"
    assert stock_state("inventory_item", SimpleNamespace(quantity=0))[2] == "out"


def test_listed_parts_come_out_then_low_then_the_rest(garage):
    context, mower, oil, blade, filt = garage
    for ref in (f"inventory_item:{blade.item_id}", f"material:{oil.material_id}", f"inventory_item:{filt.item_id}"):
        ACTION_TYPES["asset.part_add"].execute(context, {"asset_id": mower.asset_id, "part": ref})
    rows = parts_for(context, mower.asset_id)
    assert [(r["name"], r["state"]) for r in rows] == [("Air filter", "out"), ("10W-30 oil", "low"), ("Mower blade", "ok")]
    assert rows[2]["where"] == "Shed" and rows[1]["unit"] == "qt"
    assert {c["name"] for c in choices(context)} == {"10W-30 oil (Material)", "Mower blade (Inventory)", "Air filter (Inventory)"}


def test_removing_a_part_and_refusing_one_that_isnt_a_part(garage):
    context, mower, oil, blade, filt = garage
    ref = f"inventory_item:{blade.item_id}"
    ACTION_TYPES["asset.part_add"].execute(context, {"asset_id": mower.asset_id, "part": ref})
    ACTION_TYPES["asset.part_remove"].execute(context, {"asset_id": mower.asset_id, "part": ref})
    assert parts_for(context, mower.asset_id) == []
    with pytest.raises(ActionError):
        ACTION_TYPES["asset.part_add"].execute(context, {"asset_id": mower.asset_id, "part": f"asset:{mower.asset_id}"})


def test_by_voice_add_list_and_remove(garage):
    context, mower, oil, blade, filt = garage
    assert _add(context, {"asset": "mower", "part": "10W-30 oil"}) == "Mower uses 10W-30 oil."
    _add(context, {"asset": "the mower", "part": "air filter"})
    assert _list(context, {"asset": "Mower"}) == "Mower uses: Air filter (none left); 10W-30 oil (0.5 qt, low)."
    assert "Took Air filter off" in _remove(context, {"asset": "Mower", "part": "air filter"})
    said = _add(context, {"asset": "Mower", "part": "spark plug"})
    assert "You have: 10W-30 oil, Air filter, Mower blade" in said and said.endswith("first if it isn't there.")
