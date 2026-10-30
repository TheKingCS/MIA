"""The Intelligence Benchmark (docs/INTELLIGENCE_BENCHMARK.md): the
question list and the document stay in step, and the routing audit runs."""

import re
from pathlib import Path

from tests.intelligence_bench import CATEGORIES, QUESTIONS

_DOC = Path(__file__).resolve().parent.parent / "docs" / "INTELLIGENCE_BENCHMARK.md"


def test_every_question_has_an_assessment_row():
    rows = set(re.findall(r"^\| ([A-G]\d+) \|", _DOC.read_text(encoding="utf-8"), re.M))
    assert rows == set(QUESTIONS)
    assert {qid[0] for qid in QUESTIONS} == set(CATEGORIES) and len(QUESTIONS) == 112


def test_the_routing_audit_covers_every_question():
    from tools.bench_audit import audit

    rows = audit()
    assert [r["id"] for r in rows] == list(QUESTIONS)
    assert all(r["route"] in ("code", "tools", "model only") for r in rows)
