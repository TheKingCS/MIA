"""
tests.test_app_scaffold
=========================

MIA Forge's scaffold (phase M7, core/app_scaffold.py, tools/new_app.py): from one short description it writes a
manifest the Application Registry accepts, a screen on the shared frame, a first test, and the two code edits that
list the app; it refuses a bad id, a taken id, an unknown area and a file it would overwrite, writing nothing; a dry
run writes nothing; and a scaffolded app has no capabilities, permissions or stores of its own. Its hardening: a write
that fails partway is undone, text that would break the generated test or script is refused (and neutralised
anyway), an id with a trailing newline, a Windows device name or one already listed is refused, a comment by a
list's last element can't swallow the new one, a byte-order mark is read and a missing root is a plain refusal.
"""

from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path

import pytest

from core import app_registry, app_scaffold
from core.app_scaffold import AppSpec, ScaffoldError
from core.data_root import CODE_ROOT

SPEC = AppSpec("scaffold_probe", "Scaffold Probe", "home", "Every seed you've saved.", ask='What "seeds" do I have?')


@pytest.fixture
def root(tmp_path):
    """A small checkout: the real area and app lists, two real manifests, and empty web and tests folders."""
    for rel in ("core/web_areas.py", "core/web_surfaces.py", "core/capabilities.py", "core/glasses.py",
                "work/parity.json", "docs/schema/shell.example.json", "docs/schema/apps.example.json",
                "apps/sight/manifest.json", "apps/kitchen/manifest.json"):
        (tmp_path / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(CODE_ROOT / rel, tmp_path / rel)
    (tmp_path / "web").mkdir()
    (tmp_path / "tests").mkdir()
    return tmp_path


def _tree(root: Path) -> dict:
    """Every file under a folder with its bytes, to show nothing changed."""
    return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_a_new_app_gets_a_manifest_a_screen_a_test_and_its_place_in_the_lists(root):
    made = app_scaffold.write(SPEC, root)
    assert sorted(made["create"]) == ["apps/scaffold_probe/manifest.json", "tests/test_app_scaffold_probe.py",
                                      "web/scaffold_probe.html", "web/scaffold_probe.js"]
    reg = app_registry.load(root / "apps")
    assert not reg.load_problems and reg.manifests["scaffold_probe"]["name"] == "Scaffold Probe"
    orders = [m["order"] for m in reg.manifests.values()]
    assert len(set(orders)) == len(orders) and reg.manifests["scaffold_probe"]["order"] == max(orders)
    page = (root / "web" / "scaffold_probe.html").read_text(encoding="utf-8")
    assert 'data-app="scaffold_probe"' in page and 'data-say=""' in page  # no "Say: ..." until it has tools
    assert reg.manifests["scaffold_probe"]["ask"] == "" and reg.manifests["scaffold_probe"]["group"] == app_scaffold.GROUPS[-1]
    assert "<h1>Scaffold Probe</h1>" in page and page.index("shell.js") < page.index("scaffold_probe.js")
    ast.parse((root / "tests" / "test_app_scaffold_probe.py").read_text(encoding="utf-8"))
    assert made["next"] and any("tier" in step for step in made["next"])


def test_the_two_code_lists_gain_the_app_and_still_parse(root):
    before = (root / "core" / "web_areas.py").read_text(encoding="utf-8")
    app_scaffold.write(SPEC, root)
    areas = (root / "core" / "web_areas.py").read_text(encoding="utf-8")
    surfaces = (root / "core" / "web_surfaces.py").read_text(encoding="utf-8")
    home = next(c for c in ast.walk(ast.parse(areas)) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Area"
                and c.args[0].value == "home")
    last = home.args[4].elts[-1]
    assert isinstance(last, ast.Constant) and last.value == "scaffold_probe"
    assert len(areas.splitlines()) == len(before.splitlines())  # one line changed, none added or lost
    web_only = next(n for n in ast.walk(ast.parse(surfaces)) if isinstance(n, ast.Assign)
                    and getattr(n.targets[0], "id", "") == "WEB_ONLY")
    assert "scaffold_probe" in ast.literal_eval(web_only.value.args[0])


def test_the_other_lists_the_decisions_and_the_preview_examples_gain_the_app(root):
    before = {rel: (root / rel).read_bytes() for rel in ("work/parity.json", "docs/schema/apps.example.json")}
    made = app_scaffold.write(SPEC, root)
    assert sorted(made["change"]) == ["core/capabilities.py", "core/glasses.py", "core/web_areas.py",
                                      "core/web_surfaces.py", "docs/schema/apps.example.json",
                                      "docs/schema/shell.example.json", "work/parity.json"]
    scope: dict = {}
    for rel in ("core/capabilities.py", "core/glasses.py"):
        tree = ast.parse((root / rel).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") in ("LIMITS", "OVERVIEW_SKIP",
                                                                                         "NOT_ON_GLASSES"):
                value = node.value.args[0] if isinstance(node.value, ast.Call) else node.value
                scope[node.targets[0].id] = ast.literal_eval(value)
    assert scope["LIMITS"]["scaffold_probe"] == "" and "scaffold_probe" in scope["OVERVIEW_SKIP"]
    assert "scaffold_probe" in scope["NOT_ON_GLASSES"]
    gaps = json.loads((root / "work/parity.json").read_text(encoding="utf-8"))["gaps"]
    assert gaps["scaffold_probe:voice"]["status"] == gaps["scaffold_probe:glasses"]["status"] == "todo"
    shell = json.loads((root / "docs/schema/shell.example.json").read_text(encoding="utf-8"))
    assert shell["apps"][-1]["id"] == "scaffold_probe" and shell["apps"][-1]["page"] == "scaffold_probe.html"
    apps = json.loads((root / "docs/schema/apps.example.json").read_text(encoding="utf-8"))
    group = next(g for g in apps["groups"] if g["name"] == app_scaffold.GROUPS[-1])
    assert group["apps"][-1]["id"] == "scaffold_probe"
    for rel, was in before.items():  # a changed file keeps its line endings, and nothing else in it moved
        now = (root / rel).read_bytes()
        assert (b"\r\n" in now) == (b"\r\n" in was) and len(now.splitlines()) > len(was.splitlines())


def test_a_one_member_area_and_a_trailing_comma_are_handled():
    source = 'AREAS = (Area("kitchen", "Kitchen", "kitchen", "Meals.", ("kitchen",), hue="#fff"),)\n'
    out = app_scaffold.with_area_member(source, "kitchen", "scaffold_probe")
    assert '("kitchen", "scaffold_probe")' in out and ast.parse(out)
    multi = 'X = Area("home", "Home", "home", "Café.",\n         ("a", PAGE,\n          "b"), hue="#fff")\n'
    assert '"b", "scaffold_probe")' in app_scaffold.with_area_member(multi, "home", "scaffold_probe")
    with pytest.raises(ScaffoldError):
        app_scaffold.with_area_member(source, "garage", "scaffold_probe")
    with pytest.raises(ScaffoldError):
        app_scaffold.with_web_only("WEB_ONLY = something_else()\n", "scaffold_probe")


def test_a_bad_id_a_taken_id_an_unknown_area_and_an_existing_file_are_refused_and_nothing_is_written(root):
    (root / "web" / "pantry_plus.html").write_text("mine", encoding="utf-8")
    before = _tree(root)
    for spec, why in ((AppSpec("Scaffold-Probe", "Scaffold Probe", "home"), "snake_case"),
                      (AppSpec("sight", "Look Again", "home"), "already an app"),
                      (AppSpec("scaffold_probe", "Scaffold Probe", "moon"), "isn't one of the areas"),
                      (AppSpec("scaffold_probe", " ", "home"), "needs a name"),
                      (AppSpec("scaffold_probe", "Scaffold Probe", "home", group="Misc"), "isn't one of the Apps page's groups"),
                      (AppSpec("pantry_plus", "Pantry Plus", "home"), "already exists")):
        with pytest.raises(ScaffoldError, match=why):
            app_scaffold.write(spec, root)
        assert _tree(root) == before, spec.id


def test_a_dry_run_shows_everything_and_writes_nothing(root, capsys):
    from tools import new_app

    before = _tree(root)
    assert new_app.main(["scaffold_probe", "Scaffold Probe", "home", "--root", str(root), "--dry-run"]) == 0
    said = capsys.readouterr().out
    assert "Would create apps/scaffold_probe/manifest.json" in said and "Would change core/web_areas.py" in said
    assert _tree(root) == before
    assert new_app.main(["Bad Id", "X", "home", "--root", str(root)]) == 1 and _tree(root) == before
    assert new_app.main(["scaffold_probe", "Scaffold Probe", "home", "--root", str(root)]) == 0
    assert (root / "apps" / "scaffold_probe" / "manifest.json").is_file()


def test_a_scaffolded_app_can_do_nothing_until_its_manifest_says_so():
    m = app_scaffold.manifest(SPEC, 99)
    assert m["capabilities"] == {"tools": [], "actions": [], "tiers": {}, "outside": []}
    assert m["permissions"] == [] and m["components"]["data"] == [] and m["runtime"]["background"] == []
    assert json.loads(json.dumps(m)) == m and all(k in m for k in app_registry.REQUIRED)


def test_text_from_the_description_cant_break_out_of_the_page():
    nasty = AppSpec("scaffold_probe", 'Seeds <script>alert(1)</script>', "home", 'a "quote" & more', ask='"><img src=x>')
    page = app_scaffold.page(nasty)
    assert "<script>alert" not in page and "<img" not in page and "&lt;script&gt;" in page


def test_a_write_that_fails_partway_puts_every_file_back_and_a_retry_works(root, monkeypatch):
    before, real, calls = _tree(root), Path.write_text, []

    def flaky(self, *args, **kwargs):
        """Path.write_text that fails on the sixth file, after four are created and one is changed."""
        calls.append(self)
        if len(calls) == 6:
            raise PermissionError(13, "locked", str(self))
        return real(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky)
    with pytest.raises(ScaffoldError, match="Nothing was scaffolded"):
        app_scaffold.write(SPEC, root)
    assert _tree(root) == before and not (root / "apps" / "scaffold_probe").exists()
    monkeypatch.setattr(Path, "write_text", real)
    assert app_scaffold.write(SPEC, root)["create"]  # nothing left behind to refuse a retry


def test_a_name_or_tagline_that_would_break_the_generated_files_is_refused_and_the_emitters_are_safe_anyway(root):
    for bad in ("Seeds \\New", "\\x", "\\u", 'a """ b', "X */ alert(1); /*", "two\nlines"):
        for spec in (AppSpec("scaffold_probe", bad, "home"), AppSpec("scaffold_probe", "Probe", "home", bad)):
            assert any("control character" in p for p in app_scaffold.problems(spec, root)), bad
        spec = AppSpec("scaffold_probe", bad, "home", bad)
        doc = ast.get_docstring(ast.parse(app_scaffold.first_test(spec)))
        assert doc.split(" (scaffolded")[0].splitlines()[-1] == bad.replace("\n", " ")  # read back as written
        js = app_scaffold.script(spec)
        assert js.count("*/") == 1 and js.index("*/") < js.index("(function")


def test_an_id_with_a_trailing_newline_or_a_windows_device_name_is_refused(root):
    assert any("snake_case" in p for p in app_scaffold.problems(AppSpec("seed_bank\n", "Seed Bank", "home"), root))
    for name in ("con", "prn", "aux", "nul", "com1", "lpt9"):
        assert any("Windows" in p for p in app_scaffold.problems(AppSpec(name, "Device", "home"), root)), name
    assert app_scaffold.problems(AppSpec("console", "Console", "home"), root) == []


def test_a_comment_after_the_last_element_or_before_the_closer_doesnt_swallow_the_new_one():
    def members(out, name):
        """The literal assigned to `name` in `out`, evaluated."""
        node = next(n for n in ast.parse(out).body if getattr(n.targets[0], "id", "") == name)
        return ast.literal_eval(node.value.args[0] if isinstance(node.value, ast.Call) else node.value)

    for source in ('X = {"a", "b"  # the last\n}\n', 'X = {"a",\n     "b",\n     # more later\n}\n',
                   'X = frozenset({"a", ("b")})  # wrapped\n', 'X = {"a", "b",}\n'):
        assert members(app_scaffold.with_listed(source, "X", '"new"'), "X") == {"a", "b", "new"}, source
    dicts = ('LIMITS = {"a": "x",  # note\n}\n', 'LIMITS = {}\n')
    for source in dicts:
        assert members(app_scaffold.with_listed(source, "LIMITS", '"new": ""'), "LIMITS")["new"] == "", source
    for source, want in (('A = Area("home", "H", "h", "d", ("a",  # c\n))\n', ("a", "new")),
                         ('A = Area("home", "H", "h", "d", ())\n', ("new",))):
        out = app_scaffold.with_area_member(source, "home", "new")
        call = next(c for c in ast.walk(ast.parse(out)) if isinstance(c, ast.Call))
        assert ast.literal_eval(call.args[4]) == want, source
    with pytest.raises(ScaffoldError):
        app_scaffold._insert_at('X = {"a"}\n', ast.parse('X = {"a"}\n').body[0].value, '"b"', ")")


def test_a_plan_that_would_write_python_that_doesnt_parse_is_refused(root, monkeypatch):
    monkeypatch.setattr(app_scaffold, "with_web_only", lambda source, app_id: "WEB_ONLY = (\n")
    with pytest.raises(ScaffoldError, match="isn't valid Python"):
        app_scaffold.plan(SPEC, root)


def test_a_byte_order_mark_is_read_and_a_missing_root_is_a_plain_refusal(root, tmp_path, capsys):
    from tools import new_app

    for rel in ("work/parity.json", "docs/schema/apps.example.json", "core/glasses.py"):
        (root / rel).write_bytes(b"\xef\xbb\xbf" + (root / rel).read_bytes())
    assert app_scaffold.write(SPEC, root)["change"]
    missing = tmp_path / "nowhere"
    with pytest.raises(ScaffoldError, match="isn't a MIA checkout"):
        app_scaffold.plan(SPEC, missing)
    assert new_app.main(["scaffold_probe", "Scaffold Probe", "home", "--root", str(missing)]) == 1
    assert "isn't a MIA checkout" in capsys.readouterr().err


def test_an_id_already_in_one_of_the_lists_is_refused(root):
    parity = json.loads((root / "work/parity.json").read_text(encoding="utf-8"))
    parity["gaps"]["scaffold_probe:voice"] = {"status": "none", "why": "left over"}
    (root / "work/parity.json").write_text(json.dumps(parity), encoding="utf-8")
    surfaces = root / "core" / "web_surfaces.py"
    surfaces.write_text(app_scaffold.with_web_only(surfaces.read_text(encoding="utf-8"), "scaffold_probe"),
                        encoding="utf-8")
    found = app_scaffold.problems(SPEC, root)
    assert any("WEB_ONLY" in p for p in found) and any("parity.json" in p for p in found)
    assert any("core.parity" in step for step in app_scaffold.NEXT_STEPS)
