"""
MIA Homestead — Harvest-to-Sale Lot Traceability
v0.1

Real gap found while scoping docs/SUSTAINING_FEATURES.md #21:
yield_events had a full schema and was already READ everywhere
(report_generator, finance_tracker, experiment_manager, the assistant),
but nothing anywhere ever WROTE to it — same shape as the
revenue_transactions gap fixed earlier this project. record_yield()
here is the first real write path.

This is deliberately NOT a blockchain integration — this project's own
established no-vendor-dependency stance (CLAUDE.md; the SMS/ordering
corrections) argues against an external chain/wallet dependency for
what's fundamentally a local record-linking problem. Instead:
yield_events.bed_planting_id links a harvest back to the planting that
produced it (nullable — fish harvests aren't bed_plantings rows, and
historical yield honestly stays unattributed), and
traceability_ledger hash-chains each finalized lot record to the
previous one for local tamper-evidence: editing or deleting a
historical row breaks the chain, verifiably, with no external service.
"""

import hashlib
import json
import logging
import sqlite3
from datetime import datetime

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.traceability")

GENESIS = "GENESIS"


class TraceabilityManager(Describable):
    def __init__(self, db_conn: sqlite3.Connection):
        self.db = db_conn

    # ---------- Recording ----------

    def record_yield(self, cell_id: int, yield_type: str, item: str,
                      quantity: float = None, unit: str = None,
                      bed_planting_id: int = None, notes: str = None) -> int:
        """The real write path for yield_events — didn't exist before
        this. bed_planting_id is nullable: real for a bed harvest tied
        to a tracked planting, honestly NULL for a fish harvest (fish
        aren't bed_plantings rows) or any yield not tied to a tracked
        planting."""
        if yield_type not in ("harvest_produce", "harvest_fish"):
            raise ValueError(f"yield_type must be 'harvest_produce' or 'harvest_fish', got '{yield_type}'")
        cur = self.db.execute(
            "INSERT INTO yield_events (cell_id, bed_planting_id, yield_type, item, quantity, unit, notes) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (cell_id, bed_planting_id, yield_type, item, quantity, unit, notes),
        )
        self.db.commit()
        logger.info("Yield recorded: cell %s, %s %s%s (planting %s)",
                    cell_id, quantity, item, f" {unit}" if unit else "", bed_planting_id)
        return cur.lastrowid

    # ---------- Lot assembly ----------

    def get_lot_record(self, yield_event_id: int) -> dict:
        """Assembles everything real and known about one harvest: the
        yield itself, its linked planting (if any), the cell's real
        dosing/water-quality/feeding/pest history during that planting's
        life, and any revenue this specific yield was sold in
        (revenue_transactions.yield_event_id is a real, pre-existing FK).

        Honest about precision, same discipline as
        BedPlantingManager.get_expected_vs_actual(): dosing/water-quality/
        feeding history is CELL-wide, not bed-specific — if multiple
        plantings share a cell's water during the same window, this
        record includes all of it, correctly, since they really did
        share the same water chemistry. Flagged explicitly, not hidden."""
        self.db.row_factory = sqlite3.Row
        yield_row = self.db.execute(
            "SELECT * FROM yield_events WHERE id = ?", (yield_event_id,)
        ).fetchone()
        if not yield_row:
            return {"error": f"no yield_event {yield_event_id}"}
        yield_event = dict(yield_row)

        planting = None
        window_start = None
        window_end = yield_event["timestamp"]
        isolated = None
        if yield_event["bed_planting_id"] is not None:
            planting_row = self.db.execute(
                "SELECT bp.*, sp.common_name FROM bed_plantings bp "
                "JOIN species_profiles sp ON sp.id = bp.species_id WHERE bp.id = ?",
                (yield_event["bed_planting_id"],),
            ).fetchone()
            if planting_row:
                planting = dict(planting_row)
                window_start = planting["planted_date"]
                other_active = self.db.execute(
                    "SELECT COUNT(*) FROM bed_plantings WHERE cell_id = ? AND id != ? "
                    "AND status IN ('active', 'harvested') AND planted_date IS NOT NULL "
                    "AND planted_date <= ?",
                    (yield_event["cell_id"], planting["id"], window_end),
                ).fetchone()[0]
                isolated = other_active == 0

        cell_id = yield_event["cell_id"]

        def _window_query(table: str, ts_col: str = "timestamp") -> list[dict]:
            if window_start is None:
                return []
            rows = self.db.execute(
                f"SELECT * FROM {table} WHERE cell_id = ? AND {ts_col} >= ? AND {ts_col} <= ? "
                f"ORDER BY {ts_col} ASC",
                (cell_id, window_start, window_end),
            ).fetchall()
            return [dict(r) for r in rows]

        dosing_history = _window_query("dosing_events")
        water_quality_history = _window_query("water_quality_tests")
        feeding_history = _window_query("feeding_events")
        pest_disease_history = _window_query("pest_disease_observations")

        revenue = [dict(r) for r in self.db.execute(
            "SELECT * FROM revenue_transactions WHERE yield_event_id = ?", (yield_event_id,)
        ).fetchall()]

        return {
            "yield_event": yield_event,
            "planting": planting,
            "window": {"start": window_start, "end": window_end},
            "isolated_to_this_planting": isolated,
            "precision_note": (
                "no bed_planting linked — only the yield event and any direct revenue are known, "
                "no growth/dosing history available for this lot"
                if planting is None else
                "dosing/water-quality/feeding/pest history is cell-wide during this planting's window — "
                "isolated to this planting" if isolated else
                "dosing/water-quality/feeding/pest history is cell-wide during this planting's window — "
                "NOT isolated, other plantings shared this cell's water during the same window"
            ),
            "dosing_history": dosing_history,
            "water_quality_history": water_quality_history,
            "feeding_history": feeding_history,
            "pest_disease_history": pest_disease_history,
            "revenue": revenue,
        }

    # ---------- Ledger (local tamper-evidence, no external chain) ----------

    def finalize_lot(self, yield_event_id: int) -> dict:
        """Snapshots the current lot record and appends it to the local
        hash chain. Deliberately an explicit action, not automatic on
        every yield — not every harvest needs an exported/finalized
        record, same 'don't manufacture ceremony nothing asked for'
        discipline as the rest of this project."""
        record = self.get_lot_record(yield_event_id)
        if "error" in record:
            return record
        record_json = json.dumps(record, sort_keys=True, default=str)

        last = self.db.execute(
            "SELECT record_hash FROM traceability_ledger ORDER BY id DESC LIMIT 1"
        ).fetchone()
        prev_hash = last[0] if last else GENESIS
        record_hash = hashlib.sha256((prev_hash + record_json).encode("utf-8")).hexdigest()

        cur = self.db.execute(
            "INSERT INTO traceability_ledger (yield_event_id, record_json, prev_hash, record_hash) "
            "VALUES (?, ?, ?, ?)",
            (yield_event_id, record_json, prev_hash, record_hash),
        )
        self.db.commit()
        logger.info("Lot finalized: yield_event %s, ledger row %s", yield_event_id, cur.lastrowid)
        return {"ledger_id": cur.lastrowid, "yield_event_id": yield_event_id, "record_hash": record_hash}

    def verify_ledger(self) -> dict:
        """Walks the whole chain and recomputes every hash — the real
        tamper-evidence check. A row edited or deleted after the fact
        breaks the chain from that point forward, detectably, without
        needing an external service to verify against."""
        rows = self.db.execute(
            "SELECT id, yield_event_id, record_json, prev_hash, record_hash "
            "FROM traceability_ledger ORDER BY id ASC"
        ).fetchall()
        expected_prev = GENESIS
        for row in rows:
            ledger_id, yield_event_id, record_json, prev_hash, record_hash = row
            if prev_hash != expected_prev:
                return {
                    "intact": False, "chain_length": len(rows),
                    "broken_at_ledger_id": ledger_id,
                    "reason": "prev_hash doesn't match the previous row's hash — a row was likely "
                              "inserted, deleted, or reordered",
                }
            recomputed = hashlib.sha256((prev_hash + record_json).encode("utf-8")).hexdigest()
            if recomputed != record_hash:
                return {
                    "intact": False, "chain_length": len(rows),
                    "broken_at_ledger_id": ledger_id,
                    "reason": "record_hash doesn't match the record's own content — this row's "
                              "record_json was altered after finalization",
                }
            expected_prev = record_hash
        return {"intact": True, "chain_length": len(rows)}

    def get_ledger_entry_for_yield(self, yield_event_id: int) -> dict | None:
        row = self.db.execute(
            "SELECT id, created_at, record_hash FROM traceability_ledger "
            "WHERE yield_event_id = ? ORDER BY id DESC LIMIT 1",
            (yield_event_id,),
        ).fetchone()
        if not row:
            return None
        return {"ledger_id": row[0], "created_at": row[1], "record_hash": row[2]}

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="traceability",
            display_name="Harvest-to-Sale Lot Traceability",
            purpose=(
                "Records real yield events (the write path yield_events never had before this) "
                "and links a harvest back to its originating planting and cell history — dosing, "
                "water-quality tests, feeding, pest/disease observations, and any revenue it was "
                "sold in — into one queryable lot record. Finalized records are hash-chained "
                "locally for tamper-evidence, deliberately without an external blockchain/vendor "
                "dependency."
            ),
            data_produced=["yield event history", "assembled lot records", "a local tamper-evident ledger"],
            actions_possible=[
                "record a real harvest (produce or fish)",
                "assemble a full lot record for one harvest — dosing/water-quality/feeding/pest "
                "history and revenue during that planting's life",
                "finalize a lot record into the local hash-chained ledger",
                "verify the ledger's integrity end to end",
            ],
            limits_and_safety=(
                "Read/log only — never touches dosing, control, or approval logic. Cell-wide "
                "history is honestly labeled non-isolated when multiple plantings share a cell's "
                "water during the same window, never silently presented as exclusive. Not a real "
                "blockchain — a local, verifiable hash chain, matching this project's stated "
                "no-external-vendor-dependency stance."
            ),
            example_questions=[
                "Where did this batch of lettuce come from?",
                "What was this tank dosed with before this harvest?",
                "Is the traceability ledger intact?",
            ],
            verification_evidence=[
                "scenarios.py::scenario_yield_recording_and_lot_traceability",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []
