"""
MIA Homestead — State Export for Digital Twin Viewer
v0.2

Exports per-OBJECT status (not just per-cell) so the viewer can glow the
exact physical thing that needs attention — a tank, the power array, the
help beacon — rather than a whole cell. This is driven entirely by
`linked_module_id` in config/layout.json: each physical object declares
which module's alerts it should reflect, and this script just looks up
open alerts for that module_id. Adding a new physical object later means
editing layout.json, not this script.

Run this once, or on a loop, to keep the viewer current. main.py runs
this automatically every cycle once wired in.

Usage:
    python viewer/export_state.py --db mia_homestead.db
"""

import argparse
import json
import sqlite3
from pathlib import Path


def object_status(conn: sqlite3.Connection, module_id: str) -> dict:
    """Looks up the worst open alert sourced from this module_id and
    returns a status + the human-readable reason, so the viewer can
    both color the object AND tell a person WHY."""
    row = conn.execute(
        "SELECT severity, message FROM alerts WHERE resolved = 0 AND source = ? "
        "ORDER BY CASE severity WHEN 'critical' THEN 0 WHEN 'warning' THEN 1 ELSE 2 END, "
        "timestamp DESC LIMIT 1",
        (module_id,),
    ).fetchone()
    if not row:
        return {"status": "ok", "reason": None}
    severity, message = row
    return {"status": severity, "reason": message}


def export_state(db_path: str, layout_path: str, out_path: str):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    layout = json.loads(Path(layout_path).read_text())

    output = {"cells": [], "power": {}, "beacons": []}

    for cell in layout.get("cells", []):
        cell_id = cell["id"]
        readings = conn.execute(
            """
            SELECT s.type, sr.value FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.cell_id = ?
            AND sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id)
            """,
            (cell_id,),
        ).fetchall()

        tanks_out = []
        for tank in cell.get("tanks", []):
            linked = tank.get("linked_module_id")
            status = object_status(conn, linked) if linked else {"status": "ok", "reason": None}
            tanks_out.append({"name": tank["name"], **status})

        output["cells"].append({
            "id": cell_id,
            "name": cell["name"],
            "readings": {r["type"]: r["value"] for r in readings},
            "tanks": tanks_out,
        })

    for array_name, array_cfg in layout.get("power", {}).items():
        linked = array_cfg.get("linked_module_id")
        status = object_status(conn, linked) if linked else {"status": "ok", "reason": None}
        output["power"][array_name] = status

    for beacon in layout.get("beacons", []):
        linked = beacon.get("linked_module_id")
        status = object_status(conn, linked) if linked else {"status": "ok", "reason": None}
        # A beacon's real signal is an active help_request, not just an
        # open alert — check that specifically too.
        active_help = conn.execute(
            "SELECT message FROM help_requests WHERE resolved = 0 ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if active_help:
            status = {"status": "critical", "reason": active_help[0]}
        output["beacons"].append({"name": beacon["name"], **status})

    # Collect a flat "go here" list for anything not ok — this is what
    # the HUD panel in the viewer reads directly.
    go_here = []
    for cell in output["cells"]:
        for tank in cell["tanks"]:
            if tank["status"] != "ok":
                go_here.append({"location": tank["name"], "status": tank["status"], "reason": tank["reason"]})
    for name, status in output["power"].items():
        if status["status"] != "ok":
            go_here.append({"location": name, "status": status["status"], "reason": status["reason"]})
    for beacon in output["beacons"]:
        if beacon["status"] != "ok":
            go_here.append({"location": beacon["name"], "status": beacon["status"], "reason": beacon["reason"]})
    output["go_here"] = go_here

    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported state ({len(go_here)} location(s) need attention) -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--layout", default="config/layout.json")
    parser.add_argument("--out", default="viewer/state.json")
    args = parser.parse_args()
    export_state(args.db, args.layout, args.out)
