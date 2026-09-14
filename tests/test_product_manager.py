"""
tests.test_product_manager
=============================

Unit tests for core.product_manager. Isolates _DATA_DIR/_PRODUCTS_FILE
into a tmp_path scratch area, same monkeypatch pattern as
test_component_manager.py's isolated_paths.
"""

from __future__ import annotations

import pytest

import core.product_manager as product_manager_module
import core.profile_manager as profile_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.product_manager import ProductManager
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    products_file = data_dir / "products.json"
    monkeypatch.setattr(product_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(product_manager_module, "_PRODUCTS_FILE", products_file)
    monkeypatch.setattr(product_manager_module, "_USAGE_LOG_FILE", data_dir / "product_usage_log.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    return data_dir, products_file


def _make_manager() -> ProductManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return ProductManager(context)


def _make_manager_with_profile(name: str) -> tuple[ProductManager, AppContext]:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile(name=name)
    manager = ProductManager(context)
    return manager, context


# ----------------------------------------------------------------------
# Product CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    manager = _make_manager()
    assert manager.all_products() == []


def test_add_product_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    added = manager.add_product(
        name="Engraved Coaster Set", description="Set of 4", job_id="job1",
        quantity_in_stock=10, base_price=25.0, notes="Best seller",
    )

    reloaded = _make_manager()
    products = reloaded.all_products()
    assert len(products) == 1
    assert products[0].product_id == added.product_id
    assert products[0].name == "Engraved Coaster Set"
    assert products[0].description == "Set of 4"
    assert products[0].job_id == "job1"
    assert products[0].quantity_in_stock == 10
    assert products[0].base_price == 25.0
    assert products[0].notes == "Best seller"
    assert products[0].created_at
    assert products[0].updated_at


def test_add_product_clamps_negative_values_to_zero(isolated_paths):
    manager = _make_manager()
    added = manager.add_product(name="Widget", quantity_in_stock=-5, base_price=-10)
    assert added.quantity_in_stock == 0
    assert added.base_price == 0


def test_update_product_changes_fields_and_bumps_updated_at(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Original")
    product.updated_at = "2020-01-01T00:00:00"

    manager.update_product(product.product_id, name="Renamed", base_price=15.0)

    assert product.name == "Renamed"
    assert product.base_price == 15.0
    assert product.updated_at != "2020-01-01T00:00:00"


def test_update_product_clamps_negative_stock_to_zero(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Widget", quantity_in_stock=5)
    manager.update_product(product.product_id, quantity_in_stock=-10)
    assert product.quantity_in_stock == 0


def test_update_product_rejects_created_at(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    with pytest.raises(ValueError):
        manager.update_product(product.product_id, created_at="hacked")


def test_update_product_unknown_id_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.update_product("does-not-exist", name="X")


def test_update_product_unknown_field_raises(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    with pytest.raises(ValueError):
        manager.update_product(product.product_id, bogus_field="X")


def test_delete_product_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Gone soon")

    manager.delete_product(product.product_id)
    assert manager.get_product(product.product_id) is None

    manager.delete_product(product.product_id)  # already gone — must not raise


def test_get_product_returns_none_for_unknown_id(isolated_paths):
    manager = _make_manager()
    assert manager.get_product("does-not-exist") is None


def test_all_products_sorted_alphabetically_by_name(isolated_paths):
    manager = _make_manager()
    manager.add_product(name="Zebra Print Coaster")
    manager.add_product(name="acrylic keychain")
    manager.add_product(name="Maple Cutting Board")

    ordered = [p.name for p in manager.all_products()]
    assert ordered == ["acrylic keychain", "Maple Cutting Board", "Zebra Print Coaster"]


def test_search_matches_name_description_and_notes(isolated_paths):
    manager = _make_manager()
    by_name = manager.add_product(name="Coaster Set")
    by_description = manager.add_product(name="X", description="coaster variant")
    by_notes = manager.add_product(name="Y", notes="popular coaster item")
    manager.add_product(name="Unrelated")

    results = manager.search("coaster")
    result_ids = {p.product_id for p in results}
    assert result_ids == {by_name.product_id, by_description.product_id, by_notes.product_id}


def test_search_blank_query_returns_empty_list(isolated_paths):
    manager = _make_manager()
    manager.add_product(name="Something")
    assert manager.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, products_file = isolated_paths
    data_dir.mkdir(parents=True)
    products_file.write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()
    assert manager.all_products() == []


# ----------------------------------------------------------------------
# adjust_stock
# ----------------------------------------------------------------------

def test_adjust_stock_increases_quantity(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X", quantity_in_stock=5)
    manager.adjust_stock(product.product_id, 3)
    assert product.quantity_in_stock == 8


def test_adjust_stock_decreases_quantity(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X", quantity_in_stock=5)
    manager.adjust_stock(product.product_id, -3)
    assert product.quantity_in_stock == 2


def test_adjust_stock_clamps_at_zero(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X", quantity_in_stock=5)
    manager.adjust_stock(product.product_id, -100)
    assert product.quantity_in_stock == 0


def test_adjust_stock_unknown_product_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.adjust_stock("does-not-exist", 5)


# ----------------------------------------------------------------------
# Listings
# ----------------------------------------------------------------------

def test_add_listing_appends_to_product(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")

    manager.add_listing(product.product_id, platform="Etsy", price=25.0, url="https://etsy.com/listing/1")

    assert len(product.listings) == 1
    assert product.listings[0].platform == "Etsy"
    assert product.listings[0].price == 25.0
    assert product.listings[0].status == "Active"
    assert product.listings[0].url == "https://etsy.com/listing/1"


def test_add_listing_rejects_invalid_status_falls_back_to_active(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    manager.add_listing(product.product_id, platform="Etsy", status="Not A Real Status")
    assert product.listings[0].status == "Active"


def test_add_listing_unknown_product_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.add_listing("does-not-exist", platform="Etsy")


def test_add_listing_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    manager.add_listing(product.product_id, platform="Etsy", price=25.0)

    reloaded = _make_manager()
    reloaded_product = reloaded.get_product(product.product_id)
    assert len(reloaded_product.listings) == 1
    assert reloaded_product.listings[0].platform == "Etsy"


def test_remove_listing_removes_it_and_is_idempotent(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    manager.add_listing(product.product_id, platform="Etsy")
    listing_id = product.listings[0].listing_id

    manager.remove_listing(product.product_id, listing_id)
    assert product.listings == []

    manager.remove_listing(product.product_id, listing_id)  # already gone — must not raise


def test_remove_listing_unknown_product_raises(isolated_paths):
    manager = _make_manager()
    with pytest.raises(ValueError):
        manager.remove_listing("does-not-exist", "some-listing-id")


def test_product_can_have_multiple_listings(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="X")
    manager.add_listing(product.product_id, platform="Etsy", price=25.0)
    manager.add_listing(product.product_id, platform="Web Store", price=22.0)

    assert len(product.listings) == 2
    assert {listing.platform for listing in product.listings} == {"Etsy", "Web Store"}


# ------------------------------------------------------------------
# Multi-user pass (2026-09-14) — added_by_profile_id + the usage log.
# Fifth real application of the "shared object + user relationship"
# pattern. times_sold()/last_sold() (not times_used()/last_used()) —
# "used" doesn't fit a finished-goods product.
# ------------------------------------------------------------------

def test_add_product_with_no_active_profile_leaves_added_by_unset(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set")
    assert product.added_by_profile_id is None


def test_add_product_attributes_to_the_real_active_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()

    product = manager.add_product(name="Coaster Set")

    assert product.added_by_profile_id == active_profile.profile_id


def test_added_by_persists_across_a_fresh_load(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    product = manager.add_product(name="Coaster Set")

    reloaded_context = AppContext(config=ConfigManager(), events=EventBus())
    reloaded_context.profiles = context.profiles
    reloaded = ProductManager(reloaded_context)

    assert reloaded.get_product(product.product_id).added_by_profile_id == active_profile.profile_id


def test_adjust_stock_with_negative_delta_logs_a_real_usage_entry(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    active_profile = context.profiles.get_active_profile()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)

    manager.adjust_stock(product.product_id, -2.0)

    log = manager.usage_log_for_product(product.product_id)
    assert len(log) == 1
    assert log[0].delta == -2.0
    assert log[0].profile_id == active_profile.profile_id


def test_adjust_stock_with_positive_delta_also_logs_an_entry(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set")
    manager.adjust_stock(product.product_id, 5.0)
    assert len(manager.usage_log_for_product(product.product_id)) == 1
    assert manager.usage_log_for_product(product.product_id)[0].delta == 5.0


def test_adjust_stock_with_zero_delta_logs_nothing(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set")
    manager.adjust_stock(product.product_id, 0)
    assert manager.usage_log_for_product(product.product_id) == []


def test_times_sold_counts_only_negative_deltas(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    manager.adjust_stock(product.product_id, -1.0)
    manager.adjust_stock(product.product_id, -1.0)
    manager.adjust_stock(product.product_id, 5.0)  # a production credit, not a sale
    assert manager.times_sold(product.product_id) == 2


def test_times_sold_household_total_includes_every_profile(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    second_profile = context.profiles.create_profile(name="Faith", make_active=False)
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)

    manager.adjust_stock(product.product_id, -1.0)  # Alex (active)
    context.profiles.set_active_profile(second_profile.profile_id)
    manager.adjust_stock(product.product_id, -1.0)  # Faith

    assert manager.times_sold(product.product_id) == 2


def test_times_sold_scoped_to_one_profile_excludes_the_others(isolated_paths):
    manager, context = _make_manager_with_profile("Alex")
    alex = context.profiles.get_active_profile()
    faith = context.profiles.create_profile(name="Faith", make_active=False)
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)

    manager.adjust_stock(product.product_id, -1.0)  # Alex
    context.profiles.set_active_profile(faith.profile_id)
    manager.adjust_stock(product.product_id, -1.0)  # Faith

    assert manager.times_sold(product.product_id, profile_id=alex.profile_id) == 1
    assert manager.times_sold(product.product_id, profile_id=faith.profile_id) == 1


def test_last_sold_returns_the_most_recent_real_sale_event(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    manager.adjust_stock(product.product_id, -1.0)
    latest = manager.adjust_stock(product.product_id, -1.0)

    result = manager.last_sold(product.product_id)
    assert result is not None
    assert result.timestamp == latest.updated_at


def test_last_sold_ignores_production_credits(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    manager.adjust_stock(product.product_id, 10.0)  # a production credit, not a sale
    assert manager.last_sold(product.product_id) is None


def test_last_sold_none_when_never_sold(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set")
    assert manager.last_sold(product.product_id) is None


def test_last_sold_picks_the_truly_last_entry_even_with_identical_timestamps(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    from core.product_manager import ProductUsageEntry

    same_moment = "2026-09-14T12:00:00"
    manager._usage_log.append(ProductUsageEntry(entry_id="e1", product_id=product.product_id, delta=-1.0, profile_id="alex", timestamp=same_moment))
    manager._usage_log.append(ProductUsageEntry(entry_id="e2", product_id=product.product_id, delta=-1.0, profile_id="faith", timestamp=same_moment))

    result = manager.last_sold(product.product_id)
    assert result is not None
    assert result.profile_id == "faith"


def test_usage_log_isolated_per_product(isolated_paths):
    manager = _make_manager()
    product_a = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    product_b = manager.add_product(name="Shelf", quantity_in_stock=5.0)

    manager.adjust_stock(product_a.product_id, -1.0)
    manager.adjust_stock(product_b.product_id, -1.0)
    manager.adjust_stock(product_b.product_id, -1.0)

    assert len(manager.usage_log_for_product(product_a.product_id)) == 1
    assert len(manager.usage_log_for_product(product_b.product_id)) == 2


def test_usage_log_persists_across_a_fresh_load(isolated_paths):
    manager = _make_manager()
    product = manager.add_product(name="Coaster Set", quantity_in_stock=10.0)
    manager.adjust_stock(product.product_id, -1.0)

    reloaded = _make_manager()
    assert len(reloaded.usage_log_for_product(product.product_id)) == 1


def test_load_usage_log_handles_corrupt_json_gracefully(isolated_paths):
    data_dir, _ = isolated_paths
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "product_usage_log.json").write_text("{not valid json", encoding="utf-8")

    manager = _make_manager()  # must not raise
    assert manager.usage_log_for_product("anything") == []
