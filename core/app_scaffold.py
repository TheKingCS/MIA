"""
core.app_scaffold
===================

MIA Forge's scaffold (migration phase M7, DEC-0175; `docs/mia_os/MIA_OS_APPLICATION_REGISTRY.md` section E, steps
4 to 8): everything a new app needs to exist, written from one short description, so a new app starts as a working,
registered, empty screen instead of a list of files to remember.

**What it writes** for an app (`AppSpec`: id, name, area, tagline, description, what to say, icon):
- `apps/<id>/manifest.json`: the Application Registry's record (core/app_registry.py), with no capabilities yet,
  the next free place in the sidebar, and the devices a web screen runs on;
- `web/<id>.html` and `web/<id>.js`: its screen on the shared frame (web/shell.js), showing its tagline and an
  empty panel;
- `tests/test_app_<id>.py`: a test that the app is registered without problems and its page is on the frame;
- the places that list apps by hand, each found by parsing the file, never by guessing at text: `WEB_ONLY`
  (core/web_surfaces.py), its area's members (core/web_areas.py), an empty `LIMITS` line and a place in
  `OVERVIEW_SKIP` (core/capabilities.py), `NOT_ON_GLASSES` (core/glasses.py);
- the two decisions every new app owes (work/parity.json): by voice and on the glasses, both "todo", saying it was
  scaffolded and isn't built;
- the public preview's examples (docs/schema/shell.example.json and apps.example.json), so the demo's sidebar and
  Apps page list it.

These placements are the honest "not yet" ones. Whoever builds the app replaces them: a gist in the overview, a card
on the glasses, tools for its voice (`NEXT_STEPS` says each).

**What it refuses** (`problems`): an id that isn't snake_case or is taken, an area that doesn't exist, a file it
would overwrite. Nothing is written unless every check passes, and `plan()` shows exactly what would be written
without writing it.

**What it doesn't do:** it gives the app no tools, actions, stores or permissions. Each of those is added by the
person or model building the app, and the registry's test fails until the manifest claims it with a tier, so nothing
a scaffold or a model writes can give an app more than its manifest says. It is meant to run in a lab worktree
(core/dev_lab.py); the app reaches the running MIA only by the lab's merge, on Zac's approval.
`python -m tools.new_app` is its command line.
"""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass
from pathlib import Path

from core.data_root import CODE_ROOT

ID = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)*$")
GROUPS = ("Life, goals & self", "Money & business", "Home, homestead & equipment", "Outdoors & field",
          "Knowledge, tools & system")  # the Apps page's groups (each manifest's `group`)
SCAFFOLDED = "scaffolded by MIA Forge (core/app_scaffold.py); not built yet"
NEXT_STEPS = (
    "It has no example of what to say (`ask`) yet: add one to its manifest once it has tools that answer it.",
    "It sits in OVERVIEW_SKIP (core/capabilities.py): move it into AREAS with a GIST when it does something, and say "
    "what it can't do in LIMITS.",
    "It sits in NOT_ON_GLASSES (core/glasses.py): give it a card in PANELS, or decide it never has one, and settle "
    "its two todo lines in work/parity.json.",
    "Give it something to show: assemble the screen's data in core (as core/web_surfaces.py does), serve it from "
    "server/app.py, read it through web/mia.js.",
    "Each tool and action kind it gains goes in its manifest's capabilities with a tier; each store in components.data "
    "with its stores.write permission (tests/test_app_registry.py fails until they do).",
    "Every action gets a tool and a screen control: run `python -m core.parity` and decide each gap in "
    "work/parity.json.",
    "A new store, action family or daily check needs a loop or a reason in work/loop_coverage.json.",
    "Add its row to docs/WEB_PARITY.md if it replaces a Qt screen.",
    "Regenerate: python -m core.code_atlas baseline; python -m core.code_atlas; python -m core.system_map.",
)


class ScaffoldError(ValueError):
    """The app can't be scaffolded as asked; its message says every reason, one a line."""


@dataclass(frozen=True)
class AppSpec:
    """What a new app is, in the words its manifest and screen will carry."""
    id: str
    name: str
    area: str
    tagline: str = ""
    description: str = ""
    ask: str = ""  # kept for the builder; a scaffolded app shows no ask until it has tools that answer it
    icon: str = "▫"
    group: str = GROUPS[-1]


def _area_ids(root: Path) -> list[str]:
    """The ids of the web's areas, read from core/web_areas.py's source (so a lab copy is read, not the running one)."""
    tree = ast.parse((root / "core" / "web_areas.py").read_text(encoding="utf-8"))
    return [c.args[0].value for c in ast.walk(tree)
            if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Area" and c.args
            and isinstance(c.args[0], ast.Constant)]


def problems(spec: AppSpec, root: Path = CODE_ROOT) -> list[str]:
    """Why this app can't be scaffolded in `root`; [] when it can."""
    out = []
    if not ID.match(spec.id or ""):
        out.append(f"The id \"{spec.id}\" isn't snake_case (lowercase letters, digits and single underscores).")
    if not (spec.name or "").strip():
        out.append("The app needs a name.")
    if spec.group not in GROUPS:
        out.append(f"\"{spec.group}\" isn't one of the Apps page's groups: {'; '.join(GROUPS)}.")
    if spec.area not in _area_ids(root):
        out.append(f"\"{spec.area}\" isn't one of the areas: {', '.join(_area_ids(root))}.")
    if ID.match(spec.id or ""):
        if (root / "apps" / spec.id).exists():
            out.append(f"There is already an app \"{spec.id}\".")
        for path in _new_files(spec, root):
            if (root / path).exists():
                out.append(f"{path} already exists.")
    return out


def _next_order(root: Path) -> int:
    """The next free sidebar place: one past the highest any manifest has."""
    orders = []
    for path in (root / "apps").glob("*/manifest.json"):
        try:
            orders.append(int(json.loads(path.read_text(encoding="utf-8")).get("order", 0) or 0))
        except (OSError, ValueError, TypeError):
            continue
    return max(orders, default=0) + 1


def manifest(spec: AppSpec, order: int) -> dict:
    """Pure logic. The app's manifest: what it is and where it runs, with no capabilities yet."""
    return {
        "manifest_version": 1, "id": spec.id, "name": spec.name.strip(), "icon": spec.icon,
        "tagline": spec.tagline.strip(), "description": spec.description.strip() or spec.tagline.strip(),
        "version": "0.1.0", "group": spec.group, "area": spec.area, "order": order, "retired": False,
        "ask": "", "domains": [], "entry": f"web:{spec.id}.html",
        "components": {"interface": {"web": [f"{spec.id}.html"], "qt": [], "glasses": []}, "services": [],
                       "data": [], "agents": [], "workflows": [], "integrations": []},
        "capabilities": {"tools": [], "actions": [], "tiers": {}, "outside": []},
        "uses": [], "permissions": [], "dependencies": [],
        "runtime": {"devices": {"pc": "full", "phone": "full", "glasses": "none", "voice": False}, "background": []},
    }


def _esc(text: str) -> str:
    """Pure logic. Text made safe inside HTML and a double-quoted attribute."""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;"))


def page(spec: AppSpec) -> str:
    """Pure logic. The app's screen on the shared frame: its name, its tagline, an empty panel."""
    name, say = _esc(spec.name.strip()), ""  # no "Say: ..." until it has tools that answer
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="color-scheme" content="dark">
  <title>{name} — MIA</title>
  <link rel="stylesheet" href="tokens.css">
  <link rel="stylesheet" href="themes.css">
  <link rel="stylesheet" href="components.css">
  <link rel="stylesheet" href="shell.css">
  <link rel="stylesheet" href="concept.css">
  <link rel="stylesheet" href="ui.css">
</head>
<body data-app="{spec.id}" data-icon="apps" class="mod-{spec.id.replace('_', '-')}" data-say="{say}">
  <!--
    {name}: scaffolded by MIA Forge (core/app_scaffold.py). Its data is assembled in core and read through
    web/mia.js; every change goes through MIAShell.act. Formatting only here: the engine decides.
  -->
  <div class="layout" id="app" hidden>
    <nav class="side" aria-label="Apps"></nav>
    <main class="layout-main">
      <header class="hero">
        <h1>{name}</h1>
        <p class="tagline" id="sub">{_esc(spec.tagline.strip())}</p>
      </header>
      <div id="panel"></div>
    </main>
  </div>
  <script src="mia.js?v=17"></script>
  <script src="icons.js"></script>
  <script src="sound.js"></script>
  <script src="places-watch.js"></script>
  <script src="shell.js"></script>
  <script src="{spec.id}.js"></script>
</body>
</html>
"""


def script(spec: AppSpec) -> str:
    """Pure logic. The screen's script: starts on the frame and says there's nothing here yet."""
    return f"""/*
 * {spec.id}.js — {spec.name.strip()} (scaffolded by MIA Forge, core/app_scaffold.py).
 * Formatting only: read this screen's data through MIA (web/mia.js) and change things only with MIAShell.act.
 */
(function () {{
  "use strict";
  const {{ el }} = MIAShell;

  function paint() {{
    document.getElementById("panel").replaceChildren(
      el("p", {{ class: "empty" }}, "Nothing here yet."));
  }}

  MIAShell.start(async () => {{ paint(); }}, {{ refreshOnChange: true }});
}})();
"""


def first_test(spec: AppSpec) -> str:
    """Pure logic. The app's first test: registered with no problems, and its page is on the shared frame."""
    words = spec.id
    return f'''"""
tests.test_app_{spec.id}
{"=" * (15 + len(spec.id))}

{spec.name.strip()} (scaffolded by MIA Forge, core/app_scaffold.py): the app is registered and its screen is on the
shared frame. Replace and add to this as the app gains what it does.
"""

from core import app_registry
from core.data_root import CODE_ROOT


def test_the_{words}_app_is_registered_with_no_problems_and_its_page_is_on_the_frame():
    reg = app_registry.load()
    assert "{spec.id}" in reg.manifests and not [p for p in reg.problems() if p.startswith("{spec.id}:")]
    page = (CODE_ROOT / "web" / "{spec.id}.html").read_text(encoding="utf-8")
    assert 'data-app="{spec.id}"' in page and "shell.js" in page and "{spec.id}.js" in page
'''


def _new_files(spec: AppSpec, root: Path) -> dict[str, str]:
    """The files a scaffold creates, by path from the root."""
    return {
        f"apps/{spec.id}/manifest.json": json.dumps(manifest(spec, _next_order(root)), indent=2,
                                                    ensure_ascii=False) + "\n",
        f"web/{spec.id}.html": page(spec),
        f"web/{spec.id}.js": script(spec),
        f"tests/test_app_{spec.id}.py": first_test(spec),
    }


def _insert_at(source: str, node: ast.AST, item: str, closer: str) -> str:
    """The source with `item` added as the last element of the tuple or set literal `node` (found by parsing)."""
    lines = source.splitlines(keepends=True)
    offset = sum(len(line.encode("utf-8")) for line in lines[:node.end_lineno - 1]) + node.end_col_offset
    raw = source.encode("utf-8")
    before, after = raw[:offset].decode("utf-8"), raw[offset:].decode("utf-8")
    assert before.endswith(closer), "the literal doesn't end where the parser said"
    body = before[:-1].rstrip()
    return body + ("" if body.endswith((",", "(", "{")) else ",") + f" {item}" + closer + after


def with_web_only(source: str, app_id: str) -> str:
    """Pure logic. core/web_surfaces.py's source with the app added to `WEB_ONLY`. ScaffoldError when the set isn't
    where it's expected."""
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "WEB_ONLY"
                and isinstance(node.value, ast.Call) and node.value.args and isinstance(node.value.args[0], ast.Set)):
            return _insert_at(source, node.value.args[0], json.dumps(app_id), "}")
    raise ScaffoldError("core/web_surfaces.py has no WEB_ONLY = frozenset({...}) to add the app to.")


def with_area_member(source: str, area: str, app_id: str) -> str:
    """Pure logic. core/web_areas.py's source with the app added to its area's members. ScaffoldError when the
    area's members aren't where they're expected."""
    for node in ast.walk(ast.parse(source)):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Area" and len(node.args) >= 5
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == area
                and isinstance(node.args[4], ast.Tuple)):
            return _insert_at(source, node.args[4], json.dumps(app_id), ")")
    raise ScaffoldError(f"core/web_areas.py has no members tuple for the area \"{area}\".")


def with_listed(source: str, name: str, item: str) -> str:
    """Pure logic. A module's source with `item` added to the set, frozenset({...}) or dict assigned to `name` at its
    top level. ScaffoldError when there's no such literal."""
    for node in ast.parse(source).body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            value = node.value
            if isinstance(value, ast.Call) and value.args and isinstance(value.args[0], ast.Set):
                value = value.args[0]
            if isinstance(value, (ast.Set, ast.Dict)):
                return _insert_at(source, value, item, "}")
    raise ScaffoldError(f"There's no {name} = {{...}} to add the app to.")


def _json(text: str, change) -> str:
    """A JSON file's text after `change(data)`, written as these files are (two spaces, real characters, a final
    newline)."""
    data = json.loads(text)
    change(data)
    return json.dumps(data, indent=2, ensure_ascii=False) + "\n"


def _decide(spec: AppSpec):
    """The change to work/parity.json: the new app's two gaps, decided "todo"."""
    def change(data):
        for way in ("voice", "glasses"):
            data["gaps"][f"{spec.id}:{way}"] = {"status": "todo", "why": SCAFFOLDED}
    return change


def _in_shell_example(spec: AppSpec):
    """The change to the preview's shell example: the app at the end of its list."""
    def change(data):
        data["apps"].append({"id": spec.id, "name": spec.name.strip(), "icon": spec.icon,
                             "tagline": spec.tagline.strip(), "page": f"{spec.id}.html", "group": spec.group,
                             "ask": ""})
    return change


def _in_apps_example(spec: AppSpec):
    """The change to the preview's Apps example: the app at the end of its group."""
    def change(data):
        group = next((g for g in data["groups"] if g.get("name") == spec.group), None)
        if group is None:
            raise ScaffoldError(f"docs/schema/apps.example.json has no group \"{spec.group}\".")
        group["apps"].append({"id": spec.id, "name": spec.name.strip(), "icon": spec.icon,
                              "tagline": spec.tagline.strip(),
                              "description": spec.description.strip() or spec.tagline.strip(),
                              "page": f"{spec.id}.html", "on_web": True, "shown": True, "can_hide": True, "ask": "",
                              "tools": [], "favorite": False, "status": "working", "status_why": []})
    return change


def plan(spec: AppSpec, root: Path = CODE_ROOT) -> dict:
    """Everything a scaffold would write, without writing: {"create": {path: content}, "change": {path: content},
    "next": [what's left for whoever builds the app]}. ScaffoldError with every reason when it can't be done."""
    root = Path(root)
    found = problems(spec, root)
    if found:
        raise ScaffoldError("\n".join(found))
    read = lambda rel: (root / rel).read_text(encoding="utf-8")  # noqa: E731
    quoted = json.dumps(spec.id)
    capabilities = with_listed(with_listed(read("core/capabilities.py"), "LIMITS", f'{quoted}: ""'),
                               "OVERVIEW_SKIP", quoted)
    return {"create": _new_files(spec, root),
            "change": {"core/web_surfaces.py": with_web_only(read("core/web_surfaces.py"), spec.id),
                       "core/web_areas.py": with_area_member(read("core/web_areas.py"), spec.area, spec.id),
                       "core/capabilities.py": capabilities,
                       "core/glasses.py": with_listed(read("core/glasses.py"), "NOT_ON_GLASSES", quoted),
                       "work/parity.json": _json(read("work/parity.json"), _decide(spec)),
                       "docs/schema/shell.example.json": _json(read("docs/schema/shell.example.json"),
                                                               _in_shell_example(spec)),
                       "docs/schema/apps.example.json": _json(read("docs/schema/apps.example.json"),
                                                              _in_apps_example(spec))},
            "next": list(NEXT_STEPS)}


def write(spec: AppSpec, root: Path = CODE_ROOT) -> dict:
    """Scaffolds the app in `root` (see the module's opening) and returns the plan that was written. Everything is
    worked out before the first file is touched, so a refusal writes nothing."""
    root = Path(root)
    made = plan(spec, root)
    for path, content in {**made["create"], **made["change"]}.items():
        target = root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        windows = target.is_file() and b"\r\n" in target.read_bytes()  # a changed file keeps its line endings
        target.write_text(content, encoding="utf-8", newline="\r\n" if windows else "\n")
    return made
