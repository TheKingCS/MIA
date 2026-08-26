"""
MIA Homestead — Capability Registry
v0.1

Collects `describe_capabilities()` from every loaded module/service and
persists it to the `system_capabilities` table. This table — not a
hand-maintained doc, not a hardcoded chunk of the system prompt — is
the assistant's actual source of self-knowledge. It's rebuilt every
time the system starts, so it's never more than one restart behind
what the code actually does.

Call register_all() once, right after loading modules and services in
main.py. The assistant reads system_capabilities directly (see
assistant/greenhouse_assistant.py).
"""

import json
import logging
import sqlite3

from contracts.capability import Capability, Describable

logger = logging.getLogger("mia_homestead.capability_registry")


class CapabilityRegistry:
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    def register(self, item: Describable) -> Capability:
        cap = item.describe_capabilities()
        self._persist(cap)
        logger.info("Registered capability: %s", cap.module_id)
        return cap

    def register_all(self, items: list[Describable]) -> list[Capability]:
        return [self.register(item) for item in items]

    def _persist(self, cap: Capability) -> None:
        self.db.execute(
            """
            INSERT INTO system_capabilities
            (module_id, display_name, purpose, data_produced, actions_possible,
             limits_and_safety, example_questions, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(module_id) DO UPDATE SET
                display_name = excluded.display_name,
                purpose = excluded.purpose,
                data_produced = excluded.data_produced,
                actions_possible = excluded.actions_possible,
                limits_and_safety = excluded.limits_and_safety,
                example_questions = excluded.example_questions,
                updated_at = datetime('now')
            """,
            (
                cap.module_id, cap.display_name, cap.purpose,
                json.dumps(cap.data_produced), json.dumps(cap.actions_possible),
                cap.limits_and_safety, json.dumps(cap.example_questions),
            ),
        )
        self.db.commit()

    @staticmethod
    def render_compact(db_conn: sqlite3.Connection) -> str:
        """Compact summary for the system prompt — cheap to include on
        every turn, enough for the assistant to know what exists and
        route follow-up questions to get_system_capabilities for detail."""
        rows = db_conn.execute(
            "SELECT module_id, display_name, purpose FROM system_capabilities ORDER BY module_id"
        ).fetchall()
        if not rows:
            return "(no modules registered yet)"
        lines = [f"- {display_name} ({module_id}): {purpose}" for module_id, display_name, purpose in rows]
        return "\n".join(lines)

    @staticmethod
    def render_full(db_conn: sqlite3.Connection, module_id: str = None) -> list[dict]:
        """Full detail — actions possible, limits, example questions —
        for the get_system_capabilities tool to return on demand."""
        q = "SELECT * FROM system_capabilities"
        params = ()
        if module_id:
            q += " WHERE module_id = ?"
            params = (module_id,)
        db_conn.row_factory = sqlite3.Row
        rows = db_conn.execute(q, params).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["data_produced"] = json.loads(d["data_produced"] or "[]")
            d["actions_possible"] = json.loads(d["actions_possible"] or "[]")
            d["example_questions"] = json.loads(d["example_questions"] or "[]")
            results.append(d)
        return results
