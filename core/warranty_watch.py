"""
core.warranty_watch
======================

A heads-up before a warranty runs out (2026-09-28). Machines got a
"Warranty until" date (MaintenanceAsset.warranty_until), typed in or
filled from a filed warranty/manual (core/inbox_classify.py). About a
month before, and again a week before, MIA mentions it through the
communication gate, so anything that's been acting up can be looked at
while it's still covered. Each stage is said once per item and date
(remembered in config `system.warranty_notices`).
"""

from __future__ import annotations

from datetime import date
from typing import Optional

STAGES = ((7, "week"), (30, "month"))  # checked nearest first


def warranty_stage(warranty_until: str, today: date) -> Optional[tuple[str, int]]:
    """Pure logic. ("week"|"month", days left) when a heads-up is due;
    None when there's no date, it's far off, or it already ended."""
    try:
        ends = date.fromisoformat(warranty_until)
    except (TypeError, ValueError):
        return None
    days_left = (ends - today).days
    if days_left < 0:
        return None
    for limit, stage in STAGES:
        if days_left <= limit:
            return stage, days_left
    return None


def warranty_message(name: str, warranty_until: str, days_left: int) -> str:
    """Pure logic."""
    ends = date.fromisoformat(warranty_until)
    when = "today" if days_left == 0 else "tomorrow" if days_left == 1 else f"in {days_left} days"
    return (f"The {name}'s warranty ends {ends:%b} {ends.day} ({when}). If anything's been acting up, now's the time "
            "to get it looked at while it's covered.")


def due_notices(assets, today: date, already: dict) -> list[tuple[object, str, int]]:
    """Pure logic. (asset, stage, days left) not yet said. `already`:
    {asset_id: "<warranty_until>|<stage>", ...} of what was said."""
    notices = []
    for asset in assets:
        until = getattr(asset, "warranty_until", "") or ""
        found = warranty_stage(until, today)
        if found is None:
            continue
        stage, days_left = found
        said = set(str(already.get(asset.asset_id, "")).split(","))
        if f"{until}|{stage}" in said:
            continue
        notices.append((asset, stage, days_left))
    return notices
