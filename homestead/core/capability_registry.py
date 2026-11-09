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
        self._log_changes(cap)
        self._persist(cap)
        logger.info("Registered capability: %s", cap.module_id)
        return cap

    def _log_changes(self, cap: Capability) -> None:
        """Compares against what was stored last time this module
        registered — this is the actual mechanism behind 'the system's
        self-understanding changes as the code changes.' A module whose
        declared purpose, actions, or limits changed gets a real,
        timestamped entry, not just a silent overwrite."""
        existing = self.db.execute(
            "SELECT purpose, data_produced, actions_possible, limits_and_safety, verification_evidence "
            "FROM system_capabilities WHERE module_id = ?",
            (cap.module_id,),
        ).fetchone()

        if existing is None:
            self._changelog_entry(cap.module_id, "first_registered", None, None, cap.purpose)
            return

        old_purpose, old_data, old_actions, old_limits, old_evidence = existing
        new_data = json.dumps(cap.data_produced)
        new_actions = json.dumps(cap.actions_possible)
        new_evidence = json.dumps(cap.verification_evidence)

        if old_purpose != cap.purpose:
            self._changelog_entry(cap.module_id, "capability_changed", "purpose", old_purpose, cap.purpose)
        if old_data != new_data:
            self._changelog_entry(cap.module_id, "capability_changed", "data_produced", old_data, new_data)
        if old_actions != new_actions:
            self._changelog_entry(cap.module_id, "capability_changed", "actions_possible", old_actions, new_actions)
        if old_limits != cap.limits_and_safety:
            self._changelog_entry(cap.module_id, "capability_changed", "limits_and_safety",
                                   old_limits, cap.limits_and_safety)
        if old_evidence != new_evidence:
            # Worth its own change type — adding proof that something
            # works is a meaningfully different event than the
            # capability's description changing.
            self._changelog_entry(cap.module_id, "verification_changed", "verification_evidence",
                                   old_evidence, new_evidence)

    def _changelog_entry(self, module_id: str, change_type: str, field_name: str | None,
                          old_value: str | None, new_value: str | None) -> None:
        self.db.execute(
            "INSERT INTO system_changelog (module_id, change_type, field_name, old_value, new_value) "
            "VALUES (?, ?, ?, ?, ?)",
            (module_id, change_type, field_name, old_value, new_value),
        )
        self.db.commit()
        logger.info("Changelog: %s.%s changed (%s)", module_id, field_name or "", change_type)

    def register_all(self, items: list[Describable]) -> list[Capability]:
        return [self.register(item) for item in items]

    def _persist(self, cap: Capability) -> None:
        self.db.execute(
            """
            INSERT INTO system_capabilities
            (module_id, display_name, purpose, data_produced, actions_possible,
             limits_and_safety, example_questions, verification_evidence, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(module_id) DO UPDATE SET
                display_name = excluded.display_name,
                purpose = excluded.purpose,
                data_produced = excluded.data_produced,
                actions_possible = excluded.actions_possible,
                limits_and_safety = excluded.limits_and_safety,
                example_questions = excluded.example_questions,
                verification_evidence = excluded.verification_evidence,
                updated_at = datetime('now')
            """,
            (
                cap.module_id, cap.display_name, cap.purpose,
                json.dumps(cap.data_produced), json.dumps(cap.actions_possible),
                cap.limits_and_safety, json.dumps(cap.example_questions),
                json.dumps(cap.verification_evidence),
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
    def get_change_history(db_conn: sqlite3.Connection, module_id: str = None, limit: int = 20) -> list[dict]:
        """The direct answer to 'how have you changed' — a real,
        queryable log of when this system's self-understanding shifted,
        not a guess based on training data or a static changelog file
        someone has to remember to update."""
        q = "SELECT * FROM system_changelog"
        params = ()
        if module_id:
            q += " WHERE module_id = ?"
            params = (module_id,)
        q += " ORDER BY detected_at DESC LIMIT ?"
        params = params + (limit,)
        db_conn.row_factory = sqlite3.Row
        return [dict(r) for r in db_conn.execute(q, params).fetchall()]

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
            d["verification_evidence"] = json.loads(d.get("verification_evidence") or "[]")
            results.append(d)
        return results

    @staticmethod
    def get_verification_coverage(db_conn: sqlite3.Connection) -> dict:
        """What fraction of registered capabilities actually have proof
        behind them, vs. just a description. This is the honest
        maturity metric — a module can describe itself perfectly and
        still have zero evidence it actually works."""
        rows = db_conn.execute(
            "SELECT module_id, verification_evidence FROM system_capabilities"
        ).fetchall()
        total = len(rows)
        verified = 0
        unverified = []
        for module_id, evidence_json in rows:
            evidence = json.loads(evidence_json or "[]")
            if evidence:
                verified += 1
            else:
                unverified.append(module_id)
        return {"total": total, "verified": verified, "unverified_modules": unverified}
