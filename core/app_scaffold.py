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

**What it refuses** (`problems`): an id that isn't snake_case, is a name Windows reserves for a device (con, nul,
com1...), is taken or is already in one of the lists; an area that doesn't exist; a file it would overwrite; a name,
tagline, description or icon with a control character, a backslash, three double quotes or `*/` (they'd break the
generated test's docstring or the script's comment; the emitters neutralise them anyway). Nothing is written unless
every check passes, `plan()` shows exactly what would be written without writing it (and parses every Python file it
would change), and `write()` is all or nothing: if a file can't be written, every file it changed is put back and
every file it created removed.

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

ID = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")  # used with fullmatch, so "seed_bank\n" isn't an id
RESERVED = re.compile(r"con|prn|aux|nul|com[0-9]|lpt[0-9]")  # Windows device names: web/con.html can't be a file
UNSAFE = re.compile(r'[\x00-\x1f\x7f-\x9f\u2028\u2029\\]|"""|\*/')  # would break a docstring or a /* */ comment
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
    "Regenerate: python -m core.parity (docs/PARITY.md gains its two todo lines); python -m core.code_atlas "
    "baseline; python -m core.code_atlas; python -m core.system_map.",
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


def _read(root: Path, rel: str) -> str:
    """A file of the checkout as text (a UTF-8 byte-order mark is dropped). ScaffoldError, in a plain sentence, when
    it can't be read."""
    try:
        return (Path(root) / rel).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as err:
        raise ScaffoldError(f"{rel} can't be read in {root} ({err.__class__.__name__}).") from err


def _parse(source: str, rel: str) -> ast.Module:
    """A Python file's source parsed. ScaffoldError when it isn't valid Python."""
    try:
        return ast.parse(source)
    except (SyntaxError, ValueError) as err:
        raise ScaffoldError(f"{rel} isn't valid Python ({err}).") from err


def _area_ids(root: Path) -> list[str]:
    """The ids of the web's areas, read from core/web_areas.py's source (so a lab copy is read, not the running one).
    ScaffoldError when the file can't be read or parsed."""
    tree = _parse(_read(root, "core/web_areas.py"), "core/web_areas.py")
    return [c.args[0].value for c in ast.walk(tree)
            if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "Area" and c.args
            and isinstance(c.args[0], ast.Constant)]


def _listed(root: Path, app_id: str) -> list[str]:
    """Where `app_id` is already listed by hand (WEB_ONLY, LIMITS, OVERVIEW_SKIP, NOT_ON_GLASSES, parity's gaps), so
    a scaffold wouldn't add it twice. A file that can't be read or parsed is skipped here; plan() reports it."""
    found = []
    for rel, names in (("core/web_surfaces.py", ("WEB_ONLY",)), ("core/capabilities.py", ("LIMITS", "OVERVIEW_SKIP")),
                       ("core/glasses.py", ("NOT_ON_GLASSES",))):
        try:
            tree = ast.parse(_read(root, rel))
        except (ScaffoldError, SyntaxError, ValueError):
            continue
        for node in tree.body:
            name = getattr(node.targets[0], "id", "") if isinstance(node, ast.Assign) else ""
            if name not in names:
                continue
            value = node.value.args[0] if isinstance(node.value, ast.Call) and node.value.args else node.value
            try:
                if app_id in ast.literal_eval(value):
                    found.append(f"{name} ({rel})")
            except (ValueError, TypeError, SyntaxError):
                continue
    try:
        gaps = json.loads(_read(root, "work/parity.json")).get("gaps", {})
        if any(str(key).startswith(f"{app_id}:") for key in gaps):
            found.append("the gaps in work/parity.json")
    except (ScaffoldError, ValueError, AttributeError):
        pass
    return found


def problems(spec: AppSpec, root: Path = CODE_ROOT) -> list[str]:
    """Why this app can't be scaffolded in `root`; [] when it can. A root that isn't a checkout is the one reason
    given."""
    root = Path(root)
    if not (root / "core" / "web_areas.py").is_file():
        return [f"{root} isn't a MIA checkout (it has no core/web_areas.py)."]
    out = []
    good_id = bool(ID.fullmatch(spec.id or ""))
    if not good_id:
        out.append(f"The id \"{spec.id}\" isn't snake_case (lowercase letters, digits and single underscores).")
    elif RESERVED.fullmatch(spec.id):
        out.append(f"The id \"{spec.id}\" is a name Windows keeps for a device, so its files couldn't exist there.")
        good_id = False
    if not (spec.name or "").strip():
        out.append("The app needs a name.")
    for label, text in (("name", spec.name), ("tagline", spec.tagline), ("description", spec.description),
                        ("icon", spec.icon)):
        if UNSAFE.search(text or ""):
            out.append(f"The {label} can't have a control character, a backslash, three double quotes or \"*/\".")
    if spec.group not in GROUPS:
        out.append(f"\"{spec.group}\" isn't one of the Apps page's groups: {'; '.join(GROUPS)}.")
    try:
        areas = _area_ids(root)
    except ScaffoldError as err:
        out.append(str(err))
    else:
        if spec.area not in areas:
            out.append(f"\"{spec.area}\" isn't one of the areas: {', '.join(areas)}.")
    if good_id:
        if (root / "apps" / spec.id).exists():
            out.append(f"There is already an app \"{spec.id}\".")
        for path in _new_files(spec, root):
            if (root / path).exists():
                out.append(f"{path} already exists.")
        for where in _listed(root, spec.id):
            out.append(f"\"{spec.id}\" is already in {where}.")
    return out


def _next_order(root: Path) -> int:
    """The next free sidebar place: one past the highest any manifest has (a manifest with a byte-order mark is
    read; one that can't be read is passed over)."""
    orders = []
    for path in (root / "apps").glob("*/manifest.json"):
        try:
            orders.append(int(json.loads(path.read_text(encoding="utf-8-sig")).get("order", 0) or 0))
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


def _one_line(text: str) -> str:
    """Pure logic. Text with every control character (newlines among them) turned into a space."""
    return re.sub(r"[\x00-\x1f\x7f-\x9f\u2028\u2029]", " ", str(text)).strip()


def _in_comment(text: str) -> str:
    """Pure logic. Text made safe inside a JavaScript /* */ comment: one line, and no "*/" to end it early."""
    return _one_line(text).replace("*/", "* /")


def _in_docstring(text: str) -> str:
    """Pure logic. Text made safe inside a Python triple-quoted docstring: one line, backslashes doubled and every
    double quote escaped, so nothing in it can start an escape or end the string."""
    return _one_line(text).replace("\\", "\\\\").replace('"', '\\"')


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
    """Pure logic. The screen's script: starts on the frame and says there's nothing here yet. The name goes only
    into its opening comment, neutralised so it can't end it."""
    return f"""/*
 * {_in_comment(spec.id)}.js — {_in_comment(spec.name)} (scaffolded by MIA Forge, core/app_scaffold.py).
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
    """Pure logic. The app's first test: registered with no problems, and its page is on the shared frame. The name
    goes only into its docstring, escaped so it can't end it or start an escape (the id is checked by problems())."""
    words = spec.id
    return f'''"""
tests.test_app_{spec.id}
{"=" * (15 + len(spec.id))}

{_in_docstring(spec.name)} (scaffolded by MIA Forge, core/app_scaffold.py): the app is registered and its screen is on the
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


def _offset(raw: bytes, lineno: int, col: int) -> int:
    """Pure logic. The byte offset in `raw` of the parser's (line, UTF-8 column) position. Lines are split on "\\n"
    only, as the parser splits them (a form feed or line separator inside a line doesn't start a new one)."""
    start = 0
    for _ in range(lineno - 1):
        start = raw.index(b"\n", start) + 1
    return start + col


def _insert_at(source: str, node: ast.AST, item: str, closer: str) -> str:
    """Pure logic. The source with `item` added as the last element of the tuple, set or dict literal `node` (found
    by parsing). It goes straight after the last element (past any parentheses around it and its trailing comma),
    so a comment after the last element or on a line before the closer stays a comment and the item stays code.
    ScaffoldError when the literal isn't where the parser said."""
    raw = source.encode("utf-8")
    end = _offset(raw, node.end_lineno, node.end_col_offset)
    if not raw[:end].endswith(closer.encode("utf-8")):
        raise ScaffoldError("A list to add the app to doesn't end where the parser said it does.")
    elements = node.values if isinstance(node, ast.Dict) else node.elts
    if not elements:  # empty: the item is all there is (a one-item tuple needs its comma)
        lone = f"{item}," if isinstance(node, ast.Tuple) else item
        return (raw[:end - 1] + lone.encode("utf-8") + raw[end - 1:]).decode("utf-8")
    last = elements[-1]
    at = _offset(raw, last.end_lineno, last.end_col_offset)
    comma, i = False, at
    while i < end - 1:  # between the last element and the closer: space, comments, ")" around it, one comma
        ch = raw[i:i + 1]
        if ch in b" \t\r\n\f\\":
            i += 1
        elif ch == b"#":
            i = raw.find(b"\n", i)
            i = end - 1 if i < 0 else i
        elif ch == b")":
            i += 1
            at = i
        elif ch == b",":
            comma, at = True, i + 1
            break
        else:
            raise ScaffoldError("A list to add the app to has something after its last element the scaffold doesn't "
                                "understand.")
    added = (" " if comma else ", ") + item
    return (raw[:at] + added.encode("utf-8") + raw[at:]).decode("utf-8")


def with_web_only(source: str, app_id: str) -> str:
    """Pure logic. core/web_surfaces.py's source with the app added to `WEB_ONLY`. ScaffoldError when the source isn't
    valid Python or the set isn't where it's expected."""
    for node in ast.walk(_parse(source, "core/web_surfaces.py")):
        if (isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == "WEB_ONLY"
                and isinstance(node.value, ast.Call) and node.value.args and isinstance(node.value.args[0], ast.Set)):
            return _insert_at(source, node.value.args[0], json.dumps(app_id), "}")
    raise ScaffoldError("core/web_surfaces.py has no WEB_ONLY = frozenset({...}) to add the app to.")


def with_area_member(source: str, area: str, app_id: str) -> str:
    """Pure logic. core/web_areas.py's source with the app added to its area's members. ScaffoldError when the
    source isn't valid Python or the area's members aren't where they're expected."""
    for node in ast.walk(_parse(source, "core/web_areas.py")):
        if (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "Area" and len(node.args) >= 5
                and isinstance(node.args[0], ast.Constant) and node.args[0].value == area
                and isinstance(node.args[4], ast.Tuple)):
            return _insert_at(source, node.args[4], json.dumps(app_id), ")")
    raise ScaffoldError(f"core/web_areas.py has no members tuple for the area \"{area}\".")


def with_listed(source: str, name: str, item: str) -> str:
    """Pure logic. A module's source with `item` added to the set, frozenset({...}) or dict assigned to `name` at its
    top level. ScaffoldError when the source isn't valid Python or there's no such literal."""
    for node in _parse(source, f"the file with {name}").body:
        if isinstance(node, ast.Assign) and getattr(node.targets[0], "id", "") == name:
            value = node.value
            if isinstance(value, ast.Call) and value.args and isinstance(value.args[0], ast.Set):
                value = value.args[0]
            if isinstance(value, (ast.Set, ast.Dict)):
                return _insert_at(source, value, item, "}")
    raise ScaffoldError(f"There's no {name} = {{...}} to add the app to.")


def _json(text: str, change, rel: str = "a JSON file") -> str:
    """A JSON file's text after `change(data)`, written as these files are (two spaces, real characters, a final
    newline). ScaffoldError naming `rel` when it isn't JSON or isn't shaped as expected."""
    try:
        data = json.loads(text)
        change(data)
    except ScaffoldError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError) as err:
        raise ScaffoldError(f"{rel} isn't the JSON the scaffold expects ({err.__class__.__name__}: {err}).") from err
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
    "next": [what's left for whoever builds the app]}. ScaffoldError with every reason when it can't be done: a
    problem() found, a file that can't be read or isn't shaped as expected, or a Python file whose new text wouldn't
    parse (each one it would create or change is parsed before anything is written)."""
    root = Path(root)
    found = problems(spec, root)
    if found:
        raise ScaffoldError("\n".join(found))
    read = lambda rel: _read(root, rel)  # noqa: E731
    quoted = json.dumps(spec.id)
    capabilities = with_listed(with_listed(read("core/capabilities.py"), "LIMITS", f'{quoted}: ""'),
                               "OVERVIEW_SKIP", quoted)
    made = {"create": _new_files(spec, root),
            "change": {"core/web_surfaces.py": with_web_only(read("core/web_surfaces.py"), spec.id),
                       "core/web_areas.py": with_area_member(read("core/web_areas.py"), spec.area, spec.id),
                       "core/capabilities.py": capabilities,
                       "core/glasses.py": with_listed(read("core/glasses.py"), "NOT_ON_GLASSES", quoted),
                       "work/parity.json": _json(read("work/parity.json"), _decide(spec), "work/parity.json"),
                       "docs/schema/shell.example.json": _json(read("docs/schema/shell.example.json"),
                                                               _in_shell_example(spec),
                                                               "docs/schema/shell.example.json"),
                       "docs/schema/apps.example.json": _json(read("docs/schema/apps.example.json"),
                                                              _in_apps_example(spec),
                                                              "docs/schema/apps.example.json")},
            "next": list(NEXT_STEPS)}
    for path, content in {**made["create"], **made["change"]}.items():  # every Python file it writes must parse
        if path.endswith(".py"):
            _parse(content, path)
    return made


def write(spec: AppSpec, root: Path = CODE_ROOT) -> dict:
    """Scaffolds the app in `root` (see the module's opening) and returns the plan that was written. Everything is
    worked out before the first file is touched, so a refusal writes nothing; and it's all or nothing on the disk
    too: each file it changes is backed up first, and if any write fails (a locked or read-only file) every changed
    file is put back, every created file and folder removed, and ScaffoldError says which file and why."""
    root = Path(root)
    made = plan(spec, root)
    backups: dict[Path, bytes] = {}
    created: list[Path] = []
    folders: list[Path] = []
    try:
        for path in made["change"]:
            backups[root / path] = (root / path).read_bytes()
        for path, content in {**made["create"], **made["change"]}.items():
            target = root / path
            for folder in reversed(target.parents):  # note each folder it makes, to take back
                if not folder.exists():
                    folder.mkdir()
                    folders.append(folder)
            was = backups.get(target)
            windows = was is not None and b"\r\n" in was  # a changed file keeps its line endings
            if was is None:
                created.append(target)
            target.write_text(content, encoding="utf-8", newline="\r\n" if windows else "\n")
    except OSError as err:
        undone = _undo(backups, created, folders)
        where = getattr(err, "filename", None) or "a file"
        raise ScaffoldError(f"Nothing was scaffolded: {where} couldn't be written ({err.__class__.__name__}), so "
                            f"every file was put back as it was{undone}.") from err
    return made


def _undo(backups: dict[Path, bytes], created: list[Path], folders: list[Path]) -> str:
    """Puts back each changed file's bytes and removes each created file and folder (newest first); "" when that
    all worked, else the end of a sentence naming what couldn't be undone."""
    stuck = []
    for target, was in backups.items():
        try:
            if not target.is_file() or target.read_bytes() != was:
                target.write_bytes(was)
        except OSError:
            stuck.append(str(target))
    for target in created:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            stuck.append(str(target))
    for folder in reversed(folders):
        try:
            folder.rmdir()
        except OSError:
            stuck.append(str(folder))
    return f", except {', '.join(stuck)}" if stuck else ""
