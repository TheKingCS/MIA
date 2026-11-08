"""
tests.test_import_properties
==============================

Importing properties into Real Estate (tools/import_properties.py): each is upserted by a generic name key (so an
existing "Oak Rd" is matched by "Oak Dr", never duplicated), role maps to type/status, rent and provenance are
carried, and a shared or unknown loan balance is never fabricated into a per-property figure. Fictional data only —
no real addresses or lenders live in the repo (the real portfolio stays in the private, git-ignored pack).
"""

import json

import pytest

from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.real_estate_manager import RealEstateManager
from tools.import_properties import import_properties

PACK = {"properties": [
    {"id": "home", "name": "12 Oak Hollow Rd, Anyville", "role": "home",
     "loan": {"lender": "First Example Bank", "monthly_usd": 1000.00, "covers": "home + rental"}},
    {"id": "rental", "name": "Maple Rental", "role": "rental", "rent_usd_monthly": 600,
     "loan": "Shared First Example Bank loan"},
    {"id": "selling", "name": "88 Harbor Ln, Anyville", "role": "selling", "buyer": "Sample Buyers LLC",
     "price_usd": 85000, "terms": "Cash, as-is", "mortgage": {"lender": "Second Example Bank", "monthly_usd": 900.00}},
]}


@pytest.fixture
def manager(tmp_path):
    return RealEstateManager(AppContext(config=ConfigManager(), events=EventBus()), data_dir=tmp_path)


@pytest.fixture
def pack_file(tmp_path):
    p = tmp_path / "pack.json"
    p.write_text(json.dumps(PACK), encoding="utf-8")
    return p


def test_properties_import_with_roles_rent_and_provenance(manager, pack_file):
    import_properties(manager, pack=pack_file)
    props = {p.name: p for p in manager.all_properties()}
    assert set(props) == {"12 Oak Hollow Rd, Anyville", "Maple Rental", "88 Harbor Ln, Anyville"}
    assert props["Maple Rental"].property_type == "Rental" and props["Maple Rental"].monthly_rent == 600.0
    assert props["88 Harbor Ln, Anyville"].status == "For Sale"
    assert "First Example Bank" in props["12 Oak Hollow Rd, Anyville"].notes  # the shared loan is a note
    # no fabricated balance for a shared/unknown loan
    assert all(p.mortgage_balance == 0.0 for p in manager.all_properties())


def test_an_existing_property_is_updated_not_duplicated_across_a_street_type(manager, pack_file):
    manager.add_property("12 Oak Hollow Dr", property_type="Primary Residence", current_value=90000.0)
    import_properties(manager, pack=pack_file)
    oaks = [p for p in manager.all_properties() if p.name.lower().startswith("12 oak")]
    assert len(oaks) == 1 and oaks[0].current_value == 90000.0  # kept the existing value, matched Rd to Dr


def test_a_re_run_adds_no_duplicates(manager, pack_file):
    import_properties(manager, pack=pack_file)
    n = len(manager.all_properties())
    second = import_properties(manager, pack=pack_file)
    assert len(manager.all_properties()) == n and second["added"] == []
