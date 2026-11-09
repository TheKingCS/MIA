"""
MIA Homestead — State Export for the Activity Journal
v0.1

Same pattern as viewer/export_state.py and export_dashboard_state.py —
a flat JSON file main.py regenerates every cycle, this time backed by
core/activity_journal.py's three read-only aggregation methods
(get_journal/get_current_status/get_whats_next) rather than raw table
queries of its own.

Usage:
    python viewer/export_journal_state.py --db mia_homestead.db
"""

import argparse
import json
import sqlite3
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_journal import ActivityJournal


def export_journal_state(db_path: str, out_path: str, days: int = 7) -> None:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    journal = ActivityJournal(conn)

    output = {
        "journal": journal.get_journal(days=days),
        "current_status": journal.get_current_status(),
        "upcoming": journal.get_whats_next(),
        "generated_at": conn.execute("SELECT datetime('now')").fetchone()[0],
    }

    Path(out_path).write_text(json.dumps(output, indent=2, default=str))
    print(f"Exported journal state ({len(output['journal'])} entries) -> {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--out", default="viewer/journal_state.json")
    parser.add_argument("--days", type=int, default=7)
    args = parser.parse_args()
    export_journal_state(args.db, args.out, args.days)
