"""
core.main_thread
===================

Publishing events safely from background threads (2026-09-28).

The event bus is synchronous and not thread-safe on purpose (see
core/event_bus.py). But the phone server runs on its own thread, and
when a phone turn changes records ("add milk to the grocery list"), open
desktop screens should update. Their subscribers touch Qt widgets, which
must only happen on the main (GUI) thread, or Qt crashes.

`publish(context, event, **kwargs)` publishes directly when called on
the main thread, and otherwise hands the publish to the main thread
through `context.main_thread_call`, which core/application.py sets to a
Qt queued call. Without one (tests, the headless voice loop with no
screens) it publishes directly.
"""

from __future__ import annotations

import threading


def publish(context, event_name: str, **kwargs) -> None:
    events = getattr(context, "events", None)
    if events is None:
        return
    call = getattr(context, "main_thread_call", None)
    if call is None or threading.current_thread() is threading.main_thread():
        events.publish(event_name, **kwargs)
    else:
        call(lambda: events.publish(event_name, **kwargs))


# Tools that only read: running them changes nothing on screen.
_READ_ONLY_PREFIXES = ("get_", "list_", "search_", "check_", "what_", "find_", "read_", "show_", "describe_")


def changes_records(action_name: str) -> bool:
    return not action_name.startswith(_READ_ONLY_PREFIXES)


def records_changed(context, action_name: str) -> None:
    """After an Assistant tool ran: tell open screens to re-read their data."""
    if changes_records(action_name):
        publish(context, "records.changed", action=action_name)
