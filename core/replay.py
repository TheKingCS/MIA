"""
core.replay
===========

A replayed week (LS-09, docs/mia_os/MIA_LIVING_SYSTEM_GAP_ANALYSIS.md section 5): MIA's once-a-day checks run on each
day of a week with the one clock (core/clock.py) held at that day's hour, and what she said each day is read back from
her communication gate's log. A test seeds a week of things (events, bills, a stop) and checks that every due item is
said on its day, nothing twice, and the stop holds what it should.

`replay(context, jobs, start, days, hour)` returns one entry per day, {day, said: [titles and messages]}. It never
reaches outside: the checks offer through the gate as they always do, and the gate's log is what's read.
"""

from __future__ import annotations

from datetime import datetime, timedelta

# Left out of a replay: her own background work, which launches programs or reaches outside (core/homeostasis.py's
# deferrable checks), and the nightly backup. A replay is about what she says and when.
SKIPPED = frozenset(__import__("core.homeostasis", fromlist=["DEFERRABLE_CHECKS"]).DEFERRABLE_CHECKS) | {"auto_backup"}


def replay(context, jobs, start: datetime, days: int = 7, hour: int = 9, before_each=None) -> list[dict]:
    """Runs `jobs._check_daily_occasions()` once on each of `days` days from `start`, at `hour`, with the clock held
    there, leaving out `SKIPPED`; `before_each(day)` runs first on each day (a test's events: a stop said, a carry
    on). Returns
    [{day, said: [str]}], what her gate sent that day."""
    from core import clock

    out = []
    gate = getattr(context, "communication", None)
    for offset in range(days):
        moment = (start + timedelta(days=offset)).replace(hour=hour, minute=0, second=0, microsecond=0)
        with clock.frozen(moment):
            if before_each is not None:
                before_each(moment.date())
            jobs._check_daily_occasions(skip=SKIPPED)
        day = moment.date().isoformat()
        said = []
        if gate is not None:
            from core.communication_gate import ACT

            said = [f"{e.get('title', '')}: {e.get('message', '')}" for e in gate.entries_for_day(day)
                    if e.get("action") == ACT]
        out.append({"day": day, "said": said})
    return out
