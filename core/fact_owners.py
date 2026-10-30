"""
core.fact_owners
===================

One owner per fact (DEC-0052, docs/REASONING_PLAN.md section 2). A fact
MIA knows about a person lives in exactly one store; every other screen,
answer and finding reads it from that owner and never keeps a copy, so
two places can't disagree. `tests/test_fact_owners.py` fails when a
retired copy comes back.

- **OWNERS**: the fact, the store that owns it, and where to read it.
- **RETIRED**: copies that used to exist, and the only files still
  allowed to name them (the one-time move that carries an old value to
  the owner, and the settings list it's read from).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Owner:
    fact: str
    store: str  # the module that owns it
    read: str  # the function (or field) everything else reads it through


OWNERS: tuple[Owner, ...] = (
    Owner("pay: rate, shift, overtime, take-home share", "core/work_dungeon.py",
          "core.web_dungeon.job_pay()"),
    Owner("when things happen in the week: work, training, chores", "core/the_loop.py",
          "core.the_loop.training_rhythm() / LoopBook.find()"),
    Owner("what each training day is", "core/fitness_manager.py", "FitnessManager.plan['training']['rotation']"),
    Owner("repeating chores and habits", "core/recurring_mission_manager.py",
          "the recurring missions (the calendar derives them: core.calendar_view._chores)"),
    Owner("money in and out", "core/budget_manager.py", "BudgetManager (and the bank sync)"),
)

# retired copy -> the files still allowed to name it
RETIRED: dict[str, tuple[str, ...]] = {
    "freedom.hourly": ("core/freedom.py", "core/person_settings.py", "core/fact_owners.py"),
    "freedom.shift_hours": ("core/freedom.py", "core/person_settings.py", "core/fact_owners.py"),
}
