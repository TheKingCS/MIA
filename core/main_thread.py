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
    """Publishes an event on the main (Qt) thread: directly when already there or with no hand-off available, else handed over through context.main_thread_call, since the event bus isn't thread-safe and subscribers touch widgets."""
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
# Tools whose name reads like a lookup but that change records (2026-11-10, found by scanning every lookup-named
# tool's handler): they record an undo and refresh screens like any change. tests/test_tool_gate.py keeps this right.
CHANGES_DESPITE_NAME = frozenset({"check_off_grocery_item"})


def changes_records(action_name: str) -> bool:
    """Pure logic. Whether a tool may change records: every tool except the read-only ones (get_, list_, search_,
    show_...), and those that only look like one (CHANGES_DESPITE_NAME) do."""
    return action_name in CHANGES_DESPITE_NAME or not action_name.startswith(_READ_ONLY_PREFIXES)


def records_changed(context, action_name: str) -> None:
    """After an Assistant tool ran: tell open screens to re-read their data."""
    if changes_records(action_name):
        publish(context, "records.changed", action=action_name)
