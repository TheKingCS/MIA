"""
core.event_bus
===============

A minimal publish/subscribe event bus.

Why this exists: as M.I.A. grows, modules will need to react to things
happening elsewhere in the system (e.g. the "Notes" module wants to know
when the "Assistant" module creates a reminder) without importing each
other directly. Direct imports between modules create a tangled
dependency graph that becomes unmaintainable over a multi-year project.

The event bus is intentionally simple (no priorities, no async, no
threading guarantees) because M.I.A. v0.1 is a single-threaded desktop
GUI app. If a future version needs cross-thread or cross-process events
(e.g. a background robotics/networking daemon), that's a good moment to
revisit this module — but don't add that complexity now.

Usage
-----
    bus.subscribe("user.setup_complete", my_callback)
    bus.publish("user.setup_complete", name="Alex")
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from core.logger import get_logger

log = get_logger(__name__)


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event_name: str, callback: Callable[..., None]) -> None:
        """Register `callback` to be called whenever `event_name` is published."""
        self._subscribers[event_name].append(callback)
        log.debug("Subscribed %s to event '%s'", getattr(callback, "__qualname__", callback), event_name)

    def unsubscribe(self, event_name: str, callback: Callable[..., None]) -> None:
        """Remove a previously registered callback. Safe to call if not present."""
        if callback in self._subscribers.get(event_name, []):
            self._subscribers[event_name].remove(callback)

    def publish(self, event_name: str, **kwargs: Any) -> None:
        """
        Publish an event to all subscribers. Exceptions in one subscriber
        are logged but do not prevent other subscribers from running —
        one broken module should never be able to crash the whole system.
        """
        log.debug("Publishing event '%s' with data: %s", event_name, kwargs)
        for callback in list(self._subscribers.get(event_name, [])):
            try:
                callback(**kwargs)
            except Exception:
                log.exception("Error in subscriber for event '%s'", event_name)
