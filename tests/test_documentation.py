"""Documentation for everything MIA is made of (DEC-0104, core/code_atlas.py): every file says what it is; new code
arrives documented; nothing already documented slips back; docs/ATLAS.md is current."""

from pathlib import Path

from core import code_atlas


def test_nothing_new_arrives_undocumented_and_nothing_slips_back():
    found = code_atlas.census()
    wrong = code_atlas.problems(found, code_atlas.baseline())
    assert not wrong, ("Document these (what it is, what it does, how): see core/code_atlas.py.\n" + "\n".join(wrong[:20]))


def test_the_atlas_is_current():
    kept = Path(code_atlas.ATLAS).read_text(encoding="utf-8")
    assert kept == code_atlas.render(), "docs/ATLAS.md is out of date: python -m core.code_atlas"


def test_how_a_file_is_read(tmp_path):
    (tmp_path / "a.py").write_text('"""\ncore.a\n======\n\nThe thing it does.\n\nMore."""\n\n'
                                   'def f():\n    """F."""\n\n\ndef g():\n    def inner():\n        pass\n\n\n'
                                   'class C:\n    def m(self):\n        """M."""\n\n    def n(self):\n        pass\n')
    info = code_atlas.py_file(tmp_path / "a.py")
    assert info["about"] == "The thing it does." and info["doc"]
    assert info["defs"] == 5 and info["undocumented"] == ["g", "C", "C.n"]  # a nested function is g's to explain
    (tmp_path / "b.js").write_text("/*\n * b.js — the B page (claude).\n * More.\n */\n(function () {})();\n",
                                   encoding="utf-8")
    assert code_atlas.other_file(tmp_path / "b.js")["about"] == "b.js — the B page (claude). More."
    kept = {"old.py": 2}
    found = {"old.py": {"doc": True, "undocumented": ["x", "y", "z"]}, "new.py": {"doc": True, "undocumented": ["q"]},
             "bare.py": {"doc": False, "undocumented": []}}
    said = code_atlas.problems(found, kept)
    assert len(said) == 3 and "allowed 2" in said[0] and "allowed 0" in said[1] and "no description" in said[2]
