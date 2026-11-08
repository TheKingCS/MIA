"""
tests.test_property_photo
===========================

A property's photo (Q-0014, 2026-11-07): kept in the household's own folder, linked with a name that changes with
the file, and never served from outside that folder.
"""

from types import SimpleNamespace

import pytest

from core.event_bus import EventBus
from core.real_estate_manager import Property, RealEstateManager
from core.web_screens import property_photo_url


@pytest.fixture
def estate(tmp_path):
    """A real estate store in a temporary household folder with one rental."""
    context = SimpleNamespace(events=EventBus(), config=None)
    store = RealEstateManager(context, data_dir=tmp_path)
    return store, store.add_property("Maple Street Rental"), tmp_path


def test_a_photo_is_copied_in_and_linked(estate, tmp_path):
    store, rental, folder = estate
    picture = tmp_path / "front.png"
    picture.write_bytes(b"png bytes")
    assert property_photo_url(store, rental) == ""
    name = store.set_property_photo(rental.property_id, picture)
    assert (folder / "property_photos" / name).read_bytes() == b"png bytes"
    assert property_photo_url(store, rental) == f"/api/real-estate/property/{rental.property_id}/photo?v={name}"
    assert RealEstateManager(SimpleNamespace(events=EventBus(), config=None), data_dir=folder).get_property(rental.property_id).photo == name


def test_only_pictures_and_never_outside_the_folder(estate, tmp_path):
    store, rental, folder = estate
    deed = tmp_path / "deed.pdf"
    deed.write_bytes(b"%PDF")
    with pytest.raises(ValueError):
        store.set_property_photo(rental.property_id, deed)
    (folder / "secret.jpg").write_bytes(b"x")
    store.update_property(rental.property_id, photo="../secret.jpg")
    assert store.property_photo_path(rental.property_id) is None


def test_older_files_load_without_a_photo():
    assert Property.from_dict({"property_id": "p", "name": "Lot"}).photo == ""
