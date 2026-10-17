"""
core.boss_battles
===================

Boss battles (DEC-0028, the game layer's third piece): big goals with an
HP bar.

- **Every debt is a boss**, automatically. Its max HP is the highest
  balance MIA has seen for it (remembered here, since a debt only knows
  its current balance), its HP the balance now; each payment is a hit,
  and interest is the boss healing every month. At zero it's defeated.
- **Any mission can be a boss fight**: the person picks it; HP is what's
  left of its objectives.

`BossBook` is each person's own (a personal store): the debts' highest
balances, the missions made into bosses, and when each boss fell. It
writes through atomic_write_text, so turning a mission into a boss can
be undone. Money is never shown to a child (core/child_accounts.py).
"""

from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "boss_battles.json"

# (HP % at or above, phase): how the fight is going.
PHASES = ((75, "Full Strength"), (50, "Wounded"), (25, "Staggering"), (1, "Last Stand"), (0, "Defeated"))


def phase(percent: float) -> str:
    """Pure logic. 100 -> "Full Strength" ... 0 -> "Defeated"."""
    if percent <= 0:
        return "Defeated"
    return next(name for floor, name in PHASES if percent >= floor)


def months_to_defeat(balance: float, apr_percent: float, payment: float) -> Optional[int]:
    """Pure logic. Monthly hits of `payment` until a balance with this APR
    reaches zero; None when the payment doesn't beat the interest."""
    if balance <= 0:
        return 0
    rate = (apr_percent or 0) / 100 / 12
    if payment <= 0 or payment <= balance * rate:
        return None
    if rate == 0:
        return math.ceil(balance / payment)
    return math.ceil(-math.log(1 - rate * balance / payment) / math.log(1 + rate))


class BossBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.peaks: dict[str, float] = {}
        self.missions: list[str] = []
        self.defeated: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        self.peaks, self.missions, self.defeated = {}, [], {}
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            self.peaks = {str(k): float(v) for k, v in (raw.get("peaks") or {}).items()}
            self.missions = [str(m) for m in raw.get("missions") or []]
            self.defeated = {str(k): str(v) for k, v in (raw.get("defeated") or {}).items()}
        except (json.JSONDecodeError, OSError, TypeError, ValueError, AttributeError):
            log.exception("boss_battles.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"peaks": self.peaks, "missions": self.missions,
                                                  "defeated": self.defeated}, indent=2))

    def see(self, peaks: dict[str, float], fallen: dict[str, str]) -> None:
        """Remember new highest balances and newly defeated bosses (only
        writes when something changed)."""
        changed = False
        for key, value in peaks.items():
            if value > self.peaks.get(key, 0.0) + 1e-9:
                self.peaks[key] = round(value, 2)
                changed = True
        for key, when in fallen.items():
            if key not in self.defeated:
                self.defeated[key] = when
                changed = True
        if changed:
            self._save()

    def add_mission(self, mission_id: str) -> None:
        if mission_id not in self.missions:
            self.missions.append(mission_id)
            self._save()

    def remove_mission(self, mission_id: str) -> None:
        if mission_id in self.missions:
            self.missions.remove(mission_id)
            self._save()


def bosses(context, today: Optional[date] = None) -> dict:
    """Every boss: active ones first (closest to defeat first), then the
    defeated ones (the hall of fame)."""
    from core.child_accounts import is_child
    from core.region import money

    today = today or date.today()
    book = getattr(context, "boss_book", None)
    out: list[dict] = []
    peaks: dict[str, float] = {}
    fallen: dict[str, str] = {}
    budget = getattr(context, "budget", None)
    if budget is not None and not is_child(context):
        for d in budget.all_debts():
            key = f"debt:{d.debt_id}"
            balance = max(0.0, float(d.balance or 0))
            peak = max(balance, book.peaks.get(key, 0.0) if book else 0.0)
            peaks[key] = peak
            pct = round(100 * balance / peak, 1) if peak else 0.0
            apr = d.promo_apr if (d.promo_apr is not None and d.promo_expires_date and d.promo_expires_date >= today.isoformat()) \
                else d.interest_rate
            heal = round(balance * (apr or 0) / 100 / 12, 2)
            hits = months_to_defeat(balance, apr or 0, float(d.minimum_payment or 0))
            if balance <= 0:
                fallen[key] = (book.defeated.get(key) if book else None) or today.isoformat()
            out.append({"key": key, "kind": "debt", "id": d.debt_id, "name": d.name, "icon": "💳",
                        "hp": money(balance), "max_hp": money(peak), "percent": pct, "phase": phase(pct),
                        "damage": money(peak - balance), "heal": money(heal) if heal else "",
                        "hit": money(d.minimum_payment) if d.minimum_payment else "",
                        "hits_left": hits, "defeated": balance <= 0, "defeated_on": fallen.get(key, ""),
                        "hit_value": float(d.minimum_payment or 0) or None,
                        "action": {"kind": "debt.pay", "label": "Attack", "params": {"debt_id": d.debt_id}}})
    missions = getattr(context, "missions", None)
    if book is not None and missions is not None:
        for mission_id in list(book.missions):
            m = missions.get_mission(mission_id)
            if m is None:
                continue
            total = sum(max(1.0, float(getattr(o, "target", 1) or 1)) for o in m.objectives)
            done = sum(min(max(1.0, float(getattr(o, "target", 1) or 1)), float(getattr(o, "progress", 0) or 0))
                       for o in m.objectives)
            left = max(0.0, total - done)
            finished = m.status == "completed" or (total and left <= 0)
            pct = 0.0 if finished else (round(100 * left / total, 1) if total else 100.0)
            key = f"mission:{mission_id}"
            if finished:
                fallen[key] = (book.defeated.get(key)) or today.isoformat()
            out.append({"key": key, "kind": "mission", "id": mission_id, "name": m.name, "icon": m.icon or "⚔",
                        "hp": f"{left:g}", "max_hp": f"{total:g}", "percent": pct, "phase": phase(pct),
                        "damage": f"{done:g} of {total:g} done", "heal": "", "hit": "", "hits_left": None,
                        "defeated": bool(finished), "defeated_on": fallen.get(key, ""),
                        "reward": f"+{m.reward_xp} XP" if getattr(m, "reward_xp", 0) else "", "action": None})
    if book is not None:
        book.see(peaks, fallen)
    active = sorted((b for b in out if not b["defeated"]), key=lambda b: b["percent"])
    hall = sorted((b for b in out if b["defeated"]), key=lambda b: b["defeated_on"], reverse=True)
    eligible = []
    if missions is not None:
        taken = set(book.missions) if book is not None else set()
        eligible = [{"id": m.mission_id, "name": m.name} for m in missions.all_missions()
                    if m.status == "active" and m.mission_id not in taken and m.objectives]
    return {"active": active, "defeated": hall, "missions_to_pick": eligible}
