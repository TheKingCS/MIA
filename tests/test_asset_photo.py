"""
tests.test_asset_photo
========================

An asset's photo (Q-0014, 2026-11-07): kept in the household's own folder under a name of its own, shown on its page
and Garage card through a link that changes with the file, and never served from outside that folder.
"""

from types import SimpleNamespace

import pytest

from core.event_bus import EventBus
from core.maintenance_manager import MaintenanceAsset, MaintenanceManager
from core.web_equipment import asset_photo_url


@pytest.fixture
def garage(tmp_path):
    """A maintenance store in a temporary household folder with one truck."""
    context = SimpleNamespace(events=EventBus(), config=None)
    store = MaintenanceManager(context, data_dir=tmp_path)
    context.maintenance = store
    truck = store.add_asset("F-150", "Vehicle")
    return context, store, truck, tmp_path


def test_a_photo_is_copied_in_and_linked_with_a_name_that_changes(garage, tmp_path):
    context, store, truck, folder = garage
    picture = tmp_path / "IMG_0042.JPG"
    picture.write_bytes(b"jpeg bytes")
    assert asset_photo_url(context, truck) == ""
    name = store.set_asset_photo(truck.asset_id, picture)
    assert (folder / "asset_photos" / name).read_bytes() == b"jpeg bytes" and name.endswith(".jpg")
    assert store.asset_photo_path(truck.asset_id).name == name
    assert asset_photo_url(context, truck) == f"/api/garage/asset/{truck.asset_id}/photo?v={name}"
    assert MaintenanceManager(context, data_dir=folder).get_asset(truck.asset_id).photo == name  # saved


def test_only_pictures_and_only_known_assets(garage, tmp_path):
    context, store, truck, _ = garage
    doc = tmp_path / "manual.pdf"
    doc.write_bytes(b"%PDF")
    with pytest.raises(ValueError):
        store.set_asset_photo(truck.asset_id, doc)
    with pytest.raises(ValueError):
        store.set_asset_photo("nope", doc)


def test_a_stored_name_cant_reach_outside_the_photo_folder(garage):
    context, store, truck, folder = garage
    (folder / "secret.jpg").write_bytes(b"x")
    store.update_asset(truck.asset_id, photo="../secret.jpg")
    assert store.asset_photo_path(truck.asset_id) is None


def test_older_files_load_without_a_photo():
    assert MaintenanceAsset.from_dict({"asset_id": "a", "name": "Mower"}).photo == ""
