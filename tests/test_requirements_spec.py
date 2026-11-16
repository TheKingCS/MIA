"""
tests.test_requirements_spec
==============================

MIA OS's requirements specification (Prompt 04; `docs/mia_os/MIA_OS_SYSTEM_REQUIREMENTS.md`,
`tools/requirements_matrix.py`): every requirement row is well formed, defined once, with a known priority, tier and
status and an owner prompt; the scenarios name only requirements that exist; the generated traceability matrix is
current; and a malformed or duplicated row is caught.
"""

from tools import requirements_matrix as rm


def test_every_requirement_row_is_well_formed_defined_once_and_owned():
    assert rm.problems() == []
    rows, exercised, _ = rm.read()
    assert len(rows) >= 150 and all(r["owners"] for r in rows)
    assert {"REQ-ARC-002", "REQ-AUT-003", "REQ-REL-001", "REQ-SEC-005"} <= {r["id"] for r in rows}
    assert "S-18" in exercised["REQ-SEC-005"]


def test_the_traceability_matrix_is_current():
    assert rm.MATRIX.read_text(encoding="utf-8") == rm.render(), "run: python -m tools.requirements_matrix"


def test_a_malformed_or_duplicated_row_is_caught(tmp_path):
    for name in rm.SPEC_DOCS:
        (tmp_path / name).write_text("", encoding="utf-8")
    (tmp_path / rm.SPEC_DOCS[0]).write_text(
        "| REQ-ARC-001 | It shall. | Must | MVP | PC | Exists | T | E1 → 05 |\n"
        "| REQ-ARC-001 | Again. | Must | MVP | PC | Exists | T | E1 → 05 |\n"
        "| REQ-ARC-002 | Odd. | Sometimes | Soon | PC | Maybe | T | E1 |\n"
        "| REQ-ARC-003 | Short row. | Must |\n", encoding="utf-8")
    (tmp_path / rm.SCENARIOS).write_text("### S-01 x\n- **Exercises:** REQ-ARC-001, REQ-XYZ-999.\n", encoding="utf-8")
    found = rm.problems(tmp_path)
    assert "REQ-ARC-001 is defined 2 times" in found
    assert any("priority 'Sometimes'" in p for p in found) and any("tier 'Soon'" in p for p in found)
    assert any("status 'Maybe'" in p for p in found) and any("no owner prompt" in p for p in found)
    assert any("3 cells, not 8" in p for p in found) and any("REQ-XYZ-999" in p for p in found)
