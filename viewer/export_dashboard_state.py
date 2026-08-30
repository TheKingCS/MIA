"""
MIA Homestead — State Export for the Operations Dashboard
v0.1

Exports the aggregate data the on-site ops dashboard needs: live sensor
readings + short trend history per cell, open alerts, yield vs. target,
active experiments, revenue, low-stock/to-order inventory, power/battery
status, and open maintenance tasks. Mirrors viewer/export_state.py's
pattern (a flat JSON file main.py regenerates every cycle) but for the
data-dense overview screen rather than the 3D spatial "go here" view —
the two views read different JSON files and can be regenerated
independently.

Every field here is read straight off the tables it names — an empty
list/None means genuinely no data yet, not "ask the model to guess."
The dashboard page must render that as an honest empty state, matching
this project's anti-fabrication rule for the assistant (see
_annotate_if_empty() in assistant/greenhouse_assistant.py) applied to a
UI instead of a chat reply.

Usage:
    python viewer/export_dashboard_state.py --db mia_homestead.db
"""

import argparse
import json
import sqlite3
from pathlib import Path


def sparkline_points(conn: sqlite3.Connection, sensor_id: int, limit: int = 8) -> list[float]:
    rows = conn.execute(
        "SELECT value FROM sensor_readings WHERE sensor_id = ? ORDER BY id DESC LIMIT ?",
        (sensor_id, limit),
    ).fetchall()
    return [r["value"] for r in reversed(rows)]


def export_dashboard_state(db_path: str, out_path: str) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    output = {}

    cells = []
    for cell in conn.execute("SELECT * FROM cells").fetchall():
        cell_id = cell["id"]
        sensors = conn.execute(
            "SELECT id, type, unit FROM sensors WHERE cell_id = ? AND active = 1", (cell_id,)
        ).fetchall()
        readings = []
        for s in sensors:
            latest = conn.execute(
                "SELECT value, timestamp, is_stale FROM sensor_readings WHERE sensor_id = ? "
                "ORDER BY id DESC LIMIT 1",
                (s["id"],),
            ).fetchone()
            if not latest:
                continue
            readings.append({
                "type": s["type"],
                "unit": s["unit"],
                "value": latest["value"],
                "timestamp": latest["timestamp"],
                "is_stale": bool(latest["is_stale"]),
                "trend": sparkline_points(conn, s["id"]),
            })
        cells.append({"id": cell_id, "name": cell["name"], "readings": readings})
    output["cells"] = cells

    # Alerts are de-duplicated at the source now (contracts/
    # mia_homestead_contract.py's _raise_alert() bumps occurrence_count
    # instead of re-inserting a repeat) — one row per distinct
    # (source, message) while unresolved, so this just orders and caps,
    # no Python-side collapsing needed. Ordered by last_seen (most
    # recently relevant first), severity-primary.
    output["alerts"] = [
        {**dict(r), "repeat_count": r["occurrence_count"]}
        for r in conn.execute(
            "SELECT * FROM alerts WHERE resolved = 0 ORDER BY "
            "CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, "
            "last_seen DESC LIMIT 10"
        ).fetchall()
    ]

    yield_events_7d = [
        dict(r) for r in conn.execute(
            "SELECT * FROM yield_events WHERE timestamp >= datetime('now', '-7 days') "
            "ORDER BY timestamp DESC"
        ).fetchall()
    ]
    prior_week_total = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM yield_events "
        "WHERE timestamp >= datetime('now', '-14 days') AND timestamp < datetime('now', '-7 days')"
    ).fetchone()[0]
    output["yield"] = {
        "this_week_total": sum(e["quantity"] or 0 for e in yield_events_7d),
        "prior_week_total": prior_week_total,
        "events": yield_events_7d,
    }

    plantings = []
    for p in conn.execute("SELECT * FROM bed_plantings WHERE status = 'active'").fetchall():
        actual = conn.execute(
            "SELECT COALESCE(SUM(quantity), 0) FROM yield_events WHERE cell_id = ? AND timestamp >= ?",
            (p["cell_id"], p["planted_date"]),
        ).fetchone()[0]
        species = conn.execute(
            "SELECT common_name FROM species_profiles WHERE id = ?", (p["species_id"],)
        ).fetchone()
        plantings.append({
            "planting_id": p["id"],
            "species": species["common_name"] if species else None,
            "grow_bed_name": p["grow_bed_name"],
            "expected_amount": p["expected_yield_amount"],
            "expected_unit": p["expected_yield_unit"],
            "actual_amount_so_far": actual,
        })
    output["plantings"] = plantings

    output["revenue_mtd"] = conn.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM revenue_transactions "
        "WHERE timestamp >= datetime('now', 'start of month')"
    ).fetchone()[0]

    output["experiments"] = [
        dict(r) for r in conn.execute(
            "SELECT * FROM experiments WHERE status IN ('proposed', 'approved', 'running') "
            "ORDER BY id DESC"
        ).fetchall()
    ]

    output["low_stock"] = [
        dict(r) for r in conn.execute(
            "SELECT id, name, category, quantity_on_hand, reorder_threshold, unit, supplier "
            "FROM inventory_items WHERE quantity_on_hand <= reorder_threshold"
        ).fetchall()
    ]
    output["pending_orders"] = [
        dict(r) for r in conn.execute(
            "SELECT io.id AS order_id, io.item_id, ii.name, io.status FROM inventory_orders io "
            "JOIN inventory_items ii ON ii.id = io.item_id WHERE io.status IN ('proposed', 'ordered')"
        ).fetchall()
    ]

    output["power"] = [
        dict(r) for r in conn.execute(
            "SELECT * FROM power_telemetry ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
    ]

    output["maintenance"] = [
        dict(r) for r in conn.execute(
            "SELECT * FROM maintenance_tasks WHERE status IN ('open', 'in_progress') "
            "ORDER BY CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 "
            "WHEN 'medium' THEN 2 ELSE 3 END, due_date ASC"
        ).fetchall()
    ]

    output["generated_at"] = conn.execute("SELECT datetime('now')").fetchone()[0]

    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported dashboard state -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--out", default="viewer/dashboard_state.json")
    args = parser.parse_args()
    export_dashboard_state(args.db, args.out)
