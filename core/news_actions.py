"""
core.news_actions
===================

Good News Radio's buttons (core/good_news.py), so the radio is fully used
without voice as well as with it (Zac, 2026-11-10; DEC-0125). Its page
(web/news.html) turns it on and off, starts today's episode, follows a
story or stops, and marks one misleading, each through one of these
actions, and each does exactly what the words do ("turn on good news
radio", "follow the story about the reef", "the story about the reef
was misleading": `good_news.reply`).

Every rule lives in core/good_news.py; this only turns its ValueErrors
into the ActionError a screen shows. What an action writes goes through
the atomic write, so on, off, follow, stop and mark each have an exact
Undo; starting an episode has none (it reads the feeds in a process of
its own).
"""

from __future__ import annotations

from core import good_news
from core.actions import ACTION_TYPES, ActionError, ActionType


def _story(context, params) -> dict:
    """The story of the latest episode an action names by `story_id`, or ActionError."""
    story = good_news._story(good_news.latest(), str(params.get("story_id") or ""))
    if story is None:
        raise ActionError("That story isn't in the latest episode anymore.")
    return story


def _followed(context, params) -> dict:
    """The followed story an action names by `story_id`, or ActionError."""
    sid = str(params.get("story_id") or "")
    found = next((f for f in good_news.following(context) if f["id"] == sid), None)
    if found is None:
        raise ActionError("You aren't following that story.")
    return found


def _needs_on(context) -> None:
    """ActionError when Good News Radio is off for this person (its stories aren't theirs to follow or mark yet)."""
    if not good_news.is_on(context):
        raise ActionError("Good News Radio is off. Turn it on first.")


def _describe_on(context, params) -> str:
    """The sentence for news.turn_on."""
    if good_news.is_on(context):
        raise ActionError("Good News Radio is already on.")
    return "Turn Good News Radio on"


def _turn_on(context, params) -> str:
    """Does news.turn_on: the same switch as "turn on good news radio"."""
    from core import person_settings

    _describe_on(context, params)
    person_settings.put(context, good_news.SETTING, True)
    return "Good News Radio is on. It reads its public feeds once a day; nothing about you is sent."


def _describe_off(context, params) -> str:
    """The sentence for news.turn_off."""
    if not good_news.is_on(context):
        raise ActionError("Good News Radio is already off.")
    return "Turn Good News Radio off"


def _turn_off(context, params) -> str:
    """Does news.turn_off: the same switch as "turn off good news radio"."""
    from core import person_settings

    _describe_off(context, params)
    person_settings.put(context, good_news.SETTING, False)
    return "Good News Radio is off. The feeds aren't read again until it's turned back on."


def _describe_make(context, params) -> str:
    """The sentence for news.make, or why today's episode can't be started (`good_news.can_make`)."""
    why = good_news.can_make(context)
    if why:
        raise ActionError(why)
    return "Start making today's episode"


def _make(context, params) -> str:
    """Does news.make: starts today's episode now, as "make today's good news" does."""
    try:
        return good_news.start_making(context)
    except ValueError as problem:
        raise ActionError(str(problem)) from problem


def _describe_follow(context, params) -> str:
    """The sentence for news.follow."""
    _needs_on(context)
    story = _story(context, params)
    if any(f["id"] == good_news.story_id(story) for f in good_news.following(context)):
        raise ActionError("You're already following that story.")
    return f"Follow \"{story['title']}\""


def _follow(context, params) -> str:
    """Does news.follow: later reports on the story are kept for the page each day the feeds are read."""
    _describe_follow(context, params)
    try:
        kept = good_news.follow(context, str(params.get("story_id") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from problem
    return f"Following \"{kept['title']}\"."


def _describe_unfollow(context, params) -> str:
    """The sentence for news.unfollow."""
    return f"Stop following \"{_followed(context, params)['title']}\""


def _unfollow(context, params) -> str:
    """Does news.unfollow: the story and the reports kept for it are dropped (Undo brings them back)."""
    found = _followed(context, params)
    try:
        good_news.unfollow(context, found["id"])
    except ValueError as problem:
        raise ActionError(str(problem)) from problem
    return f"Stopped following \"{found['title']}\"."


def _describe_misleading(context, params) -> str:
    """The sentence for news.misleading."""
    _needs_on(context)
    story = _story(context, params)
    record = good_news.latest()
    if good_news.story_id(story) in good_news.flagged_ids(context, record["day"]):
        raise ActionError("You already marked that story misleading.")
    return f"Mark \"{story['title']}\" misleading"


def _misleading(context, params) -> str:
    """Does news.misleading: the story's outlet is weighed down, and dropped if it keeps happening."""
    _describe_misleading(context, params)
    try:
        story = good_news.flag(context, str(params.get("story_id") or ""))
    except ValueError as problem:
        raise ActionError(str(problem)) from problem
    return f"Marked \"{story['title']}\" misleading. Its source is weighed down."


STORY = {"story_id": "the story, by its id on the page"}
ACTION_TYPES["news.turn_on"] = ActionType("news.turn_on", "Turn it on", {}, _describe_on, _turn_on)
ACTION_TYPES["news.turn_off"] = ActionType("news.turn_off", "Turn it off", {}, _describe_off, _turn_off)
ACTION_TYPES["news.make"] = ActionType("news.make", "Make today's episode", {}, _describe_make, _make)
ACTION_TYPES["news.follow"] = ActionType("news.follow", "Follow", dict(STORY), _describe_follow, _follow)
ACTION_TYPES["news.unfollow"] = ActionType("news.unfollow", "Stop following", dict(STORY), _describe_unfollow,
                                           _unfollow)
ACTION_TYPES["news.misleading"] = ActionType("news.misleading", "This was misleading", dict(STORY),
                                             _describe_misleading, _misleading)
