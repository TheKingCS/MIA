"""
MIA paints (DEC-0140, core/art_studio.py): a description becomes a picture on the PC's own image engine (ComfyUI),
kept in the person's folder, and can go up as their theme's backdrop. Tested against a stand-in ComfyUI on a local
port: the same HTTP calls, a tiny PNG back.
"""

from core import at_rest
import io
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import core.config_manager as config_module
import core.profile_manager as profile_module
from core import art_studio
from core.app_context import AppContext
from core.art_studio import ArtStore, ComfyEngine, problem, prompt_for
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.profile_manager import ProfileManager

PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00"
       b"\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82")


class FakeComfy(BaseHTTPRequestHandler):
    """Answers like ComfyUI: its stats, its models, a queued prompt, its history, and the image."""
    queued: list = []

    def log_message(self, *args):
        """Quiet."""

    def _json(self, data, code=200):
        """Sends JSON."""
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # noqa: N802
        """Stats, models, history and the image."""
        if self.path == "/system_stats":
            return self._json({"devices": [{"name": "AMD Radeon RX 7900 XTX"}]})
        if self.path == "/object_info/CheckpointLoaderSimple":
            return self._json({"CheckpointLoaderSimple": {"input": {"required": {"ckpt_name": [["v1-5.ckpt", "sdxl_base.safetensors"]]}}}})
        if self.path.startswith("/history/"):
            pid = self.path.rsplit("/", 1)[1]
            return self._json({pid: {"outputs": {"7": {"images": [{"filename": "MIA_0001.png", "subfolder": "", "type": "output"}]}}}})
        if self.path.startswith("/view?"):
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.end_headers()
            self.wfile.write(PNG)
            return None
        return self._json({}, 404)

    def do_POST(self):  # noqa: N802
        """Takes a prompt."""
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeComfy.queued.append(body)
        return self._json({"prompt_id": "p1", "number": 1})


@pytest.fixture
def comfy():
    """A stand-in ComfyUI on a free local port."""
    FakeComfy.queued = []
    server = HTTPServer(("127.0.0.1", 0), FakeComfy)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield ComfyEngine(f"http://127.0.0.1:{server.server_port}", timeout=10)
    server.shutdown()


@pytest.fixture
def ctx(tmp_path, monkeypatch):
    """A context with one person signed in and their art store."""
    monkeypatch.setattr(config_module, "_CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(profile_module, "_DATA_PROFILES_DIR", tmp_path / "profiles")
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.profiles = ProfileManager(context)
    context.profiles.create_profile("Robin")
    context.art = ArtStore(context, data_dir=tmp_path / "me")
    art_studio._JOBS.clear()
    return context


def test_what_mia_will_and_wont_paint():
    assert problem("a fantasy castle village at dusk") is None
    assert "Describe" in problem("  ")
    assert "doesn't paint that" in problem("a naked figure") and "doesn't paint that" in problem("gore everywhere")
    assert "real people" in problem("a photo of Taylor Swift at a castle")
    prompt = prompt_for("a fantasy castle village at dusk.", "backdrop")
    assert "a fantasy castle village at dusk" in prompt["positive"] and (prompt["width"], prompt["height"]) == (1344, 768)
    assert "text" in prompt["negative"] and "people" in prompt["negative"]
    assert prompt_for("a lighthouse", "portal")["height"] > prompt_for("a lighthouse", "portal")["width"]


def test_the_engine_paints_through_comfyuis_own_api(comfy):
    assert comfy.available() == (True, "ComfyUI is running on AMD Radeon RX 7900 XTX.")
    assert comfy.checkpoint() == "sdxl_base.safetensors" and comfy.checkpoint("v1-5.ckpt") == "v1-5.ckpt"
    png = comfy.paint(prompt_for("a castle"), 42, "sdxl_base.safetensors", poll=0.01)
    assert png.startswith(b"\x89PNG")
    graph = FakeComfy.queued[0]["prompt"]
    assert graph["5"]["inputs"]["seed"] == 42 and graph["4"]["inputs"]["width"] == 1344
    assert "castle" in graph["2"]["inputs"]["text"] and graph["1"]["inputs"]["ckpt_name"] == "sdxl_base.safetensors"
    running, line = ComfyEngine("http://127.0.0.1:9").available()
    assert not running and "ART_ENGINE" in line


def test_a_painting_is_kept_and_goes_up_as_the_background(ctx, comfy):
    from core.themes import custom_themes, for_shell, theme_of

    job = art_studio.start(ctx, "a fantasy castle village at dusk", "backdrop", apply=True, engine=comfy, wait=True)
    assert job["status"] == "painted"  # painted on this thread (wait=True); not in the store until settle
    settled = art_studio.settle(ctx)
    assert settled[0]["status"] == "done" and settled[0]["art_id"]
    art_id = settled[0]["art_id"]
    assert ctx.art.path(art_id).read_bytes() == PNG and ctx.art.get(art_id)["description"] == "a fantasy castle village at dusk"
    mine = custom_themes(ctx)
    assert [t["name"] for t in mine] == ["My Stark"] and theme_of(ctx) == mine[0]["id"]
    assert for_shell(ctx)["backdrop"] == {"art": art_id, "strength": 0.6}
    assert art_studio.settle(ctx) == []  # once only
    page = art_studio.status(ctx)
    assert page["items"][0]["image"] == f"/api/art/{art_id}/image" and page["jobs"][0]["status"] == "done"


def test_by_voice_she_paints_uses_takes_down_and_deletes(ctx, comfy, monkeypatch):
    from core.actions import ActionError
    from core.art_studio import _describe_delete
    from core.assistant_art_actions import _action_delete_picture, _action_paint, _action_use_backdrop
    from core.themes import for_shell

    monkeypatch.setattr(art_studio, "engine_for", lambda context: comfy)
    said = _action_paint(ctx, {"description": "a fantasy castle village at dusk"})
    assert "about a minute" in said and "background" in said
    for _ in range(200):
        if art_studio.settle(ctx):
            break
        time.sleep(0.02)
    art_id = ctx.art.all()[0]["id"]
    assert for_shell(ctx)["backdrop"]["art"] == art_id
    assert "down" in _action_use_backdrop(ctx, {"picture": "none"}) and "backdrop" not in for_shell(ctx)
    assert "castle" in _action_use_backdrop(ctx, {"picture": "the castle one", "strength": 0.9})
    assert for_shell(ctx)["backdrop"] == {"art": art_id, "strength": 0.9}
    assert "Want me to paint one" in _action_use_backdrop(ctx, {"picture": "a submarine"})
    assert "doesn't paint that" in _action_paint(ctx, {"description": "something nsfw"})
    assert _describe_delete(ctx, {"id": art_id}).startswith("Delete the picture of a fantasy castle")
    assert "Deleted" in _action_delete_picture(ctx, {"picture": "castle"}) and ctx.art.all() == []
    assert (ctx.art.folder / "removed" / f"{art_id}.png").is_file()  # kept aside for undo
    with pytest.raises(ActionError):
        _describe_delete(ctx, {"id": art_id})


def test_when_the_engine_isnt_running_she_says_how_to_start_it(ctx):
    with pytest.raises(ValueError, match="ART_ENGINE"):
        art_studio.start(ctx, "a castle", engine=ComfyEngine("http://127.0.0.1:9"))


def test_a_theme_file_never_carries_a_picture_from_someone_elses_folder():
    from core.theme_actions import export
    from core.themes import STARK_CHOICES, build_theme

    theme = build_theme({**STARK_CHOICES, "backdrop": "abcdef123456"}, None, "my_x", "X")
    assert theme["backdrop"]["art"] == "abcdef123456" and export(theme)["choices"]["backdrop"] == ""


def test_a_painting_added_or_removed_is_a_line_in_her_history(tmp_path):
    """The person's own history (life events in their folder) says a painting was made and put away, never what the
    painting's words were."""
    import json

    from core.art_studio import ArtStore as Store

    store = Store(None, data_dir=tmp_path)
    staged = tmp_path / "staged.png"
    staged.write_bytes(b"png")
    item = store.add(staged, "my grandmother's porch", "backdrop", {"positive": "a porch", "width": 8, "height": 8}, 1,
                     "comfyui")
    store.remove(item["id"])
    lines = [json.loads(x) for x in at_rest.open_text(tmp_path / "life_events.jsonl").splitlines() if x]
    assert [(e["type"], e["summary"]) for e in lines] == [("art_added", "Added a painting MIA made"),
                                                         ("art_removed", "Removed a painting")]
    assert "porch" not in json.dumps(lines)
