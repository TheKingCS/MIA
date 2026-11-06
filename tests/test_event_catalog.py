"""The event catalogue (build plan step 7, core/event_catalog.py): docs/EVENTS.md is the code's own record of what
each file publishes and hears on the event bus, and no listener waits on an event nothing sends."""

from pathlib import Path

from core import event_catalog


def test_the_catalogue_is_current():
    found = event_catalog.catalogue()
    kept = (Path(event_catalog.ROOT) / "docs" / "EVENTS.md").read_text(encoding="utf-8")
    assert kept == event_catalog.render(found), "docs/EVENTS.md is out of date: python -m core.event_catalog"


def test_no_one_listens_for_an_event_nothing_sends():
    assert event_catalog.orphans(event_catalog.catalogue())["unsent"] == []


def test_reading_the_code(tmp_path):
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "a.py").write_text('context.events.publish("thing.done", x=1)\n'
                                            'publish(context, "records.changed", action="y")\n', encoding="utf-8")
    (tmp_path / "core" / "b.py").write_text('self.context.events.subscribe("thing.done", self._on)\n'
                                            'events.subscribe("ghost.event", cb)\n', encoding="utf-8")
    found = event_catalog.catalogue(tmp_path)
    assert found["thing.done"] == {"publishers": ["core/a.py"], "subscribers": ["core/b.py"]}
    assert event_catalog.orphans(found) == {"unheard": ["records.changed"], "unsent": ["ghost.event"]}
