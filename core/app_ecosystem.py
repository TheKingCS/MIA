"""
core.app_ecosystem
====================

MIA's understanding of her own app ecosystem (prompt 22 §7, migration phase M2; DEC-0175, DEC-0178): the Application
Registry (`core/app_registry.py`) asked the questions a person asks, answered in code from the manifests, the code and
the runtime, never from a model.

- **Inventory** (`inventory`): how many apps, by life area, how many on each device, the retired ones.
- **One app** (`details`): what it's for, what it can do (its tools and actions, counted, with a few named), how many
  of those need the person's yes each time (their tier, core/grants.py), what it keeps, what runs in the background, where it runs, what it shares with other apps and what depends on it.
- **Which app** (`which`): the app behind a tool or action name, or the apps whose words best match what was asked.
- **Status** (`statuses`, migration phase M5): every app's state now (working, needs attention, failing, missing
  something it needs, hidden, retired) with why, from its record, the scheduler's records of its jobs, the Fix-It
  Log's breakages of its tools, pages and actions, and its stores that had to be reset. `health` is the apps that
  aren't working. Whether the records agree with the code is a test's job, not a running MIA's.
- **Overlaps** (`overlaps`): tools in two different apps whose descriptions say nearly the same thing. A suggestion to
  look at, never a fault: the answer says so (the Living System invariant: recommendations are marked).
- **Gaps**: what people asked for that no app does (`core/capability_gaps.py`), counted.

`check` puts health, overlaps and gaps together for "is anything wrong with my apps?". Each `*_sentence` function is
the spoken answer; `page` is the same for the Apps page. The registry is read once per process (`registry()`):
manifests change only with the code.
"""

from __future__ import annotations

import re
from typing import Optional

from core import app_registry

_LOADED: dict = {}
OVERLAP = 0.6  # shared content words for two tools to "say nearly the same thing"
_STOP = frozenset("a an and any are as at be by can do does for from has have her how i in into is it its me my "
                  "of on one or own she so than that the their them they this to up use used what when where "
                  "which who will with you your".split())


def registry() -> app_registry.Registry:
    """The registry from the repository's manifests, read once per process."""
    if "reg" not in _LOADED:
        _LOADED["reg"] = app_registry.load()
    return _LOADED["reg"]


def _words(text: str) -> set:
    """The content words of a text, lower-cased."""
    return {w for w in re.findall(r"[a-z0-9]+", (text or "").lower()) if w not in _STOP and len(w) > 2}


def _tools(context) -> dict:
    """Every Assistant tool this MIA has, by name."""
    return dict(getattr(getattr(context, "assistant_actions", None), "_actions", {}) or {})


def _count(n: int, word: str) -> str:
    """\"1 tool\", \"3 tools\"."""
    return f"{n} {word}" + ("" if n == 1 else "s")


def _area_name(m: dict) -> str:
    """An app's life area (its group), as people read it."""
    return m.get("group") or "Other"


# ---------------------------------------------------------------- inventory and one app


def inventory(reg: app_registry.Registry) -> dict:
    """Every app, by life area, with the counts on each device and the retired ones."""
    live = reg.apps()
    areas: dict = {}
    for m in live:
        areas.setdefault(_area_name(m), []).append(m["name"])
    return {"apps": len(live), "areas": {a: sorted(n) for a, n in sorted(areas.items())},
            "devices": {d: len(reg.on_device(d)) for d in ("pc", "phone", "glasses")},
            "voice": sum(1 for m in live if m["runtime"]["devices"].get("voice")),
            "retired": sorted(m["name"] for m in reg.apps(True) if m.get("retired"))}


def _find_app(reg: app_registry.Registry, words: str) -> Optional[dict]:
    """The app a person named: by id, by name, or by the name inside what they said."""
    said = " ".join((words or "").lower().replace("_", " ").split())
    if not said:
        return None
    every = reg.apps(True)
    for m in every:
        if said in (m["id"].replace("_", " "), m["name"].lower()):
            return m
    named = [m for m in every if re.search(r"\b" + re.escape(m["name"].lower()) + r"\b", said)]
    return max(named, key=lambda m: len(m["name"]), default=None)


def details(reg: app_registry.Registry, m: dict) -> dict:
    """One app's parts, from its manifest, with the capabilities that need the person's yes each time."""
    caps = m["capabilities"]
    devices = m["runtime"]["devices"]
    return {"id": m["id"], "name": m["name"], "tagline": m.get("tagline", ""), "area": _area_name(m),
            "retired": bool(m.get("retired")), "tools": list(caps["tools"]), "actions": list(caps["actions"]),
            "stores": list(m["components"]["data"]), "background": list(m["runtime"]["background"]),
            "devices": [d for d in ("pc", "phone", "glasses") if devices.get(d, "none") != "none"],
            "voice": bool(devices.get("voice")), "uses": list(m.get("uses", [])),
            "dependents": reg.dependents_of(m["id"]), "pages": list(m["components"]["interface"]["web"]),
            "asks_each_time": sorted(n for n, t in caps.get("tiers", {}).items() if t == "act_with_approval")}


# ---------------------------------------------------------------- which app


def which(reg: app_registry.Registry, context, what: str, limit: int = 3) -> list[dict]:
    """The app behind a tool or action named exactly, else the apps whose name, description, tools and actions best
    match the words asked (each with the tools that matched)."""
    what = (what or "").strip()
    owner = reg.owner_of(what)
    if owner:
        return [{"app": reg.get(owner), "matched": [what], "exact": True}]
    asked = _words(what)
    if not asked:
        return []
    tools = _tools(context)
    scored = []
    for m in reg.apps():
        own = _words(" ".join((m["name"], m.get("tagline", ""), m.get("description", ""))))
        score = 2 * len(asked & own)
        matched = []
        for name in m["capabilities"]["tools"]:
            tool = tools.get(name)
            text = name.replace("_", " ") + " " + (getattr(tool, "description", "") or "")
            hit = len(asked & _words(text))
            if hit:
                score += hit
                matched.append((hit, name))
        if score:
            scored.append((score, m, [n for _h, n in sorted(matched, reverse=True)[:3]]))
    scored.sort(key=lambda s: (-s[0], s[1]["name"]))
    return [{"app": m, "matched": names, "exact": False} for _s, m, names in scored[:limit]]


# ---------------------------------------------------------------- health, overlaps, gaps


# An app's status (migration phase M5; docs/mia_os/MIA_OS_APPLICATION_LIFECYCLE.md section 3), worst first.
FAILING, MISSING_DEPENDENCY, NEEDS_ATTENTION, HIDDEN, WORKING, RETIRED = STATUSES = (
    "failing", "missing_dependency", "needs_attention", "hidden", "working", "retired")
STATUS_WORDS = {FAILING: "failing", MISSING_DEPENDENCY: "missing something it needs",
                NEEDS_ATTENTION: "needs attention", HIDDEN: "hidden from your sidebar", WORKING: "working",
                RETIRED: "retired"}
BROKE_DAYS = 7  # a breakage in the Fix-It Log this recent, not yet fixed, counts
_BROKE = ("tool_error", "page_error", "action_failed")


def _breakages(reg: app_registry.Registry, context) -> dict:
    """Per app, what broke in the last BROKE_DAYS and isn't marked fixed or ignored in the Fix-It Log
    (core/failure_log.py): a tool, a page or an approved action, each pinned on the app that owns it. Read from the
    person's own log; none when it isn't here or can't be read."""
    log = getattr(context, "failures", None)
    out: dict = {}
    if log is None:
        return out
    page_owner = {p: i for i, m in reg.manifests.items() for p in m["components"]["interface"].get("web", [])}
    try:
        issues = log.issues(days=BROKE_DAYS)
    except Exception:  # noqa: BLE001 - a log that won't read reports nothing broken
        return out
    for issue in issues:
        if issue.get("status") != "open" or not set(issue.get("kinds", [])) & set(_BROKE):
            continue
        example = (issue.get("examples") or [{}])[0]
        page = str(example.get("page") or "").split("/")[-1].split("#")[0].split("?")[0]
        app_id = reg.owner_of(str(example.get("tool") or "")) or page_owner.get(page) or page_owner.get(page + ".html")
        if app_id:
            out.setdefault(app_id, []).append(f"{issue['title']} ({_count(issue['count'], 'time')} this week)")
    return out


def _recovered(reg: app_registry.Registry, now=None) -> dict:
    """Per app, its stores that couldn't be read and were reset to empty in the last BROKE_DAYS (the data.recovered
    record, core/data_recovery.py), pinned by the store's file name (any .json or .jsonl name its module defines) on
    the app that owns the store."""
    import sys
    from datetime import datetime, timedelta

    from core.personal_data import HOUSEHOLD_STORES, PERSONAL_STORES

    files = {}
    for name, cls in list(PERSONAL_STORES) + list(HOUSEHOLD_STORES):
        found = {v for v in vars(sys.modules.get(cls.__module__) or cls).values()
                 if isinstance(v, str) and v.endswith((".json", ".jsonl"))}
        found |= {getattr(v, "name", "") for v in vars(sys.modules.get(cls.__module__) or cls).values()
                  if hasattr(v, "suffix") and str(getattr(v, "suffix", "")) in (".json", ".jsonl")}
        for file_name in found - {""}:
            files.setdefault(file_name, name)  # a file two stores' modules name stays with the first
    store_owner = {s: i for i, m in reg.manifests.items() for s in m["components"].get("data", [])}
    since = ((now or datetime.now()) - timedelta(days=BROKE_DAYS)).isoformat()
    out: dict = {}
    try:
        from core.dev_store import DEV_DATA, DevStore

        for rec in DevStore(DEV_DATA / "recovered").tail(200):
            store = files.get(str(rec.get("file", "")))
            if store and str(rec.get("at", "")) >= since and store in store_owner:
                out.setdefault(store_owner[store], set()).add(store)
    except Exception:  # noqa: BLE001 - no record, nothing recovered
        return {}
    return {i: [f"its {s.replace('_', ' ')} couldn't be read and started empty" for s in sorted(stores)]
            for i, stores in out.items()}


def statuses(reg: app_registry.Registry, context) -> dict:
    """Every app's status now, with why: {app_id: {"status", "why": [...]}} (see STATUSES). Failing: its record
    couldn't be loaded, or one of its jobs failed three times in a row and is backing off. Missing something it
    needs: a dependency that isn't an app or is retired. Needs attention: one of its jobs failed lately, something of
    its broke this week and isn't fixed (the Fix-It Log), or one of its stores was reset after it couldn't be read.
    Hidden: tucked out of the person's sidebar. Otherwise working (retired ones say so). Built from the registry, the
    scheduler's records, the Fix-It Log and the recovered-file record; never from the model."""
    from core.homeostasis import BACKOFF_AFTER

    failing: dict = {}
    attention: dict = {}
    ids = sorted(reg.manifests, key=len, reverse=True)  # "world_intel" before "world"
    for problem in reg.load_problems:
        app_id = next((i for i in ids if problem.startswith(i + ":")), problem.split(":")[0] or "mia")
        failing.setdefault(app_id, []).append(problem)
    job_owner = {j: i for i, m in reg.manifests.items() for j in m["runtime"]["background"]}
    scheduler = getattr(context, "scheduler", None)
    try:
        jobs = scheduler.status() if scheduler is not None else []
    except Exception:  # noqa: BLE001
        jobs = []
    for job in jobs:
        n = int(job.get("failures_in_a_row") or 0)
        if n:
            said = (f"its job {job['name']} failed {_count(n, 'time')} in a row"
                    + (f" ({job['last_error']})" if job.get("last_error") else ""))
            (failing if n >= BACKOFF_AFTER else attention).setdefault(job_owner.get(job["name"], "mia"), []).append(said)
    for source in (_breakages(reg, context), _recovered(reg)):
        for app_id, why in source.items():
            attention.setdefault(app_id, []).extend(why)
    hidden = _hidden(context)
    out = {}
    for app_id, m in reg.manifests.items():
        missing = [d.get("application_id") for d in m.get("dependencies", [])
                   if d.get("application_id") not in reg.manifests or (reg.get(d.get("application_id")) or {}).get("retired")]
        if app_id in failing:
            out[app_id] = {"status": FAILING, "why": failing[app_id] + attention.get(app_id, [])}
        elif missing:
            out[app_id] = {"status": MISSING_DEPENDENCY, "why": [f"it needs {', '.join(missing)}, which isn't here"]}
        elif app_id in attention:
            out[app_id] = {"status": NEEDS_ATTENTION, "why": attention[app_id]}
        elif m.get("retired"):
            out[app_id] = {"status": RETIRED, "why": []}
        elif app_id in hidden:
            out[app_id] = {"status": HIDDEN, "why": ["you tucked it away; it still works and its tools still answer"]}
        else:
            out[app_id] = {"status": WORKING, "why": []}
    for app_id in set(failing) - set(out):  # a record that couldn't be loaded has no manifest to list it by
        out[app_id] = {"status": FAILING, "why": failing[app_id]}
    return out


def _hidden(context) -> set:
    """The apps tucked out of this person's sidebar (core/web_surfaces._visible); none when it can't be told."""
    try:
        from core.web_surfaces import APPS, RETIRED, _visible

        return {a.module_id for a in APPS if a.module_id not in RETIRED and not _visible(context, a)}
    except Exception:  # noqa: BLE001
        return set()


def health(reg: app_registry.Registry, context) -> dict:
    """Per app, what's wrong now: the apps whose status (`statuses`) isn't working, hidden or retired, with why. The
    full comparison of every record with the code (`Registry.problems`) isn't run here: it needs the PC's whole tool
    list built afresh, which a phone or a runtime without a window can't do, and `tests/test_app_registry.py` already
    refuses a build where they disagree."""
    return {i: s["why"] for i, s in statuses(reg, context).items() if s["status"] not in (WORKING, HIDDEN, RETIRED)}


def overlaps(reg: app_registry.Registry, context) -> list[dict]:
    """Tools in two different apps whose descriptions share most of their content words: worth a look, not a fault."""
    tools = _tools(context)
    owned = []
    for m in reg.apps():
        for name in m["capabilities"]["tools"]:
            if name in tools:
                owned.append((m["id"], name, _words(getattr(tools[name], "description", ""))))
    found = []
    for i, (app_a, tool_a, words_a) in enumerate(owned):
        if len(words_a) < 4:
            continue
        for app_b, tool_b, words_b in owned[i + 1:]:
            if app_b == app_a or len(words_b) < 4:
                continue
            alike = len(words_a & words_b) / len(words_a | words_b)
            if alike >= OVERLAP:
                found.append({"apps": [app_a, app_b], "tools": [tool_a, tool_b], "alike": round(alike, 2)})
    return sorted(found, key=lambda f: -f["alike"])


def gaps(context) -> list[dict]:
    """What people asked for that no app does yet, open ones, most asked first."""
    from core import capability_gaps

    open_ = [g for g in capability_gaps.load(context) if g.get("status") in ("open", "offered")]
    return sorted(open_, key=lambda g: -g.get("count", 0))


def check(reg: app_registry.Registry, context) -> dict:
    """Health, overlaps and gaps together."""
    return {"health": health(reg, context), "overlaps": overlaps(reg, context), "gaps": gaps(context)}


# ---------------------------------------------------------------- spoken answers


def _names(reg: app_registry.Registry, ids) -> str:
    """App names for ids, joined."""
    return ", ".join((reg.get(i) or {}).get("name", i) for i in ids)


def inventory_sentence(reg: app_registry.Registry) -> str:
    """\"What apps do I have?\""""
    inv = inventory(reg)
    areas = "; ".join(f"{a}: {', '.join(n)}" for a, n in inv["areas"].items())
    d = inv["devices"]
    text = (f"I have {inv['apps']} apps. {areas}. On the PC {d['pc']}, the phone {d['phone']}, the glasses "
            f"{d['glasses']}; {inv['voice']} work by voice.")
    if inv["retired"]:
        text += f" Retired: {', '.join(inv['retired'])}."
    return text


def details_sentence(reg: app_registry.Registry, words: str, context=None) -> str:
    """\"What can Greenhouse do?\", \"what depends on Home?\" and \"is Greenhouse working?\": its parts, how much of it
    needs a yes each time and, with a `context`, its status now (`statuses`)."""
    m = _find_app(reg, words)
    if m is None:
        return f"I don't have an app called {words}. Ask \"what apps do I have?\" for the list."
    d = details(reg, m)
    state = statuses(reg, context).get(m["id"], {}) if context is not None else {}
    some = ", ".join(t.replace("_", " ") for t in d["tools"][:5])
    tagline = d["tagline"].rstrip(" .")
    parts = [f"{d['name']} ({d['area']})" + (f": {tagline}" if tagline else "")]
    if d["retired"]:
        parts.append("It's retired")
    elif state.get("status"):
        why = "; ".join(state.get("why", [])[:2])
        parts.append(f"Right now it's {STATUS_WORDS[state['status']]}" + (f": {why}" if why and state["status"] != HIDDEN else ""))
    parts.append(f"It has {_count(len(d['tools']), 'tool')} and {_count(len(d['actions']), 'action')}"
                 + (f", like {some}" if some else ""))
    if d["asks_each_time"]:
        parts.append(f"{_count(len(d['asks_each_time']), 'thing')} it does need{'s' if len(d['asks_each_time']) == 1 else ''} "
                     f"your yes each time (paying, sending, deleting)")
    if d["stores"]:
        parts.append(f"It keeps {', '.join(s.replace('_', ' ') for s in d['stores'])}")
    if d["background"]:
        parts.append(f"{_count(len(d['background']), 'job')} run{'s' if len(d['background']) == 1 else ''} in the background")
    parts.append(f"It runs on {', '.join(d['devices']) or 'no screen'}" + (" and by voice" if d["voice"] else ""))
    if d["uses"]:
        parts.append(f"It shares {', '.join(d['uses'])} with other apps")
    parts.append(f"Depends on it: {_names(reg, d['dependents'])}" if d["dependents"] else "No app depends on it")
    return ". ".join(parts) + "."


def which_sentence(reg: app_registry.Registry, context, what: str) -> str:
    """\"Which app can monitor energy?\""""
    found = which(reg, context, what)
    if not found:
        return f"None of my apps does {what} that I can tell. If you'd like it, say so and I'll note it as a gap."
    first = found[0]
    if first["exact"]:
        return f"{first['matched'][0]} belongs to {first['app']['name']}."
    lines = []
    for f in found:
        tools = ", ".join(t.replace("_", " ") for t in f["matched"])
        lines.append(f"{f['app']['name']}" + (f" ({tools})" if tools else ""))
    return "Best matches, by their words: " + "; ".join(lines) + "."


def check_sentence(reg: app_registry.Registry, context) -> str:
    """\"Is anything wrong with my apps?\": health first, then what's suggested, marked as suggestions."""
    c = check(reg, context)
    parts = []
    if c["health"]:
        parts.append("Wrong now: " + "; ".join(
            f"{_names(reg, [i]) if i != 'mia' else 'MIA herself'}: {', '.join(p[:2])}" for i, p in c["health"].items()))
    else:
        parts.append("Every app's record loaded and no background job is failing")
    if c["overlaps"]:
        o = c["overlaps"][0]
        parts.append(f"My suggestion, not a fault: {_count(len(c['overlaps']), 'pair')} of tools in different apps say "
                     f"nearly the same thing, like {o['tools'][0]} ({_names(reg, [o['apps'][0]])}) and "
                     f"{o['tools'][1]} ({_names(reg, [o['apps'][1]])})")
    if c["gaps"]:
        parts.append(f"{_count(len(c['gaps']), 'thing')} you've asked for that no app does yet")
    return ". ".join(parts) + "."


def page(context) -> dict:
    """The Apps page's registry section: the inventory's counts, each app's problems, overlaps and gaps, and what
    MIA may do on her own (her grants, core/grants.py) with how many capabilities always need the person's yes."""
    reg = registry()
    c = check(reg, context)
    inv = inventory(reg)
    from core import grants

    return {"apps": inv["apps"], "devices": inv["devices"], "voice": inv["voice"],
            "manifests": len(reg.manifests),
            "grants": [g.as_dict() for g in grants.standing(context)],
            "asks_each_time": sum(1 for t in grants.tiers().values() if t == grants.WITH_APPROVAL),
            "health": [{"id": i, "name": (reg.get(i) or {}).get("name", "MIA"), "problems": p}
                       for i, p in sorted(c["health"].items())],
            "overlaps": [{"tools": o["tools"], "apps": [(reg.get(a) or {}).get("name", a) for a in o["apps"]]}
                         for o in c["overlaps"][:10]],
            "gaps": [{"what": (g.get("examples") or [""])[0], "count": g.get("count", 0), "need": g.get("need", "")}
                     for g in c["gaps"][:10]]}
