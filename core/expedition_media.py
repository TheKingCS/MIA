"""
core.expedition_media
=======================

Photos, videos and files on an expedition (Zac, 2026-10-16: "after
planning a trip you should be able to attach pictures and videos and
files to it"). Uploads from the phone or the web go to the expedition's
own folder, `<trip photo root>/expeditions/<expedition_id>/`; photos a
trip already has (added on the desktop, `Trip.photo_filenames`) show in
the same gallery, marked with their trip. Each item is named by a `ref`
("e/<name>" or "t/<trip_id>/<name>") and every ref is checked to stay
inside its folder. Files are copies MIA keeps; deleting one can't be
undone.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.my_files import clean_name, kind_of, size_text

MAX_BYTES = 200 * 1024 * 1024


def _changed() -> None:
    from core.live import bump

    bump()


def _trips(context):
    trips = getattr(context, "trips", None)
    if trips is None:
        raise ValueError("Expeditions aren't set up on this MIA.")
    return trips


def _expedition(context, expedition_id: str):
    expeditions = getattr(context, "expeditions", None)
    found = expeditions.get_expedition(expedition_id) if expeditions is not None else None
    if found is None:
        raise ValueError("That expedition isn't there anymore.")
    return found


def folder(context, expedition_id: str) -> Path:
    return _trips(context).photo_root / "expeditions" / expedition_id


def _inside(path: Path, root: Path) -> Path:
    real, base = path.resolve(), root.resolve()
    if base not in real.parents:
        raise ValueError("That isn't part of this expedition.")
    return real


def media(context, expedition_id: str) -> list[dict]:
    """Everything on the expedition, newest first."""
    out = []
    here = folder(context, expedition_id)
    if here.is_dir():
        for p in here.iterdir():
            if p.is_file() and not p.is_symlink() and not p.name.startswith("."):
                out.append((p, f"e/{p.name}", ""))
    trips = _trips(context)
    for trip in trips.trips_for_expedition(expedition_id):
        for name in trip.photo_filenames:
            p = trips.photo_path(trip.trip_id, name)
            if p.is_file():
                out.append((p, f"t/{trip.trip_id}/{name}", trip.name))
    items = []
    for p, ref, trip_name in out:
        stat = p.stat()
        items.append({"ref": ref, "name": p.name, "kind": kind_of(p.name), "size_text": size_text(stat.st_size),
                      "added": datetime.fromtimestamp(stat.st_mtime).date().isoformat(), "trip": trip_name,
                      "_t": stat.st_mtime})
    items.sort(key=lambda i: i.pop("_t"), reverse=True)
    return items


def path_of(context, expedition_id: str, ref: str) -> Path:
    _expedition(context, expedition_id)
    ref = str(ref or "")
    if ref.startswith("e/"):
        return _inside(folder(context, expedition_id) / ref[2:], folder(context, expedition_id))
    if ref.startswith("t/"):
        bits = ref.split("/", 2)
        if len(bits) == 3:
            trips = _trips(context)
            trip = trips.get_trip(bits[1])
            if trip is not None and trip.expedition_id == expedition_id and bits[2] in trip.photo_filenames:
                return _inside(trips.photo_path(trip.trip_id, bits[2]), trips.photo_root / trip.trip_id)
    raise ValueError("That isn't part of this expedition.")


def save(context, expedition_id: str, filename: str, data: bytes) -> str:
    """An upload, saved under the expedition; a name already used gets " (2)"."""
    _expedition(context, expedition_id)
    if not data:
        raise ValueError("Nothing was received.")
    if len(data) > MAX_BYTES:
        raise ValueError("That file is over 200 MB.")
    here = folder(context, expedition_id)
    here.mkdir(parents=True, exist_ok=True)
    name = clean_name(Path(str(filename)).name)
    target, n = here / name, 2
    while target.exists():
        target = here / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    partial = here / f".{target.name}.part"
    partial.write_bytes(data)
    partial.replace(target)
    _changed()
    return target.name


def delete(context, expedition_id: str, ref: str) -> str:
    path = path_of(context, expedition_id, ref)
    if not path.is_file():
        raise ValueError("That isn't there anymore.")
    if ref.startswith("t/"):
        _, trip_id, name = ref.split("/", 2)
        _trips(context).remove_photo(trip_id, name)  # the trip forgets it and its copy goes
    else:
        path.unlink()
    _changed()
    return path.name
