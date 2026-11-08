"""Trail Maps on the web: the screen by state, adding a PDF (and refusing what isn't one), and taking one out so Undo
can bring it back whole."""

from types import SimpleNamespace

import pytest

import core.trail_map_library as tml
import core.web_trails as wt
from core.actions import ACTION_TYPES, ActionError
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.app_context import AppContext


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """A context whose trail map catalog and folder live in a temporary folder."""
    monkeypatch.setattr(tml, "_DATA_DIR", tmp_path / "data")
    monkeypatch.setattr(tml, "_TRAIL_MAPS_FILE", tmp_path / "data" / "trail_maps.json")
    monkeypatch.setattr(tml, "_DEFAULT_ROOT", tmp_path / "trail_maps")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.trail_maps = tml.TrailMapLibrary(context)
    return context


def test_a_sent_pdf_is_kept_by_state_and_anything_else_is_refused(ctx):
    wt.add_upload(ctx, "Mammoth Cave", "Kentucky", b"%PDF-1.7 map")
    wt.add_upload(ctx, "Fall Creek Falls", "Tennessee", b"%PDF-1.4 map", "the gorge")
    page = wt.screen(ctx)
    assert page["count"] == 2 and [g["state"] for g in page["states"]] == ["Kentucky", "Tennessee"]
    assert page["states"][1]["maps"][0]["notes"] == "the gorge" and page["states"][0]["maps"][0]["here"]
    with pytest.raises(ValueError, match="isn't a PDF"):
        wt.add_upload(ctx, "Fake", "Ohio", b"<html>not found</html>")
    with pytest.raises(ValueError, match="Which park"):
        wt.add_upload(ctx, "", "Ohio", b"%PDF")
    with pytest.raises(ValueError, match="https"):
        wt.add_link(ctx, "Park", "Ohio", "file:///etc/passwd")


def test_taking_one_out_sets_its_pdf_aside_so_it_can_come_back(ctx):
    wt.add_upload(ctx, "Mammoth Cave", "Kentucky", b"%PDF-1.7 map")
    [t] = ctx.trail_maps.all_trail_maps()
    ACTION_TYPES["trail_map.delete"].describe(ctx, {"trail_map_id": t.trail_map_id})
    ACTION_TYPES["trail_map.delete"].execute(ctx, {"trail_map_id": t.trail_map_id})
    assert wt.screen(ctx)["count"] == 0
    assert (ctx.trail_maps.root_path / "removed" / t.filename).exists()
    ctx.trail_maps._trail_maps.append(t)  # what Undo does: the catalog as it was
    assert ctx.trail_maps.file_path(t.trail_map_id) is not None
    with pytest.raises(ActionError):
        ACTION_TYPES["trail_map.delete"].describe(ctx, {"trail_map_id": "nope"})
    assert wt.screen(SimpleNamespace()) == {"available": False}
