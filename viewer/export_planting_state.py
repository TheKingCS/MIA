"""
MIA Homestead — State Export for the Planting Planner Viewer
v0.1

Exports every real grow bed (config/layout.json for real w/l dimensions,
matching viewer/export_state.py's DB+layout.json merge pattern) with its
planned/active/recent plantings grouped underneath, via
core/bed_planting.py's get_bed_layout() — the real data layer, not
duplicated SQL (same discipline as every other export script here).

Run this once, or on a loop, to keep the viewer current. main.py runs
this automatically every cycle once wired in.

Usage:
    python viewer/export_planting_state.py --db mia_homestead.db
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.bed_planting import BedPlantingManager
from core.species_registry import SpeciesRegistry


def export_planting_state(db_path: str, layout_path: str, out_path: str):
    conn = sqlite3.connect(db_path)
    layout = json.loads(Path(layout_path).read_text())
    species_registry = SpeciesRegistry(conn)
    bed_planting = BedPlantingManager(conn, species_registry)

    # Real bed w/l dimensions live only in layout.json today (grow_beds
    # in the DB has sqft but not an explicit width/length) — merged by
    # name, same pattern export_state.py already uses for tanks.
    layout_beds_by_name = {}
    for cell in layout.get("cells", []):
        for bed in cell.get("grow_beds", []):
            layout_beds_by_name[bed["name"]] = bed

    beds = bed_planting.get_bed_layout()

    cells_out = []
    for cell in layout.get("cells", []):
        cell_beds = [b for b in beds if b["cell_id"] == cell["id"]]
        beds_out = []
        for bed in cell_beds:
            layout_bed = layout_beds_by_name.get(bed["name"], {})
            sqft = bed["sqft"] or layout_bed.get("sqft") or 16
            # Fallback size_ft only if layout.json has no real dimensions
            # for this bed — a plausible rectangle, not a guess dressed
            # up as real data (flagged via "estimated_size" below).
            size_ft = layout_bed.get("size_ft")
            estimated_size = size_ft is None
            if size_ft is None:
                size_ft = {"w": round((sqft ** 0.5) * 1.6, 1), "l": round((sqft ** 0.5) / 1.6, 1)}
            plantings_out = [
                {
                    "id": p["id"],
                    "status": p["status"],
                    "species": p["common_name"],
                    "organism_type": p["organism_type"],
                    "variety": p["variety"],
                    "quantity_planted": p["quantity_planted"],
                    "planted_date": p["planted_date"],
                    "target_plant_date": p["target_plant_date"],
                    "expected_harvest_date": p["expected_harvest_date"],
                    "days_to_maturity": p["days_to_maturity"],
                    "notes": p["notes"],
                }
                for p in bed["plantings"]
            ]
            beds_out.append({
                "name": bed["name"],
                "sqft": sqft,
                "media_type": bed["media_type"],
                "size_ft": size_ft,
                "estimated_size": estimated_size,
                "plantings": plantings_out,
            })
        cells_out.append({"id": cell["id"], "name": cell["name"], "beds": beds_out})

    output = {
        "cells": cells_out,
        "species": [
            {"id": s["id"], "common_name": s["common_name"], "organism_type": s["organism_type"]}
            for s in species_registry.list_all()
        ],
    }
    output["generated_at"] = conn.execute("SELECT datetime('now')").fetchone()[0]

    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported planting planner state ({sum(len(c['beds']) for c in cells_out)} bed(s)) -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--layout", default="config/layout.json")
    parser.add_argument("--out", default="viewer/planting_state.json")
    args = parser.parse_args()
    export_planting_state(args.db, args.layout, args.out)
