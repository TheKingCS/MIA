"""
tests.test_dependency_audit
=============================

Known vulnerabilities in MIA's packages (docs/SECURITY.md step 5): OSV's answer
is read into one finding per package and advisory with the fixing version
(tools/dependency_audit.py); the weekly check is due after a week; findings are
said once, plainly, and none means nothing is said (core/dependency_audit.py).
"""

from datetime import datetime, timedelta

from core import dependency_audit as da
from tools import dependency_audit as tool

ADVISORY = {"id": "GHSA-xxxx", "summary": "Sandbox escape\nmore detail", "affected": [
    {"package": {"name": "Jinja2", "ecosystem": "PyPI"}, "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.10.1"}]}]}]}


def test_osv_s_answer_becomes_one_finding_per_advisory_with_its_fix():
    """In the packages' order; a package with no advisories adds nothing."""
    packages = [("Jinja2", "2.10"), ("requests", "2.32.0")]
    batch = {"results": [{"vulns": [{"id": "GHSA-xxxx"}]}, {}]}
    assert tool.findings(packages, batch, {"GHSA-xxxx": ADVISORY}) == [
        {"package": "Jinja2", "version": "2.10", "id": "GHSA-xxxx", "summary": "Sandbox escape", "fixed_in": "2.10.1"}]
    assert tool.fixed_in(ADVISORY, "requests") == ""


def test_the_weekly_check_is_due_after_a_week_and_findings_are_said_once(tmp_path, monkeypatch):
    """None saved: due. Saved today: not due, and its findings make one message whose fingerprint is the ids."""
    monkeypatch.setattr(da, "DEV_DATA", tmp_path)
    now = datetime(2026, 11, 8, 9, 0)
    assert da.due(now)
    finding = {"package": "Jinja2", "version": "2.10", "id": "GHSA-xxxx", "summary": "", "fixed_in": "2.10.1"}
    da.save([finding], now)
    assert not da.due(now + timedelta(days=3)) and da.due(now + timedelta(days=8))
    title, message, fingerprint = da.offer(da.last_result())
    assert title == "Security updates for MIA" and "Jinja2 2.10 (GHSA-xxxx): update to 2.10.1" in message
    assert fingerprint == "dependency_audit:GHSA-xxxx"
    assert da.offer({"checked": "x", "findings": []}) is None and da.offer(None) is None
