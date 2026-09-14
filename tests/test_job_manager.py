"""
tests.test_job_manager
=========================

Unit tests for core.job_manager. Isolates _DATA_DIR/_JOBS_FILE into a
tmp_path scratch area, same monkeypatch pattern as
test_component_manager.py's isolated_paths. consume_material()/
total_cost()/produce_product() also need core.material_manager/
core.product_manager isolated in the same tmp_path, same
"combined-manager fixture" pattern as test_mission_manager.py's
Trip/Waypoint/Expedition isolation.
"""

from __future__ import annotations

import pytest

import core.job_manager as job_manager_module
import core.material_manager as material_manager_module
import core.product_manager as product_manager_module
import core.profile_manager as profile_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.job_manager import Job, JobManager, MaterialConsumptionEntry, job_labor_cost, job_material_cost, job_total_cost
from core.material_manager import Material, MaterialManager
from core.product_manager import ProductManager
from core.profile_manager import ProfileManager


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(job_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(job_manager_module, "_JOBS_FILE", data_dir / "jobs.json")
    monkeypatch.setattr(material_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(material_manager_module, "_MATERIALS_FILE", data_dir / "materials.json")
    monkeypatch.setattr(material_manager_module, "_USAGE_LOG_FILE", data_dir / "material_usage_log.json")
    monkeypatch.setattr(product_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(product_manager_module, "_PRODUCTS_FILE", data_dir / "products.json")
    monkeypatch.setattr(product_manager_module, "_USAGE_LOG_FILE", data_dir / "product_usage_log.json")
    monkeypatch.setattr(profile_manager_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")


def _make_context() -> AppContext:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.materials = MaterialManager(context)
    context.products = ProductManager(context)
    context.jobs = JobManager(context)
    return context


# ----------------------------------------------------------------------
# job_material_cost / job_labor_cost / job_total_cost (pure)
# ----------------------------------------------------------------------

def test_job_material_cost_sums_consumption_entries():
    job = Job(
        job_id="j1", name="Coasters",
        material_consumption=[
            MaterialConsumptionEntry(material_id="ply", quantity_used=2),
            MaterialConsumptionEntry(material_id="stain", quantity_used=1),
        ],
    )
    materials_by_id = {
        "ply": Material(material_id="ply", name="Plywood", unit_cost=10.0),
        "stain": Material(material_id="stain", name="Stain", unit_cost=5.0),
    }
    assert job_material_cost(job, materials_by_id) == 25.0


def test_job_material_cost_skips_deleted_material():
    job = Job(job_id="j1", name="X", material_consumption=[MaterialConsumptionEntry(material_id="gone", quantity_used=5)])
    assert job_material_cost(job, {}) == 0.0


def test_job_labor_cost():
    job = Job(job_id="j1", name="X", labor_hours=3)
    assert job_labor_cost(job, labor_rate_per_hour=20.0) == 60.0


def test_job_total_cost_combines_material_and_labor():
    job = Job(
        job_id="j1", name="X", labor_hours=2,
        material_consumption=[MaterialConsumptionEntry(material_id="ply", quantity_used=1)],
    )
    materials_by_id = {"ply": Material(material_id="ply", name="Plywood", unit_cost=10.0)}
    assert job_total_cost(job, materials_by_id, labor_rate_per_hour=15.0) == 40.0


# ----------------------------------------------------------------------
# JobManager CRUD
# ----------------------------------------------------------------------

def test_starts_empty_when_no_file_exists(isolated_paths):
    context = _make_context()
    assert context.jobs.all_jobs() == []


def test_add_job_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    added = context.jobs.add_job(name="Engrave 20 coasters", description="Etsy order #123", labor_hours=2.5)

    reloaded = JobManager(context)
    jobs = reloaded.all_jobs()
    assert len(jobs) == 1
    assert jobs[0].job_id == added.job_id
    assert jobs[0].name == "Engrave 20 coasters"
    assert jobs[0].description == "Etsy order #123"
    assert jobs[0].status == "Planned"
    assert jobs[0].labor_hours == 2.5
    assert jobs[0].created_at
    assert jobs[0].updated_at


def test_add_job_rejects_invalid_status_falls_back_to_planned(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="X", status="Not A Real Status")
    assert job.status == "Planned"


def test_add_job_clamps_negative_labor_hours(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="X", labor_hours=-5)
    assert job.labor_hours == 0


def test_update_job_changes_fields_and_bumps_updated_at(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="Original")
    job.updated_at = "2020-01-01T00:00:00"

    context.jobs.update_job(job.job_id, name="Renamed", status="In Progress")

    assert job.name == "Renamed"
    assert job.status == "In Progress"
    assert job.updated_at != "2020-01-01T00:00:00"


def test_update_job_rejects_created_at(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="X")
    with pytest.raises(ValueError):
        context.jobs.update_job(job.job_id, created_at="hacked")


def test_update_job_unknown_id_raises(isolated_paths):
    context = _make_context()
    with pytest.raises(ValueError):
        context.jobs.update_job("does-not-exist", name="X")


def test_update_job_unknown_field_raises(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="X")
    with pytest.raises(ValueError):
        context.jobs.update_job(job.job_id, bogus_field="X")


def test_delete_job_removes_it_and_is_idempotent(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="Gone soon")

    context.jobs.delete_job(job.job_id)
    assert context.jobs.get_job(job.job_id) is None

    context.jobs.delete_job(job.job_id)  # already gone — must not raise


def test_get_job_returns_none_for_unknown_id(isolated_paths):
    context = _make_context()
    assert context.jobs.get_job("does-not-exist") is None


def test_all_jobs_sorted_most_recently_created_first(isolated_paths):
    context = _make_context()
    first = context.jobs.add_job(name="First")
    first.created_at = "2026-01-01T00:00:00"
    second = context.jobs.add_job(name="Second")
    second.created_at = "2026-06-01T00:00:00"

    ordered = [j.name for j in context.jobs.all_jobs()]
    assert ordered == ["Second", "First"]


def test_search_matches_name_description_and_notes(isolated_paths):
    context = _make_context()
    by_name = context.jobs.add_job(name="Coaster batch")
    by_description = context.jobs.add_job(name="X", description="coaster order")
    by_notes = context.jobs.add_job(name="Y", notes="for the coaster fair")
    context.jobs.add_job(name="Unrelated")

    results = context.jobs.search("coaster")
    result_ids = {j.job_id for j in results}
    assert result_ids == {by_name.job_id, by_description.job_id, by_notes.job_id}


def test_search_blank_query_returns_empty_list(isolated_paths):
    context = _make_context()
    context.jobs.add_job(name="Something")
    assert context.jobs.search("   ") == []


def test_load_handles_corrupt_json_gracefully(isolated_paths, tmp_path):
    (tmp_path / "data").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "jobs.json").write_text("{not valid json", encoding="utf-8")

    context = _make_context()
    assert context.jobs.all_jobs() == []


# ----------------------------------------------------------------------
# consume_material — the real cross-manager integration
# ----------------------------------------------------------------------

def test_consume_material_records_entry_and_deducts_stock(isolated_paths):
    context = _make_context()
    material = context.materials.add_material(name="Plywood", unit_cost=10.0, quantity_on_hand=20)
    job = context.jobs.add_job(name="Coasters")

    context.jobs.consume_material(job.job_id, material.material_id, 5)

    assert len(job.material_consumption) == 1
    assert job.material_consumption[0].material_id == material.material_id
    assert job.material_consumption[0].quantity_used == 5
    assert context.materials.get_material(material.material_id).quantity_on_hand == 15


def test_consume_material_logs_real_attributed_usage(isolated_paths):
    """Multi-user pass (2026-09-14) — consume_material() now routes
    through MaterialManager.adjust_quantity() rather than
    update_material() directly, so a real Job consuming stock is also
    real, attributed usage, not just a manual quantity tweak."""
    context = _make_context()
    context.profiles = ProfileManager(context)
    active_profile = context.profiles.create_profile(name="Alex")
    material = context.materials.add_material(name="Plywood", unit_cost=10.0, quantity_on_hand=20)
    job = context.jobs.add_job(name="Coasters")

    context.jobs.consume_material(job.job_id, material.material_id, 5)

    usage = context.materials.usage_log_for_material(material.material_id)
    assert len(usage) == 1
    assert usage[0].delta == -5
    assert usage[0].profile_id == active_profile.profile_id
    assert context.materials.times_used(material.material_id) == 1


def test_consume_material_clamps_stock_at_zero_rather_than_going_negative(isolated_paths):
    context = _make_context()
    material = context.materials.add_material(name="Plywood", quantity_on_hand=3)
    job = context.jobs.add_job(name="Coasters")

    context.jobs.consume_material(job.job_id, material.material_id, 10)

    assert context.materials.get_material(material.material_id).quantity_on_hand == 0
    assert job.material_consumption[0].quantity_used == 10  # the job's own record is honest about what was used


def test_consume_material_unknown_job_raises(isolated_paths):
    context = _make_context()
    material = context.materials.add_material(name="Plywood", quantity_on_hand=10)
    with pytest.raises(ValueError):
        context.jobs.consume_material("does-not-exist", material.material_id, 1)


def test_consume_material_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    material = context.materials.add_material(name="Plywood", quantity_on_hand=20)
    job = context.jobs.add_job(name="Coasters")
    context.jobs.consume_material(job.job_id, material.material_id, 5)

    reloaded_jobs = JobManager(context)
    reloaded_job = reloaded_jobs.get_job(job.job_id)
    assert len(reloaded_job.material_consumption) == 1
    assert reloaded_job.material_consumption[0].quantity_used == 5


def test_total_cost_combines_live_material_price_and_labor_rate(isolated_paths):
    context = _make_context()
    context.config.set("workshop.labor_rate_per_hour", 20.0)
    material = context.materials.add_material(name="Plywood", unit_cost=10.0, quantity_on_hand=20)
    job = context.jobs.add_job(name="Coasters", labor_hours=2)
    context.jobs.consume_material(job.job_id, material.material_id, 3)

    # material: 3 * 10.0 = 30, labor: 2 * 20.0 = 40, total = 70
    assert context.jobs.total_cost(job.job_id) == 70.0


def test_total_cost_defaults_labor_rate_to_zero_when_unset(isolated_paths):
    context = _make_context()
    job = context.jobs.add_job(name="X", labor_hours=5)
    assert context.jobs.total_cost(job.job_id) == 0.0


def test_total_cost_unknown_job_returns_none(isolated_paths):
    context = _make_context()
    assert context.jobs.total_cost("does-not-exist") is None


# ----------------------------------------------------------------------
# produce_product — the other half of the consume/produce loop
# ----------------------------------------------------------------------

def test_produce_product_records_entry_and_credits_stock(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters", quantity_in_stock=5)
    job = context.jobs.add_job(name="Batch run")

    context.jobs.produce_product(job.job_id, product.product_id, 20)

    assert len(job.products_produced) == 1
    assert job.products_produced[0].product_id == product.product_id
    assert job.products_produced[0].quantity_produced == 20
    assert context.products.get_product(product.product_id).quantity_in_stock == 25


def test_produce_product_logs_real_attributed_usage(isolated_paths):
    """Multi-user pass (2026-09-14) — unlike consume_material(),
    produce_product() needed NO rewiring at all: it already called
    ProductManager.adjust_stock(), which now logs attributed usage
    internally. This proves that's genuinely true, not assumed."""
    context = _make_context()
    context.profiles = ProfileManager(context)
    active_profile = context.profiles.create_profile(name="Alex")
    product = context.products.add_product(name="Coasters", quantity_in_stock=5)
    job = context.jobs.add_job(name="Batch run")

    context.jobs.produce_product(job.job_id, product.product_id, 20)

    usage = context.products.usage_log_for_product(product.product_id)
    assert len(usage) == 1
    assert usage[0].delta == 20
    assert usage[0].profile_id == active_profile.profile_id


def test_produce_product_unknown_job_raises(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters")
    with pytest.raises(ValueError):
        context.jobs.produce_product("does-not-exist", product.product_id, 5)


def test_produce_product_persists_across_a_fresh_load(isolated_paths):
    context = _make_context()
    product = context.products.add_product(name="Coasters", quantity_in_stock=0)
    job = context.jobs.add_job(name="Batch run")
    context.jobs.produce_product(job.job_id, product.product_id, 10)

    reloaded_jobs = JobManager(context)
    reloaded_job = reloaded_jobs.get_job(job.job_id)
    assert len(reloaded_job.products_produced) == 1
    assert reloaded_job.products_produced[0].quantity_produced == 10


def test_a_job_can_both_consume_materials_and_produce_products(isolated_paths):
    """The full loop: a job consumes raw material and produces a
    finished product from it, both real inventory movements."""
    context = _make_context()
    material = context.materials.add_material(name="Plywood", unit_cost=10.0, quantity_on_hand=20)
    product = context.products.add_product(name="Coasters", quantity_in_stock=0)
    job = context.jobs.add_job(name="Batch run")

    context.jobs.consume_material(job.job_id, material.material_id, 5)
    context.jobs.produce_product(job.job_id, product.product_id, 20)

    assert context.materials.get_material(material.material_id).quantity_on_hand == 15
    assert context.products.get_product(product.product_id).quantity_in_stock == 20
