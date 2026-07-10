"""
tests.test_event_bus
======================

Unit tests for core.event_bus.EventBus.
"""

from __future__ import annotations

from core.event_bus import EventBus


def test_subscriber_receives_published_event():
    bus = EventBus()
    received = {}

    def handler(**kwargs):
        received.update(kwargs)

    bus.subscribe("test.event", handler)
    bus.publish("test.event", value=42)

    assert received == {"value": 42}


def test_unsubscribed_callback_is_not_called():
    bus = EventBus()
    calls = []

    def handler(**kwargs):
        calls.append(kwargs)

    bus.subscribe("test.event", handler)
    bus.unsubscribe("test.event", handler)
    bus.publish("test.event")

    assert calls == []


def test_one_broken_subscriber_does_not_block_others():
    bus = EventBus()
    calls = []

    def broken_handler(**kwargs):
        raise RuntimeError("boom")

    def good_handler(**kwargs):
        calls.append(kwargs)

    bus.subscribe("test.event", broken_handler)
    bus.subscribe("test.event", good_handler)
    bus.publish("test.event", value=1)

    assert calls == [{"value": 1}]


def test_publish_with_no_subscribers_does_not_raise():
    bus = EventBus()
    bus.publish("nobody.listening")
