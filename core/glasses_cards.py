"""
core.glasses_cards
====================

Glasses cards for the apps that only had an ask (Zac, 2026-11-08: "build out the glasses screens as much as
possible"; DEC-0125 full use on every device). Each app's quick action menu gains a readout panel or two, built here
from the same page assembler its web screen uses (never a second copy of the logic), in core/glasses.py's panel shape:
a title, at most five short lines (text, detail, tone) and what to say when it's empty. The app's asks stay after its
panels, so MIA still answers anything the card doesn't show.

What these cards may change is still core/glasses.GLASSES_KINDS: here only "Done" on an open promise
(`life_note.done`, undoable), and starting and moving a Trade Master job along (`trade.start`, `trade.next`, `trade.check`,
`trade.back`, `trade.answer`, `trade.stop`: the hold points are enforced in core/trade_session.py). Everything else is a readout: no money moves, no camera settings, no browser steps (a
browser commit is approved by a person on a bigger screen, DEC-0117), no compliance marked filed.

How: `PANELS` maps an app id to its menu entries (item id, label, builder), merged into core/glasses.PANELS at import;
each builder is `(context, today) -> panel` and never raises (a store that isn't here gives the panel's empty line).
Money is formatted by the page assemblers (core.region.money); tones are "attention" for what needs the person and
"bad" only for something broken.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Callable

from core.logger import get_logger

log = get_logger(__name__)


def _line(text: str, detail: str = "", tone: str = "", action=None) -> dict:
    """core/glasses._line (imported when called: core/glasses imports this module at its end)."""
    from core.glasses import _line as line

    return line(text, detail, tone, action)


def _panel(title: str, lines: list, empty: str, more: int = 0) -> dict:
    """core/glasses._panel (imported when called, like _line)."""
    from core.glasses import _panel as panel

    return panel(title, lines, empty, more)


def _page(title: str, read: Callable[[], dict], empty: str):
    """The page an assembler returns, or (None, the panel to show instead) when it isn't available or fails."""
    try:
        page = read()
    except Exception:  # noqa: BLE001 - a card that can't be read says so; the glasses keep going
        log.exception("Glasses: %s couldn't be read", title)
        return None, _panel(title, [], "That couldn't be read just now.")
    if not isinstance(page, dict) or page.get("available") is False:
        return None, _panel(title, [], empty)
    return page, None


def _days_word(days) -> str:
    """Pure logic. A due date's distance in words: "today", "in 3 days", "4 days late"."""
    if days is None:
        return ""
    days = int(days)
    if days == 0:
        return "today"
    if days < 0:
        return f"{-days} day{'s' if days != -1 else ''} late"
    return "tomorrow" if days == 1 else f"in {days} days"


def _split(text: str, room: int = 44) -> tuple[str, str]:
    """Pure logic. A long sentence as a glasses line: (the head, the rest as its detail), split at a dash, semicolon,
    comma or question mark that falls within `room` characters, else at the last word that fits; short text stays
    whole."""
    text = " ".join(str(text or "").split())
    if len(text) <= room:
        return text, ""
    for mark in (" — ", "; ", "? ", ", ", ": "):
        at = text.find(mark)
        if 0 < at <= room:
            cut = at + (1 if mark in ("? ",) else 0)
            return text[:cut].rstrip(" ,;:"), text[at + len(mark):]
    at = text.rfind(" ", 0, room + 1)  # no mark near the start: break at the last word that fits
    return (text[:at], text[at + 1:]) if at > room // 2 else (text, "")


# ------------------------------------------------------------ the Dungeon (paid work as a game)

def _dungeon_week(context, today: date):
    """Panel: this week's loot so far, the projection, what's banked, and each dungeon's shift today."""
    from core.web_dungeon import dungeon_page

    page, none = _page("This Week", lambda: dungeon_page(context, today), "Set up your job in the Dungeon first.")
    if none:
        return none
    s = page.get("summary") or {}
    lines = [_line(f"{s.get('week_text', '')} so far", f"on pace for {s.get('projected_text', '')}"),
             _line(f"{s.get('banked_text', '')} banked", "toward Freedom")]
    for d in page.get("dungeons") or []:
        t = d.get("today") or {}
        if t.get("hours"):
            lines.append(_line(d["name"], f"today {t['hours']:g} h · {t.get('loot_text', '')} · {t.get('status', '')}"))
    nxt = page.get("next_dungeon") or {}
    if nxt.get("line"):
        lines.append(_line("Next dungeon", nxt["line"]))
    return _panel("This Week", lines, "No shifts yet this week.")


# ------------------------------------------------------------ the Fix-It Log

def _issues_open(context, today: date):
    """Panel: what's still broken in MIA, heaviest first, with how often and when last."""
    from core.failure_actions import failures_page

    page, none = _page("Open Issues", lambda: failures_page(context), "The Fix-It Log isn't on this MIA.")
    if none:
        return none
    s = page.get("summary") or {}
    open_ = [i for i in page.get("issues") or [] if i.get("status") == "open"]
    lines = [_line(i["title"], f"{i['count']}× · last {str(i.get('last', ''))[:10]}", "bad") for i in open_]
    if s.get("fixed"):
        lines.append(_line(f"{s['fixed']} fixed lately", f"{s.get('learned', 0)} new phrases learned"))
    return _panel("Open Issues", lines, "Nothing broken right now.")


# ------------------------------------------------------------ Compliance

def _compliance_due(context, today: date):
    """Panel: deadlines overdue, then soon, each with when and who it's owed to; unverified ones said so."""
    from core.web_compliance import compliance_page

    page, none = _page("Deadlines", lambda: compliance_page(context, today), "Compliance isn't on this MIA.")
    if none:
        return none
    groups = page.get("groups") or {}
    lines = []
    for where in ("overdue", "soon"):
        for o in groups.get(where) or []:
            detail = " · ".join(b for b in (o.get("authority", ""), _days_word(o.get("days")),
                                            "" if o.get("verified") else "date not checked") if b)
            lines.append(_line(o["title"], detail, "attention"))
    more = len(groups.get("later") or [])
    return _panel("Deadlines", lines, "Nothing due soon.", more=more)


# ------------------------------------------------------------ the Flock

def _flock_today(context, today: date):
    """Panel: eggs today and this week across the flocks, each flock's lay rate, and eggs not yet used."""
    from core.web_flock import flock_page

    page, none = _page("Eggs", lambda: flock_page(context, today), "Add your flock in the Flock app first.")
    if none:
        return none
    t = page.get("total") or {}
    lines = [_line(f"{t.get('today', 0):g} eggs today", f"{t.get('week', 0):g} this week · {t.get('hens', 0)} hens")]
    for f in page.get("flocks") or []:
        fig = f.get("figures") or {}
        lines.append(_line(f["name"], f"{fig.get('today', 0):g} today · lays {fig.get('lay_rate_text', '')}"
                                      f" · feed {fig.get('feed_per_dozen_text', '')}/dozen"))
    if t.get("loose"):
        lines.append(_line(f"{t['loose']:g} eggs on hand", "not yet sold or used"))
    return _panel("Eggs", lines, "No flock yet.")


# ------------------------------------------------------------ Business (orders and quotes)

def _business_orders(context, today: date):
    """Panel: open orders, overdue first, with the customer, the stage, when due and what's still owed."""
    from core.web_business import business_page

    page, none = _page("Open Orders", lambda: business_page(context, today), "The business isn't set up here.")
    if none:
        return none
    orders = sorted((o for o in page.get("orders") or [] if o.get("open")),
                    key=lambda o: (not o.get("overdue"), o.get("due") or "9999"))
    lines = [_line(o["title"], " · ".join(b for b in (o.get("customer", ""), o.get("status", ""),
                                                       f"due {o['due']}" if o.get("due") else "",
                                                       f"{o['left']} owed" if o.get("left_value") else "") if b),
                   "attention" if o.get("overdue") else "") for o in orders]
    return _panel("Open Orders", lines, "No open orders.")


def _business_quotes(context, today: date):
    """Panel: quotes still open, with the customer, the price and how long the quote holds."""
    from core.web_business import business_page

    page, none = _page("Open Quotes", lambda: business_page(context, today), "The business isn't set up here.")
    if none:
        return none
    lines = [_line(q["title"], " · ".join(b for b in (q.get("customer", ""), q.get("price", ""),
                                                       f"good until {q['valid_until']}" if q.get("valid_until") else "")
                                          if b))
             for q in page.get("quotes") or [] if q.get("open")]
    return _panel("Open Quotes", lines, "No open quotes.")


# ------------------------------------------------------------ Insurance

def _insurance_renewals(context, today: date):
    """Panel: each policy by renewal date, with the insurer and what it costs a year; what she could save."""
    from core.insurance import insurance_page
    from core.region import money

    page, none = _page("Renewals", lambda: insurance_page(context, today), "Insurance isn't on this MIA.")
    if none:
        return none
    lines = []
    for p in sorted(page.get("policies") or [], key=lambda p: p.get("renews") or "9999"):
        days = None
        try:
            days = (date.fromisoformat(p["renews"]) - today).days if p.get("renews") else None
        except ValueError:
            pass
        lines.append(_line(p.get("name") or p.get("kind", "Policy"),
                           " · ".join(b for b in (p.get("insurer", ""), f"renews {_days_word(days)}" if days is not None
                                                  else "", f"{money(p.get('per_year') or 0)} a year") if b),
                           "attention" if days is not None and days <= 30 else ""))
    s = page.get("summary") or {}
    if s.get("could_save"):
        lines.append(_line(f"Could save {money(s['could_save'])} a year", "from the quotes you've kept"))
    return _panel("Renewals", lines, "No policies saved yet.")


# ------------------------------------------------------------ Security cameras

def _security_cameras(context, today: date):
    """Panel: each camera, where it is and whether it's answering (a problem is broken, so it's red)."""
    from core.security_cams import security_page

    page, none = _page("Cameras", lambda: security_page(context), "No cameras set up yet.")
    if none:
        return none
    def where(c) -> str:
        """The camera's place when its name doesn't already say it."""
        loc = c.get("location") or ""
        return f"{loc} · " if loc and loc.lower() != str(c.get("name", "")).lower() else ""

    lines = [_line(c["name"], c["problem"] if c.get("problem") else where(c) + "working", "bad" if c.get("problem") else "")
             for c in page.get("cameras") or []]
    return _panel("Cameras", lines, "No cameras set up yet.")


# ------------------------------------------------------------ the Reward Shop

def _shop_rewards(context, today: date):
    """Panel: credits left, then the rewards you can buy now and how far off the rest are (buying is on the phone)."""
    from core.game_layer import shop_page

    page, none = _page("Rewards", lambda: shop_page(context), "The Reward Shop isn't on this MIA.")
    if none:
        return none
    c = page.get("credits") or {}
    rewards = sorted((r for r in page.get("rewards") or [] if r.get("available")),
                     key=lambda r: (not r.get("affordable"), r.get("to_go") or 0))
    lines = [_line(f"{c.get('left', 0)} credits", f"{c.get('earned', 0)} earned · {c.get('spent', 0)} spent")]
    lines += [_line(f"{r.get('icon', '')} {r['name']}".strip(),
                    f"{r['cost']} credits · " + ("ready" if r.get("affordable") else f"{r.get('to_go', 0)} to go"),
                    "attention" if r.get("affordable") else "") for r in rewards]
    return _panel("Rewards", lines, "No rewards in the shop yet.")


# ------------------------------------------------------------ the Memory Vault

def _vault_status(context, today: date):
    """Panel: what the vault is doing, how many photos and videos are kept, and what's waiting to copy."""
    from core.memory_vault import vault_page

    page, none = _page("Memory Vault", lambda: vault_page(context, today=today), "The Memory Vault isn't set up.")
    if none:
        return none
    s = page.get("summary") or {}
    lines = [_line(page.get("state_words") or ("On" if page.get("on") else "Off"), ""),
             _line(f"{s.get('photos', 0)} photos · {s.get('videos', 0)} videos", f"{s.get('size', '')} on the PC")]
    if s.get("waiting"):
        lines.append(_line(f"{s['waiting']} waiting to copy", s.get("waiting_size", ""), "attention"))
    free = page.get("free") or {}
    if free.get("count"):
        lines.append(_line(f"{free['count']} safe to free on the phone", free.get("size", "")))
    return _panel("Memory Vault", lines, "Nothing kept yet.")


# ------------------------------------------------------------ the Knowledge library

def _knowledge_packs(context, today: date):
    """Panel: the offline reference packs installed, with how many articles each holds."""
    library = getattr(context, "reference_library", None)
    if library is None:
        return _panel("Offline Library", [], "No offline packs installed yet.")
    try:
        packs = library.list_packs()
    except Exception:  # noqa: BLE001 - a library that can't be read shows none
        log.exception("Glasses: the offline library couldn't be read")
        packs = []
    lines = [_line(p.title, f"{p.article_count:,} articles") for p in packs]
    return _panel("Offline Library", lines, "No offline packs installed yet.")


# ------------------------------------------------------------ the Toolbox

def _toolbox_alarms(context, today: date):
    """Panel: the alarms, earliest first, with when they repeat and whether they're on."""
    from core.web_toolbox import _alarms

    alarms = _alarms(context)
    lines = [_line(f"{a['time']} {a['label']}".strip(), f"{a['repeat']} · {'on' if a['on'] else 'off'}")
             for a in alarms]
    return _panel("Alarms", lines, "No alarms set.")


# ------------------------------------------------------------ the Operating Journal

def _operating_how(context, today: date):
    """Panel: each line of how you said you want to live, with how it's going (under half is worth a look)."""
    from core.operating_journal import screen

    page, none = _page("How I'm Living", lambda: screen(context, today), "")
    if none:
        return none
    lines = []
    for o in page.get("lines") or []:
        score = o.get("score") or {}
        pct = score.get("pct")
        lines.append(_line(o["text"], score.get("text") or o.get("how", ""),
                           "attention" if isinstance(pct, (int, float)) and pct < 50 else ""))
    return _panel("How I'm Living", lines, "Nothing written yet. Say \"add a rule: ...\" to start.")


# ------------------------------------------------------------ Kept (promises, decisions, ideas)

_KIND_WORDS = re.compile(r"^(a promise|an idea|a decision|a goal set aside|a goal)( to)?\s*:?\s*", re.I)

def _kept(kind: str, title: str, empty: str, done_button: bool = False):
    """A builder for one kind of kept note: the open ones, newest first, due ones flagged; promises can be marked done."""
    def build(context, today: date):
        """Panel: the open notes of this kind, newest first (a promise past its date needs you)."""
        from core.life_notes import screen

        page, none = _page(title, lambda: screen(context), "")
        if none:
            return none
        group = next((g for g in page.get("kinds") or [] if g.get("kind") == kind), {"notes": []})
        lines = []
        for n in group["notes"]:
            if n.get("status") != "open":
                continue
            late = bool(n.get("due")) and n["due"] < today.isoformat()
            action = {"kind": "life_note.done", "label": "Done", "params": {"note_id": n["id"]}} if done_button else None
            text = _KIND_WORDS.sub("", n["line"]) or n["line"]  # the card says which kind; the line says what (and to whom)
            lines.append(_line(text[:1].upper() + text[1:], f"by {n['due']}" if n.get("due") else str(n.get("at", ""))[:10],
                               "attention" if late else "", action))
        return _panel(title, lines, empty)
    return build


# ------------------------------------------------------------ Play

def _play_week(context, today: date):
    """Panel: this week's play against your workouts, then the latest games with how hard they were."""
    from core.recreation import screen

    page, none = _page("Play", lambda: screen(context, today), "")
    if none:
        return none
    weeks = page.get("weeks") or []
    lines = []
    if weeks:
        w = weeks[-1]
        lines.append(_line(f"{w.get('play_minutes', 0)} min of play this week",
                           f"{w.get('played', 0)} games · {w.get('workouts', 0)} workouts"))
    lines += [_line(p["what"], f"{p.get('minutes', 0)} min · {p.get('effort_word', '')} · {p.get('date', '')}")
              for p in (page.get("played") or [])[:4]]
    return _panel("This Week", lines, "Nothing played yet. Say \"I played an hour of basketball\".")


# ------------------------------------------------------------ Good News

def _news_today(context, today: date):
    """Panel: today's good stories, each with how sure it is (one outlet only is worth knowing)."""
    from core.good_news import screen

    page, none = _page("Good News", lambda: screen(context), "")
    if none:
        return none
    if not page.get("on"):
        return _panel("Good News", [], "Good News Radio is off. Turn it on in the app.")
    lines = [_line(s["title"], " · ".join(b for b in (s.get("topic", ""), s.get("tag", "")) if b),
                   "attention" if s.get("tone") == "attention" else "") for s in page.get("stories") or []]
    return _panel("Today's Stories", lines, "No stories yet today.")


# ------------------------------------------------------------ Her browser

def _browser_waiting(context, today: date):
    """Panel: the steps her browser is waiting on you for (approve them on the phone or PC), then the tasks taught."""
    from core.web_browser import screen

    page, none = _page("Browser", lambda: screen(context), "Her browser isn't set up on this PC.")
    if none:
        return none
    lines = [_line(w["summary"], f"{w.get('site', '')} · approve on your phone or PC", "attention")
             for w in page.get("waiting") or []]
    lines += [_line(t["name"], t.get("state", "")) for t in page.get("tasks") or []]
    opened = page.get("open") or {}
    if opened.get("title") and not lines:
        lines.append(_line(f"On {opened['title']}", ""))
    return _panel("Waiting For You", lines, "Nothing waiting, and no tasks taught yet.")


# ------------------------------------------------------------ Diagnostics

def _diagnostics_health(context, today: date):
    """Panel: each check-up passed or what failed (a failure is broken), then the log's newest problems."""
    from core.diagnostics import screen

    page, none = _page("PC Health", lambda: screen(context), "")
    if none:
        return none
    if page.get("error"):
        return _panel("PC Health", [], page["error"])
    lines = [_line(c["title"], "all good" if c["ok"] else c["failed"][0], "" if c["ok"] else "bad")
             for c in page.get("checks") or []]
    problems = page.get("problems") or []
    if problems:
        lines.append(_line(f"{len(problems)} recent problem{'s' if len(problems) != 1 else ''} in her log",
                           problems[0].get("text", ""), "bad" if any(p.get("level") == "error" for p in problems) else ""))
    return _panel("PC Health", lines, "No check-ups ran.")


# ------------------------------------------------------------ Files

def _files_recent(context, today: date):
    """Panel: MIA's folder: its folders with how much is in each, then the newest files there."""
    from core.web_more import files_page

    page, none = _page("MIA Folder", lambda: files_page(context), "Files isn't set up on this PC.")
    if none:
        return none
    lines = [_line(f["name"] + "/", f"{f.get('count', 0)} items") for f in page.get("folders") or []]
    newest = sorted(page.get("files") or [], key=lambda f: str(f.get("modified") or ""), reverse=True)
    lines += [_line(f["name"], " · ".join(b for b in (f.get("size_text", ""), str(f.get("modified") or "")[:10]) if b))
              for f in newest]
    return _panel("MIA Folder", lines, "The folder is empty. Open the files on your phone to add some.")


# ------------------------------------------------------------ features with a page but no app of their own

def _whats_next(context, today: date):
    """Panel (the Greenhouse card): the homestead's next move, the goal it's a step toward, and the checks behind it
    (core/development_engine.plan, DEC-0144; advice only, the same as the web's What's Next)."""
    from core.development_engine import plan

    try:
        found = plan(context, month=today.month)
    except Exception:  # noqa: BLE001 - advice that can't be worked out says so
        log.exception("Glasses: What's Next couldn't be worked out")
        return _panel("What's Next", [], "That couldn't be worked out just now.")
    nxt = found.get("next") or {}
    if not nxt.get("name"):
        return _panel("What's Next", [], found.get("note") or "Nothing to suggest yet.")
    first = (nxt.get("path") or [{}])[0]
    lines = [_line(nxt["name"], first.get("cost", "") + (" · make it" if first.get("made") else ""))]
    if len(nxt.get("path") or []) > 1 and nxt.get("goal"):
        lines.append(_line(f"Step 1 of {len(nxt['path'])}", f"toward {nxt['goal']['name']}"))
    for c in nxt.get("checks") or []:
        if c["ok"] is not True:  # what's in place goes without saying on a 600-pixel card
            head, rest = _split(c["line"])
            lines.append(_line(head, rest, "attention" if c["ok"] is False else ""))
    return _panel("What's Next", lines, "Nothing to suggest yet.")


def _campaign(context, today: date):
    """Panel (the Play card): the campaign last played in Living Worlds, the latest turn and the quests still open
    (DEC-0134; play a turn by saying "in my campaign I…")."""
    from core.web_worlds import screen

    page, none = _page("Your Campaign", lambda: screen(context), "Living Worlds isn't on this MIA.")
    if none:
        return none
    c = page.get("campaign")
    if not c:
        return _panel("Your Campaign", [], "No campaign yet. Start one in Living Worlds.")
    lines = [_line(c["name"], " · ".join(b for b in (c.get("status_word", ""), (c.get("universe") or {}).get("name", ""))
                                          if b))]
    story = c.get("story") or []
    if story:
        last = story[-1]
        lines.append(_line(last["lines"][0] if last.get("lines") else last.get("said", ""), "you: " + last.get("said", "")))
    lines += [_line(q["name"], "quest") for q in c.get("quests") or [] if q.get("status") == "open"]
    return _panel("Your Campaign", lines, "Nothing played yet. Say \"in my campaign I…\"")


def _directions(context, today: date):
    """Panel (the Operating Journal card): today's seed, one thing within reach right now, and the directions in force
    (core/web_directions.screen, DEC-0141)."""
    from core.web_directions import screen

    page, none = _page("My Directions", lambda: screen(context, today), "Directions aren't on this MIA.")
    if none:
        return none
    lines = []
    if page.get("seed"):
        head, rest = _split(page["seed"])
        lines.append(_line(head, "today's seed" + (f" · {rest}" if rest else "")))
    if page.get("right_now"):
        head, rest = _split(page["right_now"])
        lines.append(_line(head, "right now" + (f" · {rest}" if rest else "")))
    lines += [_line(d["title"], d.get("statement", "")) for d in page.get("directions") or [] if d.get("active")]
    return _panel("My Directions", lines, "No directions yet. Say \"add a direction: …\"")


def _connections(context, today: date):
    """Panel (the Observations card): the connections MIA is holding, what each ties into, and what she found first
    (core/web_connections.screen, DEC-0146)."""
    from core.web_connections import screen

    page, none = _page("Connections", lambda: screen(context, today), "Connections aren't on this MIA.")
    if none:
        return none
    lines = []
    for c in page.get("waiting") or []:
        found = (c.get("found") or [{}])[0].get("line", "")
        lines.append(_line(f"{c['name']}", f"you said \u201c{c['said']}\u201d" + (f" · {found}" if found else "")))
    return _panel("Connections", lines, "No connections waiting.")


def _trade_job(context, today: date):
    """Panel (the Workshop card): the job or diagnosis being walked through (Trade Master, core/web_trades.walkthrough,
    DEC-0149): the step in focus with Next (a long one split where it reads well, its rest on the next line), its hold point with Checked,
    Back, Stop, then why; a diagnosis's question
    with Yes and No; with none going, the jobs and diagnoses to start (Start). The holds are enforced in
    core/trade_session.py, so Next on an unchecked hold says what to check."""
    from core.web_trades import walkthrough

    try:
        w = walkthrough(context)
    except Exception:
        log.exception("Glasses: the job panel failed")
        return _panel("The Job", [], "The job couldn't be read just now.")
    act = lambda kind, label, **params: {"kind": kind, "label": label, "params": params}  # noqa: E731
    if not w or w.get("status") != "working":
        from core.web_trades import library

        if getattr(context, "trade_session", None) is None:
            return _panel("The Job", [], "Trade Master isn't on this MIA.")
        starts = [_line(it["name"], f"{it['kind_word'].lower()} · {it['steps']} {'checks' if it['kind'] == 'diagnosis' else 'steps'}",
                        "", act("trade.start", "Start", item_id=it["id"]))
                  for g in library() for it in g["items"]]
        return _panel("Start a Job", starts, "Nothing written yet. Say \u201cwalk me through\u2026\u201d a build or a repair.")
    if w["kind"] == "diagnosis":
        head, rest = _split(w.get("ask") or w.get("say", ""))
        return _panel(w["title"], [_line(head, rest or "diagnosis"),
                                   _line("Yes", "", "", act("trade.answer", "Yes", answer="yes")),
                                   _line("No", "", "", act("trade.answer", "No", answer="no")),
                                   _line("Stop", "", "", act("trade.stop", "Stop"))], "")
    pr = w.get("progress") or {}
    where = f"{pr.get('phase', '')} · step {pr.get('step')} of {pr.get('of')}" if pr else ""
    open_hold = w.get("hold") and not w.get("checked")
    head, rest = _split(w.get("step_text", ""))
    lines = [_line(head, where, "", None if open_hold else act("trade.next", "Next"))]
    if rest:  # the rest of a long step on its own line, so the whole step can be read
        lines.append(_line(rest[:1].upper() + rest[1:], "then"))
    if w.get("hold"):
        lines.append(_line(w["hold"], "checked" if w.get("checked") else "check before you go on",
                           "" if w.get("checked") else "attention",
                           act("trade.check", "Checked") if open_hold else None))
    lines += [_line("Back", "one step", "", act("trade.back", "Back")), _line("Stop", "", "", act("trade.stop", "Stop"))]
    if w.get("why"):  # last: when five lines are full, "why" is still a word away
        lines.append(_line(w["why"], "why"))
    return _panel(w["title"], lines, "")


def _good_runs(context, today: date):
    """Panel (the Operating Journal card): how your good runs go (Natural Momentum, DEC-0148, core/momentum.picture):
    the findings as counts, or how many runs she's seen of the few she waits for; on a run now, only that."""
    from core import momentum

    try:
        p = momentum.picture(context)
    except Exception:
        log.exception("Glasses: the good runs failed")
        return _panel("Good Runs", [], "Your runs couldn't be read just now.")
    lines = [_line("You're on a run", "anything that can wait is held")] if p.get("in_flow") else []
    for f in p.get("findings") or []:
        head, rest = _split(f)
        lines.append(_line(head, rest))
    return _panel("Good Runs", lines, momentum.picture_words(p) or "Nothing yet.")


def _tracks(context, today: date):
    """Panel (the Maps card): the latest tracks (core/web_tracks.screen, DEC-0099), each with its distance, climb and
    time, and the last 30 days' total."""
    from core.web_tracks import screen

    page, none = _page("Tracks", lambda: screen(context, today), "Tracks aren't on this MIA.")
    if none:
        return none
    lines = [_line(t["name"], " · ".join(b for b in (f"{t['km']:g} km", f"{t['climb_m']} m up" if t["climb_m"] else "",
                                                      t["time"], t["date"]) if b)) for t in page.get("tracks") or []]
    t = page.get("totals") or {}
    if lines and t.get("count_30"):
        lines.insert(0, _line(f"{t['km_30']:g} km in the last 30 days", f"{t['count_30']} track{'s' if t['count_30'] != 1 else ''}"))
    return _panel("Tracks", lines, "No tracks yet. Add a GPX file on your phone or PC.")


def _practice(context, today: date):
    """Panel (the Classroom card): each learning path started (core/paths.path_card, DEC-0112) with its stage and what's
    next, and for a guitar check that names a chord, the chord's shape, string by string from the low E (frets and
    fingers), to read while the guitar is in your hands."""
    from core import paths

    book = getattr(context, "paths", None)
    if book is None:
        return _panel("Practice", [], "Learning paths aren't on this MIA.")
    try:
        cards = [paths.path_card(book, p) for p in (paths.program_of(context, pid) for pid in book.started()) if p]
    except Exception:
        log.exception("Glasses: the practice panel failed")
        return _panel("Practice", [], "Your paths couldn't be read just now.")
    lines = []
    for c in cards:
        st = c.get("stats") or {}
        nxt = c.get("next", "")
        m = re.search(r'next is "([^"]+)"\s*(.*)', nxt)  # "…: next is "Tune all six strings" (show me, …)."
        head, rest = (m.group(1), re.sub(r"^\([^)]*\)\.?\s*", "", m.group(2)).strip(" .")) if m else _split(nxt)
        lines.append(_line(f"{c['name']}: stage {st.get('stage', '?')}", " · ".join(b for b in (
            st.get("stage_name", ""), f"{st.get('week_minutes', 0)} min this week" if st.get("week_minutes") else "") if b)))
        if head:
            lines.append(_line(head, rest or "next"))
        if c["id"] == "guitar":
            from core.guitar import CHORDS

            for chk in c.get("open") or []:
                chord = CHORDS.get(chk.get("about") or "")
                if chord is not None:
                    lines.append(_line(f"{chord.name}: {' '.join(chord.frets)}",
                                       f"fingers {' '.join(chord.fingers)} · low E to high E"))
                    break
    return _panel("Practice", lines, "No path started. Say \u201cI want to learn guitar\u201d.")


# More menu items on cards that already had panels: added after theirs (the menu still holds five at most).
EXTRA = {
    "greenhouse": (("next", "What's Next", _whats_next),),
    "play": (("campaign", "Your Campaign", _campaign),),
    "operating_journal": (("directions", "My Directions", _directions), ("runs", "Good Runs", _good_runs)),
    "observations": (("connections", "Connections", _connections),),
    "workshop": (("job", "The Job", _trade_job),),
    "maps": (("tracks", "Tracks", _tracks),),
    "classroom": (("practice", "Practice", _practice),),
}


PANELS = {
    "dungeon": (("week", "This Week", _dungeon_week),),
    "issues": (("open", "Open Issues", _issues_open),),
    "compliance": (("due", "Deadlines", _compliance_due),),
    "flock": (("eggs", "Eggs", _flock_today),),
    "business": (("orders", "Open Orders", _business_orders), ("quotes", "Open Quotes", _business_quotes)),
    "insurance": (("renewals", "Renewals", _insurance_renewals),),
    "security": (("cameras", "Cameras", _security_cameras),),
    "reward_shop": (("rewards", "Rewards", _shop_rewards),),
    "vault": (("status", "Memory Vault", _vault_status),),
    "knowledge": (("packs", "Offline Library", _knowledge_packs),),
    "toolbox": (("alarms", "Alarms", _toolbox_alarms),),
    "operating_journal": (("how", "How I'm Living", _operating_how),),
    "life_notes": (("promises", "Promises", _kept("commitment", "Promises", "No open promises.", done_button=True)),
                   ("ideas", "Ideas", _kept("idea", "Ideas", "No ideas kept yet.")),
                   ("decisions", "Decisions", _kept("decision", "Decisions", "No decisions kept yet."))),
    "play": (("week", "This Week", _play_week),),
    "good_news": (("today", "Today's Stories", _news_today),),
    "browser": (("waiting", "Waiting For You", _browser_waiting),),
    "diagnostics": (("health", "PC Health", _diagnostics_health),),
    "files": (("folder", "MIA Folder", _files_recent),),
}


# The cards whose status line (the card face, before its menu) is their first panel's first line: the cheap reads
# only (Diagnostics inspects the PC, Files lists a folder, her browser and the vault ask a service: those show none).
STATUS_FROM = {"dungeon": "week", "issues": "open", "compliance": "due", "flock": "eggs", "business": "orders",
               "insurance": "renewals", "reward_shop": "rewards", "operating_journal": "how", "life_notes": "promises",
               "play": "week", "toolbox": "alarms"}


def status(context, app_id: str, today: date) -> dict:
    """A card's face line for an app with no at-a-glance line: {line, tone} from its first panel (tone "attention" when
    any line there needs the person), or {} for an app not in STATUS_FROM or with nothing to show."""
    item = STATUS_FROM.get(app_id)
    build = next((b for i, _label, b in PANELS.get(app_id, ()) if i == item), None)
    if build is None:
        return {}
    panel = build(context, today)
    if not panel["lines"]:
        return {}
    tone = "attention" if any(line["tone"] in ("attention", "bad") for line in panel["lines"]) else ""
    return {"line": panel["lines"][0]["text"][:48], "tone": tone}


# ------------------------------------------------------------ card-face tiles (the canvas's tile row, 2 to 4 each)

def _tile(label: str, value, tone: str = "") -> dict:
    """One tile on a card's face (core/glasses._tile's shape)."""
    return {"label": label, "value": str(value), "tone": tone}


def _flock_tiles(context, today: date) -> list[dict]:
    """The Chickens card's face: eggs today, this week, hens."""
    from core.web_flock import flock_page

    page = flock_page(context, today)
    t = (page.get("total") or {}) if page.get("available") else {}
    return [_tile("Today", f"{t.get('today', 0):g}"), _tile("Week", f"{t.get('week', 0):g}"),
            _tile("Hens", t.get("hens", 0))] if t else []


def _dungeon_tiles(context, today: date) -> list[dict]:
    """The Dungeon card's face: this week's loot, the projection, what's banked."""
    from core.web_dungeon import dungeon_page

    page = dungeon_page(context, today)
    s = (page.get("summary") or {}) if page.get("available") else {}
    return [_tile("Week", s.get("week_text", "")), _tile("Pace", s.get("projected_text", "")),
            _tile("Banked", s.get("banked_text", ""))] if s else []


def _compliance_tiles(context, today: date) -> list[dict]:
    """The Compliance card's face: overdue (needs you), soon, open."""
    from core.web_compliance import compliance_page

    page = compliance_page(context, today)
    c = (page.get("counts") or {}) if page.get("available") else {}
    return [_tile("Overdue", c.get("overdue", 0), "attention" if c.get("overdue") else ""),
            _tile("Soon", c.get("soon", 0)), _tile("Open", c.get("open", 0))] if c else []


def _shop_tiles(context, today: date) -> list[dict]:
    """The Reward Shop card's face: credits left, rewards ready to buy, bought."""
    from core.game_layer import shop_page

    page = shop_page(context)
    if not page.get("available"):
        return []
    c, n = page.get("credits") or {}, page.get("counts") or {}
    return [_tile("Credits", c.get("left", 0)), _tile("Ready", n.get("ready", 0)), _tile("Bought", n.get("bought", 0))]


def _business_tiles(context, today: date) -> list[dict]:
    """The Orders & Quotes card's face: open orders, open quotes, what's owed."""
    from core.web_business import business_page

    page = business_page(context, today)
    if not page.get("available"):
        return []
    c = page.get("counts") or {}
    return [_tile("Orders", c.get("open_orders", 0)), _tile("Quotes", c.get("open_quotes", 0)),
            _tile("Owed", c.get("owed", ""))]


TILES = {"flock": _flock_tiles, "dungeon": _dungeon_tiles, "compliance": _compliance_tiles,
         "reward_shop": _shop_tiles, "business": _business_tiles}
