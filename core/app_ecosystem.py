"""
core.app_ecosystem
====================

MIA's understanding of her own app ecosystem (prompt 22 §7, migration phase M2; DEC-0175, DEC-0178): the Application
Registry (`core/app_registry.py`) asked the questions a person asks, answered in code from the manifests, the code and
the runtime, never from a model.

- **Inventory** (`inventory`): how many apps, by life area, how many on each device, the retired ones.
- **One app** (`details`): what it's for, what it can do (its tools and actions, counted, with a few named), what it
  keeps, what runs in the background, where it runs, what it shares with other apps and what depends on it.
- **Which app** (`which`): the app behind a tool or action name, or the apps whose words best match what was asked.
- **Health** (`health`): per app, what the registry check found wrong and the background jobs that are failing (from
  the scheduler's own records).
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
    """One app's parts, from its manifest."""
    caps = m["capabilities"]
    devices = m["runtime"]["devices"]
    return {"id": m["id"], "name": m["name"], "tagline": m.get("tagline", ""), "area": _area_name(m),
            "retired": bool(m.get("retired")), "tools": list(caps["tools"]), "actions": list(caps["actions"]),
            "stores": list(m["components"]["data"]), "background": list(m["runtime"]["background"]),
            "devices": [d for d in ("pc", "phone", "glasses") if devices.get(d, "none") != "none"],
            "voice": bool(devices.get("voice")), "uses": list(m.get("uses", [])),
            "dependents": reg.dependents_of(m["id"]), "pages": list(m["components"]["interface"]["web"])}


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


def health(reg: app_registry.Registry, context) -> dict:
    """Per app: what the registry check found wrong, and its background jobs that are failing now. Only apps with
    something wrong appear."""
    out: dict = {}
    ids = sorted(reg.manifests, key=len, reverse=True)  # "world_intel" before "world"
    for problem in reg.problems():
        app_id = next((i for i in ids if problem.startswith((i + ":", i + " claims"))), "mia")
        out.setdefault(app_id, []).append(problem)
    job_owner = {j: i for i, m in reg.manifests.items() for j in m["runtime"]["background"]}
    scheduler = getattr(context, "scheduler", None)
    for job in (scheduler.status() if scheduler is not None else []):
        if job.get("failures_in_a_row"):
            app_id = job_owner.get(job["name"], "mia")
            out.setdefault(app_id, []).append(
                f"its job {job['name']} failed {_count(job['failures_in_a_row'], 'time')} in a row"
                + (f" ({job['last_error']})" if job.get("last_error") else ""))
    return out


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


def details_sentence(reg: app_registry.Registry, words: str) -> str:
    """\"What can Greenhouse do?\" and \"what depends on Home?\""""
    m = _find_app(reg, words)
    if m is None:
        return f"I don't have an app called {words}. Ask \"what apps do I have?\" for the list."
    d = details(reg, m)
    some = ", ".join(t.replace("_", " ") for t in d["tools"][:5])
    tagline = d["tagline"].rstrip(" .")
    parts = [f"{d['name']} ({d['area']})" + (f": {tagline}" if tagline else "")]
    if d["retired"]:
        parts.append("It's retired")
    parts.append(f"It has {_count(len(d['tools']), 'tool')} and {_count(len(d['actions']), 'action')}"
                 + (f", like {some}" if some else ""))
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
        parts.append("Every app's record agrees with the code and no background job is failing")
    if c["overlaps"]:
        o = c["overlaps"][0]
        parts.append(f"My suggestion, not a fault: {_count(len(c['overlaps']), 'pair')} of tools in different apps say "
                     f"nearly the same thing, like {o['tools'][0]} ({_names(reg, [o['apps'][0]])}) and "
                     f"{o['tools'][1]} ({_names(reg, [o['apps'][1]])})")
    if c["gaps"]:
        parts.append(f"{_count(len(c['gaps']), 'thing')} you've asked for that no app does yet")
    return ". ".join(parts) + "."


def page(context) -> dict:
    """The Apps page's registry section: the inventory's counts, each app's problems, overlaps and gaps."""
    reg = registry()
    c = check(reg, context)
    inv = inventory(reg)
    return {"apps": inv["apps"], "devices": inv["devices"], "voice": inv["voice"],
            "manifests": len(reg.manifests),
            "health": [{"id": i, "name": (reg.get(i) or {}).get("name", "MIA"), "problems": p}
                       for i, p in sorted(c["health"].items())],
            "overlaps": [{"tools": o["tools"], "apps": [(reg.get(a) or {}).get("name", a) for a in o["apps"]]}
                         for o in c["overlaps"][:10]],
            "gaps": [{"what": (g.get("examples") or [""])[0], "count": g.get("count", 0), "need": g.get("need", "")}
                     for g in c["gaps"][:10]]}
