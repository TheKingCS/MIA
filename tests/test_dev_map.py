"""MIA's architecture map (DEC-0078, core/dev_map.py): read from the code with
ast, nothing run; the layering rule checked; docs that describe how things
are checked against the files."""

from types import SimpleNamespace

from core import dev_map


def _repo(tmp_path):
    """A tiny repo to map: a core file that's fine, one that imports gui (and application.py, which may), a module importing another module, and a CLAUDE.md naming a file that's gone."""
    (tmp_path / "core").mkdir()
    (tmp_path / "core" / "fine.py").write_text("from core import logger\n", encoding="utf-8")
    (tmp_path / "core" / "bad.py").write_text("import json\nfrom gui.main_window import MainWindow\n", encoding="utf-8")
    (tmp_path / "core" / "application.py").write_text("from gui.splash_screen import Splash\n", encoding="utf-8")
    for m in ("skills", "missions"):
        (tmp_path / "modules" / m).mkdir(parents=True)
    (tmp_path / "modules" / "module_base.py").write_text("class ModuleBase: pass\n", encoding="utf-8")
    (tmp_path / "modules" / "skills" / "module.py").write_text(
        "from modules.module_base import ModuleBase\nfrom modules.missions.module import x\nfrom modules.skills.parts import y\n",
        encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("See `core/fine.py` and `core/gone.py`.", encoding="utf-8")
    return tmp_path


def test_the_layering_rule_is_read_from_the_code(tmp_path):
    root = _repo(tmp_path)
    breaks = {(b["file"], b["imports"]) for b in dev_map.layering(root)}
    assert breaks == {("core/bad.py", "gui.main_window"), ("modules/skills/module.py", "modules.missions.module")}
    # boot (application.py) crosses it by design; the shared base and a module's own parts don't count


def test_docs_naming_files_that_arent_there(tmp_path):
    assert dev_map.doc_mismatches(_repo(tmp_path)) == [{"doc": "CLAUDE.md", "names": "core/gone.py"}]


def test_growth_by_area_and_week():
    T = SimpleNamespace
    tasks = {"a": T(status="done", files=["core/x.py", "tests/t.py"], updated="2026-11-04", created=""),
             "b": T(status="done", files=["core/y.py"], updated="2026-11-03", created=""),
             "c": T(status="open", files=["web/z.js"], updated="2026-11-04", created="")}
    g = dev_map.growth(tasks)
    assert dict(g["areas"]) == {"core": 2, "tests": 1} and g["weeks"] == [("2026-W45", 2)]


def test_the_real_repo_holds_to_its_rule_but_one_known_break():
    breaks = {(b["file"], b["imports"]) for b in dev_map.layering()}
    assert breaks <= {("modules/skills/module.py", "modules.missions.module")}  # T-0042: fixing it shrinks this
    assert dev_map.doc_mismatches() == []
