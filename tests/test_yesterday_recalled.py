"""
tests.test_yesterday_recalled
===============================

"What did I tell you yesterday?" (brainstorm round 15, 2026-11-25): yesterday's kept conversations, summarised, never
only their titles; a day with nothing kept says so; no day named lists the newest as before.
"""

from datetime import datetime, timedelta
from types import SimpleNamespace

from core import assistant_screen_tools as tools


def _conversation(when, said):
    """A kept conversation of one exchange at a time."""
    at = when.isoformat(timespec="seconds")
    return SimpleNamespace(conversation_id="c" + at, title="Goats", created_at=at, updated_at=at, off_record=False,
                           messages=[SimpleNamespace(role="user", content=said, timestamp=at, private=False),
                                     SimpleNamespace(role="assistant", content="Alpines are good milkers.",
                                                     timestamp=at, private=False)])


def test_yesterdays_conversations_are_summarised(monkeypatch):
    from core import conversation_export

    yesterday = datetime.now() - timedelta(days=1)
    convs = [_conversation(yesterday, "which goats are best for milk?"), _conversation(datetime.now(), "hello")]
    context = SimpleNamespace(conversations=SimpleNamespace(all_conversations=lambda: convs), llm=None)
    monkeypatch.setattr(conversation_export, "kept", lambda c: c.messages)
    said = tools._past(context, {"question": "do you remember what I told you yesterday?"})
    assert said.startswith(f"From {yesterday.date().isoformat()}:") and "which goats are best for milk?" in said
    assert "hello" not in said
    context.conversations = SimpleNamespace(all_conversations=lambda: [convs[1]])
    assert tools._past(context, {"question": "what did we talk about yesterday"}).startswith("Nothing's kept from")
