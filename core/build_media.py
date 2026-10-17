"""
core.build_media
==================

Photos and videos of a workshop build (DEC-0030 phase B): the before and
after of a furniture flip, the build in progress, the finished piece for
the portfolio. They live with the household's workshop data, in
`<jobs folder>/workshop_media/<job_id>/`; a name starting "before-" or
"after-" is shown as Before or After. Every name is checked to stay
inside its build's folder. Deleting one can't be undone.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from core.my_files import clean_name, kind_of, size_text

MAX_BYTES = 200 * 1024 * 1024
TAGS = ("before", "during", "after")


def _job(context, job_id: str):
    jobs = getattr(context, "jobs", None)
    job = jobs.get_job(job_id) if jobs is not None else None
    if job is None:
        raise ValueError("That build isn't there anymore.")
    return job


def folder(context, job_id: str) -> Path:
    return Path(context.jobs.data_dir) / "workshop_media" / job_id


def tag_of(name: str) -> str:
    """Pure logic. "after-table.jpg" → "after"."""
    first = name.split("-", 1)[0].lower()
    return first if first in TAGS and "-" in name else ""


def media(context, job_id: str) -> list[dict]:
    """Everything on the build, oldest first (so the story reads in order)."""
    here = folder(context, job_id)
    items = []
    if here.is_dir():
        for p in here.iterdir():
            if p.is_file() and not p.is_symlink() and not p.name.startswith("."):
                stat = p.stat()
                items.append({"name": p.name, "kind": kind_of(p.name), "tag": tag_of(p.name),
                              "size_text": size_text(stat.st_size),
                              "added": datetime.fromtimestamp(stat.st_mtime).date().isoformat(), "_t": stat.st_mtime})
    items.sort(key=lambda i: (TAGS.index(i["tag"]) if i["tag"] else 1, i.pop("_t")))
    return items


def path_of(context, job_id: str, name: str) -> Path:
    _job(context, job_id)
    base = folder(context, job_id).resolve()
    real = (base / str(name or "")).resolve()
    if base not in real.parents:
        raise ValueError("That isn't part of this build.")
    return real


def save(context, job_id: str, filename: str, data: bytes, tag: str = "") -> str:
    """An upload, saved with the build; a name already used gets " (2)"."""
    _job(context, job_id)
    if not data:
        raise ValueError("Nothing was received.")
    if len(data) > MAX_BYTES:
        raise ValueError("That file is over 200 MB.")
    here = folder(context, job_id)
    here.mkdir(parents=True, exist_ok=True)
    name = clean_name(Path(str(filename)).name)
    if tag in TAGS and not tag_of(name):
        name = f"{tag}-{name}"
    target, n = here / name, 2
    while target.exists():
        target = here / f"{Path(name).stem} ({n}){Path(name).suffix}"
        n += 1
    partial = here / f".{target.name}.part"
    partial.write_bytes(data)
    partial.replace(target)
    from core.live import bump

    bump()
    return target.name


def delete(context, job_id: str, name: str) -> str:
    path = path_of(context, job_id, name)
    if not path.is_file():
        raise ValueError("That isn't there anymore.")
    path.unlink()
    from core.live import bump

    bump()
    return path.name
