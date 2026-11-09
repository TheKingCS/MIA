"""
MIA Homestead — Automated Action Log
v0.1

dosing_events already carries a rationale per dose. This is the same
pattern for everything else automated: load-shedding, beacon triggers,
and any future action that doesn't have its own dedicated table. One
place to ask "why did you do that" regardless of which module acted.
"""

import logging
import sqlite3

logger = logging.getLogger("mia_homestead.action_log")


def log_action(db_conn: sqlite3.Connection, module_id: str, action: str, rationale: str) -> None:
    db_conn.execute(
        "INSERT INTO automated_action_log (module_id, action, rationale) VALUES (?, ?, ?)",
        (module_id, action, rationale),
    )
    db_conn.commit()
    logger.info("%s: %s — %s", module_id, action, rationale)


def get_recent_actions(db_conn: sqlite3.Connection, module_id: str = None, days: int = 7) -> list[dict]:
    db_conn.row_factory = sqlite3.Row
    q = "SELECT * FROM automated_action_log WHERE timestamp >= datetime('now', ?)"
    params = [f"-{days} days"]
    if module_id:
        q += " AND module_id = ?"
        params.append(module_id)
    q += " ORDER BY timestamp DESC"
    return [dict(r) for r in db_conn.execute(q, params).fetchall()]
