"""
core.environment
==================

The real-vs-fictional boundary (DEC-0137): *shared intelligence, not shared authority.* MIA reuses the same primitives
— entities, events, goals, progression — across real domains (missions, the garage, the homestead) and fictional ones
(Living Worlds). This module is the one guarantee that keeps their **authority** separate, so a fictional achievement
never becomes a real one and a simulated outcome never becomes a recorded fact.

Every record that could be confused across domains carries an `environment`:

- **real** — the person's actual life. Only real state may be committed to a real store or earn real XP.
- **fictional** — a Living Worlds campaign. Its quests, XP and events live in its own store and are tagged fictional.
- **simulated** — a what-if/scenario outcome. It is never committed as real except by the person approving a real
  action through `core/actions.py`.

`require_real` is the enforcer: a real-authority sink calls it, and a fictional or simulated write raises `DomainLeak`
instead of silently crossing the boundary. Pure, dependency-free, so anything (life_events, rewards, a store) can guard
itself without a cycle.
"""

from __future__ import annotations

REAL = "real"
FICTIONAL = "fictional"
SIMULATED = "simulated"
ENVIRONMENTS = (REAL, FICTIONAL, SIMULATED)


class DomainLeak(RuntimeError):
    """Raised when fictional or simulated state tries to reach a real-authority sink (a real store, the real XP
    ledger, a real action). The boundary MIA must never silently cross (DEC-0137 §7)."""


def normalize(environment) -> str:
    """A clean environment string: one of ENVIRONMENTS, defaulting to 'real' for None or anything unknown (so a caller
    that says nothing is treated as real, never as fiction by accident)."""
    return environment if environment in ENVIRONMENTS else REAL


def is_real(environment) -> bool:
    """Whether this is the person's actual life (the only state that may be committed as real)."""
    return normalize(environment) == REAL


def require_real(environment, what: str = "this change") -> None:
    """Guard a real-authority sink: do nothing when the environment is real, else raise DomainLeak. A real store, the
    real XP ledger or a real action calls this so fictional or simulated state can never be committed as real."""
    if not is_real(environment):
        raise DomainLeak(f"{what} is {normalize(environment)!r}, not real — it may not be committed to real state.")
