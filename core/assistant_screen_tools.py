"""
core.assistant_screen_tools
=============================

Voice tools for screens that had none (claude, 2026-11-09; DEC-0125: every feature works by voice and without it):

- **look_up_online** (Look It Up Online, DEC-0053, T-0017): the person asking to look something up IS the yes that
  core/online_lookup.OFFER waits for, so the tool searches their own SearXNG with the words scrubbed, and returns the
  results through `online_lookup.said()`: each with its source and date, marked as from the web (never instructions),
  never a legal or tax ruling. When it isn't allowed or the engine isn't running, it says why, in her words.
- **get_app_status** ("what isn't working?", "are any of your apps broken?"): core/capabilities.status_summary, so a
  planned app is never said as working and what broke is said as inferred. "What's not working" stays the setup
  check's (core/assistant_undo_actions.check_my_setup).
- **list_past_conversations** and **find_in_conversations** (the chat page's History): the conversations kept, newest
  first, and the ones whose kept messages mention some words. Off-the-record and private messages were never written,
  so they can't be found.
- **list_sensors** (the Sensors page, core/sensors.py): each sensor, where its readings go, the last one and when.
  Adding one stays on a screen: its key is shown once and never spoken.

Facts come from code; the model only phrases them.
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction


def _look_up(context, arguments: dict) -> str:
    """Tool look_up_online: searches the person's own search engine for their words (asked, so no offer first)."""
    from core import online_lookup

    words = str(arguments.get("words") or "").strip()
    if not words:
        return "What should I look up?"
    try:
        return online_lookup.said(online_lookup.search(context, words))
    except online_lookup.LookupUnavailable as why:
        return str(why)


def _app_status(context, arguments: dict) -> str:
    """Tool get_app_status: which of MIA's apps are working, partly working, unwell or only planned."""
    from core.capabilities import status_summary

    return status_summary(context)


def _past(context, arguments: dict) -> str:
    """Tool list_past_conversations: the newest kept conversations (five), each with when and how it began."""
    from core.web_conversations import history

    page = history(context)
    rows = page.get("conversations") or []
    if not page.get("available"):
        return "I don't keep conversations on this MIA."
    if not rows:
        return "No past conversations kept yet."
    said = "; ".join(f"{r['title'] or 'Untitled'} ({r['when'][:10]}, {r['count']} messages)" for r in rows[:5])
    return f"{page.get('total', len(rows))} kept. The newest: {said}. They're on the chat page's History too."


def _find(context, arguments: dict) -> str:
    """Tool find_in_conversations: the kept conversations whose messages mention all the words (five at most), each
    with the line that matched."""
    manager = getattr(context, "conversations", None)
    words = [w for w in str(arguments.get("words") or "").lower().split() if len(w) > 2]
    if manager is None:
        return "I don't keep conversations on this MIA."
    if not words:
        return "What should I look for in our conversations?"
    hits = []
    for c in manager.all_conversations():
        line = next((m.content for m in c.messages if m.role in ("user", "assistant")
                     and all(w in m.content.lower() for w in words)), None)
        if line is not None:
            hits.append(f"{c.title or 'Untitled'} ({(c.updated_at or c.created_at or '')[:10]}): “{line[:140]}”")
    if not hits:
        return f"I didn't find “{' '.join(words)}” in our kept conversations (private and off-the-record ones aren't kept)."
    return f"{len(hits)} conversation{'s' if len(hits) != 1 else ''}: " + "; ".join(hits[:5]) + "."


def _sensors(context, arguments: dict) -> str:
    """Tool list_sensors: the person's sensors, where each sends its readings, and its last reading and when."""
    from core.person_settings import person_id
    from core.sensors import target_words

    store = getattr(context, "sensors", None)
    if store is None:
        return "Sensors aren't on this MIA."
    mine = store.mine(person_id(context) or "")
    if not mine:
        return "No sensors yet. Add one on the Sensors page (Settings and Diagnostics)."
    return "; ".join(f"{s['name']} → {target_words(s)}: " + (f"{s['last_value']:g} at {s['last_at'][11:16]} on {s['last_at'][:10]}"
                                                         if s.get("last_at") else "no readings yet") for s in mine) + "."


def register_screen_tools(registry) -> None:
    """Registers look_up_online, get_app_status, list_past_conversations, find_in_conversations and list_sensors."""
    registry.register(AssistantAction(
        name="look_up_online", domain="system",
        description=("Look something up online through the person's own search engine, when they ask you to search "
                     "the web or look something up. Their records never leave; say each fact with its source."),
        parameters={"type": "object", "properties": {
            "words": {"type": "string", "description": "What to search for, in the person's words."}},
            "required": ["words"]},
        handler=_look_up, prompt_arg="words",
        trigger_phrases=("look it up online", "look that up online", "look up online", "search online", "search the web",
                         "search the internet", "look online for", "google it", "google that", "find online",
                         "look it up on the internet", "search for it online"),
        subjects=("online", "web", "internet"),
    ))
    registry.register(AssistantAction(
        name="get_app_status", domain="system",
        description=("Which of MIA's apps are fully working, partly working, unwell from what broke this week, or only "
                     "planned. From her own capability list, never from memory."),
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_app_status,
        trigger_phrases=("what isn't working", "what is not working right", "what's broken", "what is broken",
                         "anything broken", "are any of your apps broken", "which apps work", "what apps are working",
                         "which of your apps", "is everything working", "are you working properly"),
        subjects=("you", "mia", "apps"),
    ))
    registry.register(AssistantAction(
        name="list_past_conversations", domain="system",
        description="The person's past conversations with MIA that were kept, newest first.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_past,
        trigger_phrases=("past conversations", "our conversations", "previous conversations", "chat history",
                         "conversation history", "what have we talked about", "what did we talk about"),
        subjects=("conversation", "conversations", "chat", "chats"),
    ))
    registry.register(AssistantAction(
        name="find_in_conversations", domain="system",
        description="Find the kept past conversations that mention some words, with the line that mentions them.",
        parameters={"type": "object", "properties": {
            "words": {"type": "string", "description": "What to look for, in the person's words."}},
            "required": ["words"]},
        handler=_find, prompt_arg="words",
        trigger_phrases=("when did we talk about", "when did i tell you about", "find where we talked about",
                         "did we talk about", "find in our conversations", "search our conversations",
                         "search my chats"),
        subjects=("conversation", "conversations", "chat", "talked"),
    ))
    registry.register(AssistantAction(
        name="list_sensors", domain="system",
        description="The person's sensors that send their own readings: where each one's go, and its last reading and when.",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=_sensors,
        trigger_phrases=("my sensors", "what sensors", "which sensors", "sensor readings", "is my sensor",
                         "is the probe", "last sensor reading"),
        subjects=("sensor", "sensors", "probe"),
    ))
