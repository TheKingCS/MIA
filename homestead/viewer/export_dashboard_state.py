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
import sys
from pathlib import Path


def sparkline_points(conn: sqlite3.Connection, sensor_id: int, limit: int = 8) -> list[float]:
    rows = conn.execute(
        "SELECT value FROM sensor_readings WHERE sensor_id = ? ORDER BY id DESC LIMIT ?",
        (sensor_id, limit),
    ).fetchall()
    return [r["value"] for r in reversed(rows)]


ADJUSTABLE = ("ph_target_min", "ph_target_max", "ec_target_min", "ec_target_max", "temp_min", "temp_max",
              "humidity_max")


def mia_directions(conn) -> dict:
    """What MIA reads back about her directions (DEC-0185, docs/MIA_COMMAND_INTERFACE.md step 3): each cell's current
    adjustable targets (as the cell reads them: an active override, else config/modules.yaml), so she sends the value
    she believes from what the node says; and her latest directions with what became of each (staged, applied or
    refused, why, and its proposal's status once someone approved or denied it), so she reports a change only once
    she sees it applied here. Nothing from before the table existed: empty."""
    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from core.experiment_manager import ExperimentManager

    manager, modules = ExperimentManager(conn), str(root / "config" / "modules.yaml")
    targets = {str(cell[0]): {p: manager._current_target(cell[0], p, modules) for p in ADJUSTABLE}
               for cell in conn.execute("SELECT id FROM cells").fetchall()}
    has_table = conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'mia_commands'").fetchone()
    recent = [] if not has_table else [dict(r) for r in conn.execute(
        "SELECT c.id, c.received_at, c.cell_id, c.param_name, c.value, c.believed_current, c.state, c.reason, "
        "c.proposal_id, p.status AS proposal_status, p.decided_at FROM mia_commands c "
        "LEFT JOIN parameter_change_proposals p ON p.id = c.proposal_id ORDER BY c.id DESC LIMIT 20").fetchall()]
    for row in recent:  # what it came to: applied only once the change is a live target
        row["outcome"] = ("applied" if row["state"] == "applied" or row.get("proposal_status") == "approved" else
                          "denied" if row.get("proposal_status") == "denied" else
                          "waiting for approval" if row["state"] == "staged" else "refused")
    return {"targets": targets, "recent": recent}


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
            "SELECT id, name, category, quantity_on_hand, reorder_threshold, unit, "
            "supplier, supplier_url, unit_cost "
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

    output["mia_directions"] = mia_directions(conn)

    output["generated_at"] = conn.execute("SELECT datetime('now')").fetchone()[0]

    conn.close()  # main.py exports every cycle: never leave a connection behind
    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported dashboard state -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--out", default="viewer/dashboard_state.json")
    args = parser.parse_args()
    export_dashboard_state(args.db, args.out)
