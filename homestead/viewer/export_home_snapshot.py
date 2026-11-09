"""
MIA Homestead — Summarized State Export for MIA Home
v0.1

Produces a small, glance-level snapshot for MIA Home's dashboard —
distinct from viewer/export_dashboard_state.py, which exports full
detail (every sensor's trend history, every open alert, every
maintenance task) for Homestead's OWN on-site ops console. This script
reuses that script's queries but summarizes them down, matching the
shared JSON snapshot shape MIA Home's core/finance_manager.py already
knows how to ingest: a flat top-level object with `source` and
`generated_at` (both required — everything else is read verbatim into
`FinancialSnapshot.data`/`HomesteadSnapshot.data`, `summary` included,
NOT nested under a `data` key of its own — confirmed 2026-08-30 against
the real `~/Projects/MIA/gui/home_dashboard.py` formatter code after an
earlier draft of this script got that nesting wrong and silently failed
to import; caught by actually running the real MIA-side ingestion
against a real export, not just by writing to spec). See
docs/MIA_HOME_SYNC_PLAN.md for the full scoping.

**Delivery to MIA Home is deliberately NOT automated here.** Per the
plan doc, neither of MIA Home's other two snapshot sources (a Kraken
trading agent, a real-estate dashboard) have automated cross-machine
transport yet either — both are manual/user-downloaded. This script
only writes the local file; getting it onto MIA Home's watched folder
(a Ryzen/Radeon desktop, per the user's 2026-08-30 clarification — the
compute backend, accessed from multiple client devices/screens
including Pi5s elsewhere in the build) is a separate, still-undecided
step. Don't build automated transport here without that decision made
first.

Usage:
    python viewer/export_home_snapshot.py --db mia_homestead.db
"""

import argparse
import json
import re
import sqlite3
from pathlib import Path


def _cell_slug(name: str) -> str:
    """'Cell A' -> 'cell_a' — matches this project's own module-id
    naming convention (see config/modules.yaml), used below to decide
    whether an alert's source clearly belongs to one cell rather than
    being a whole-system condition (power, self-preservation) that
    would be misleading to pin on a single cell."""
    return "cell_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def export_home_snapshot(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Alerts are de-duplicated at the source (contracts/
    # mia_homestead_contract.py's _raise_alert()) — one row per distinct
    # (source, message) while unresolved, occurrence_count tracks
    # repeats — no Python-side collapsing needed here anymore.
    alerts = [dict(r) for r in conn.execute(
        "SELECT * FROM alerts WHERE resolved = 0 ORDER BY "
        "CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, last_seen DESC"
    ).fetchall()]

    critical_count = sum(1 for a in alerts if a["severity"] == "critical")
    warning_count = sum(1 for a in alerts if a["severity"] == "warning")
    top_alert = None
    if alerts:
        top = alerts[0]
        top_alert = {
            "severity": top["severity"],
            "source": top["source"],
            "message": top["message"],
            "repeat_count": top["occurrence_count"],
        }

    yield_events_7d = conn.execute(
        "SELECT quantity FROM yield_events WHERE timestamp >= datetime('now', '-7 days')"
    ).fetchall()
    yield_this_week = sum(r["quantity"] or 0 for r in yield_events_7d)
    yield_prior_week = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM yield_events "
        "WHERE timestamp >= datetime('now', '-14 days') AND timestamp < datetime('now', '-7 days')"
    ).fetchone()[0]

    revenue_mtd = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM revenue_transactions "
        "WHERE timestamp >= datetime('now', 'start of month')"
    ).fetchone()[0]

    open_maintenance = conn.execute(
        "SELECT priority, COUNT(*) as n FROM maintenance_tasks "
        "WHERE status IN ('open', 'in_progress') GROUP BY priority"
    ).fetchall()
    maintenance_by_priority = {r["priority"]: r["n"] for r in open_maintenance}
    open_maintenance_total = sum(maintenance_by_priority.values())
    open_maintenance_critical = maintenance_by_priority.get("critical", 0)

    cells_out = []
    for cell in conn.execute("SELECT * FROM cells").fetchall():
        slug = _cell_slug(cell["name"])
        cell_alerts = [a for a in alerts if a["source"] == slug]
        if cell_alerts:
            status = cell_alerts[0]["severity"]
        else:
            status = "ok"
        cells_out.append({"name": cell["name"], "status": status})

    generated_at = conn.execute("SELECT datetime('now')").fetchone()[0].replace(" ", "T") + "Z"
    output = {
        "source": "mia_homestead",
        "generated_at": generated_at,
        "summary": {
            "critical_alert_count": critical_count,
            "warning_alert_count": warning_count,
            "yield_this_week_kg": round(yield_this_week, 2),
            "yield_prior_week_kg": round(yield_prior_week, 2),
            "revenue_mtd": round(revenue_mtd, 2),
            "open_maintenance_critical": open_maintenance_critical,
            "open_maintenance_total": open_maintenance_total,
        },
        "cells": cells_out,
        "top_alert": top_alert,
    }

    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported MIA Home snapshot -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--out", default="viewer/home_snapshot.json")
    args = parser.parse_args()
    export_home_snapshot(args.db, args.out)
