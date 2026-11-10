"""
tests.test_history_and_links
==============================

The interconnection work from the first self-audit (DEC-0108, 2026-11-07):
`life_events.on_change` puts a store's changes in her history, and the new
link kinds let the rest of a life's records be linked, with the refs the
history carries.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from pathlib import Path

from core import at_rest, life_events, links


@dataclass
class Thing:
    """A stand-in record."""
    thing_id: str
    name: str


class Store:
    """A stand-in store with a decorated add, update, delete and a failing method."""

    def __init__(self, data_dir: Path) -> None:
        """Keeps its folder, where its history goes."""
        self.data_dir = data_dir

    @life_events.on_change("thing_added", "a thing", "thing")
    def add(self, name: str) -> Thing:
        """Makes a thing."""
        return Thing("t1", name)

    @life_events.on_change("thing_removed", "a thing", "thing")
    def delete(self, thing_id: str) -> None:
        """Removes nothing, returns nothing."""

    @life_events.on_change("secret_added", "a secret", named=False)
    def keep(self, text: str) -> dict:
        """Keeps a secret, returning it as a dict."""
        return {"id": "s1", "text": text}

    @life_events.on_change("thing_added", "a thing", "thing")
    def broken(self) -> None:
        """Fails."""
        raise ValueError("no")


def test_a_decorated_store_method_records_its_change(tmp_path):
    """Each call that succeeds is one event, named from what it returned and referenced by its id; a delete takes
    the id it was given; named=False keeps the words out; a failing call records nothing and still raises."""
    import pytest

    store = Store(tmp_path)
    assert store.add("Mower").name == "Mower"
    store.delete("t1")
    store.keep("the code is 1234")
    with pytest.raises(ValueError):
        store.broken()
    lines = at_rest.open_text(tmp_path / life_events.FILE_NAME).splitlines()  # each line sealed on disk (DEC-0126)
    assert len(lines) == 3, lines
    import json

    first, second, third = (json.loads(line) for line in lines)
    assert first["type"] == "thing_added" and first["summary"] == "Added a thing: Mower" and first["refs"] == ["thing:t1"]
    assert second["summary"] == "Removed a thing" and second["refs"] == ["thing:t1"]
    assert third["summary"] == "Added a secret" and "1234" not in json.dumps(third)
    assert Store.add.__doc__ == "Makes a thing."  # the method keeps its own name and docstring


def test_every_link_kind_points_at_a_real_store_list_and_fields():
    """Each kind's store is one MIA builds, its lister is a method or list the store has, and its records have the
    id and name fields named: a dataclass's fields, or for a store that keeps dicts, the keys it writes."""
    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

    classes = dict(PERSONAL_STORES + HOUSEHOLD_STORES)
    app = Path(__file__).resolve().parent.parent / "core" / "application.py"
    built = app.read_text(encoding="utf-8")
    for kind in links.KINDS.values():
        cls = classes.get(kind.store)
        if cls is None:
            assert f"self.context.{kind.store} =" in built, kind.kind  # a device-level store the app builds
            continue
        source = inspect.getsource(inspect.getmodule(cls))
        assert f"def {kind.lister}(" in source or f"self.{kind.lister}:" in source, kind.kind
        for attr in (kind.id_attr, kind.name_attr):
            assert f"    {attr}: str" in source or f'"{attr}": ' in source, (kind.kind, attr)


def test_the_history_refs_match_the_link_kinds():
    """A store's decorated changes reference its records by the same kind a link uses, so history and links meet."""
    import re

    root = Path(__file__).resolve().parent.parent / "core"
    used = set()
    for path in root.glob("*.py"):
        used |= set(re.findall(r'@life_events\.on_change\("\w+", "[^"]+", "(\w+)"', path.read_text(encoding="utf-8")))
    # refs without a link kind yet are fine only where the record isn't something to link (a lesson, a listing...)
    unlinked = used - set(links.KINDS)
    assert unlinked <= {"memory", "rhythm", "operating_line", "note", "track", "course", "lesson", "subject",
                        "email_draft", "alarm", "shop_expense", "shop_revenue", "order", "quote", "market",
                        "camera", "insurance_quote", "business_use", "inbox_item", "boss", "intent", "mission",
                        "person", "pet", "recipe"}, unlinked
