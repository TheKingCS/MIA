"""
core.assistant_records_actions
================================

Asking about what she keeps (DEC-0125, full use both ways): Insurance,
Kept, the Operating Journal, Play and Files could be changed by voice or
only seen on a screen, never asked about. Five read-only tools, each
phrased from its screen's own data so voice and screen agree:

- get_insurance: each policy, what it costs a year, when it renews, and
  what's worth a look (core/insurance.py);
- list_kept: the promises, decisions, ideas and goals she kept, open first
  (core/life_notes.py; "I kept my promise to Sam" stays a quick command);
- get_operating_journal: each line and how it's going (core/operating_journal.py);
- get_play: this week's games and the load (core/recreation.py);
- find_my_files: a folder's contents or files by name, only inside the
  person's own MIA files folder (core/my_files.py);
- get_vault_status: whether the phone's photos are safe at home
  (core/memory_vault.py, the Memory Vault's summary).

`register_area_keywords` gives older areas the words that should reach
their tools ("what's my next trip?" reached none: DEC-0125's glasses asks
found it, 2026-11-07).
"""

from __future__ import annotations

from core.assistant_actions import AssistantAction, AssistantActionRegistry


def _action_get_insurance(context, arguments: dict) -> str:
    """Tool get_insurance: each policy (or the one named) with its insurer, yearly cost, renewal date and the checks
    worth a look; then the total and what the best quotes could save."""
    from core.insurance import insurance_page
    from core.region import money

    page = insurance_page(context)
    if not page.get("available"):
        return "There's no insurance here yet."
    wanted = " ".join(str(arguments.get("policy") or "").lower().split())
    policies = [p for p in page["policies"]
                if not wanted or wanted in f"{p['name']} {p['kind']} {p['insurer']} {p['covers']}".lower()]
    if not policies:
        return f"I don't see a policy for {wanted}." if wanted else "No policies yet. Add one in Insurance."
    lines = []
    for p in policies:
        line = f"{p['name'] or p['kind']} with {p['insurer']}: {money(p['per_year'])} a year"
        line += f", renews {p['renews']}" if p["renews"] else ", no renewal date set"
        if p["deductible"]:
            line += f", {money(p['deductible'])} deductible"
        lines.append(line + "." + "".join(" " + c["text"] for c in p["checks"][:2]))
    summary = page["summary"]
    if not wanted:
        lines.append(f"In all {money(summary['per_year'])} a year" +
                     (f"; the best quotes could save {money(summary['could_save'])}." if summary["could_save"] else "."))
    return " ".join(lines)


def _action_list_kept(context, arguments: dict) -> str:
    """Tool list_kept: the notes she kept of one kind (promises, decisions, ideas, goals set aside) or all, the open
    ones first, with when they're due."""
    from core.life_notes import screen

    wanted = " ".join(str(arguments.get("kind") or "").lower().split())
    lines = []
    for kind in screen(context)["kinds"]:
        if wanted and wanted.rstrip("s") not in f"{kind['kind']} {kind['title']}".lower():
            continue
        open_ = [n for n in kind["notes"] if n["status"] == "open"][:6]
        if open_:
            lines.append(f"{kind['title']}: " + "; ".join(n["line"] + (f" (by {n['due']})" if n["due"] else "")
                                                       for n in open_) + ".")
    return " ".join(lines) or "Nothing kept" + (f" of {wanted}" if wanted else "") + " yet."


def _action_get_operating_journal(context, arguments: dict) -> str:
    """Tool get_operating_journal: each line of how the person means to live and how it's going now."""
    from core.operating_journal import screen

    lines = screen(context)["lines"]
    if not lines:
        return "Your operating journal is empty. Say \"add to my operating journal: ...\" to start it."
    return " ".join(f"{l['text']}: {l['now'] or l['how']}." for l in lines[:10])


def _action_get_play(context, arguments: dict) -> str:
    """Tool get_play: this week's play and load beside the weeks before, and the latest games."""
    from core.recreation import screen

    page = screen(context)
    if not page["played"]:
        return "No games logged yet. Say something like \"played pickleball for an hour, it was hard\"."
    latest = "; ".join(f"{e['what']} {e['minutes']:g} min on {e['date']}" + (f" with {e['with']}" if e["with"] else "")
                       for e in page["played"][:3])
    return " ".join(page["lines"] + [f"Latest: {latest}."])


def _action_find_my_files(context, arguments: dict) -> str:
    """Tool find_my_files: the files whose names hold the words asked for, or the top folder's contents; only inside
    the person's own MIA files folder."""
    from core.my_files import MyFiles

    try:
        files = MyFiles.for_context(context)
    except ValueError:
        return "There's no files folder here."
    wanted = " ".join(str(arguments.get("name") or "").lower().split())
    if not wanted:
        listing = files.listing("")
        items = [f["name"] + "/" for f in listing["folders"]] + [f["name"] for f in listing["files"]]
        return ("In My Files: " + ", ".join(items[:15]) + "." if items else "My Files is empty.")
    root = files.root.resolve()
    found = [p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and wanted in p.name.lower()]
    if not found:
        return f"No file named like {wanted} in My Files."
    return "Found: " + ", ".join(files.relative(p) for p in found[:10]) + ". Open them in Files."


def register_records_actions(registry: AssistantActionRegistry) -> None:
    """Registers get_insurance (insurance), list_kept (life_notes), get_operating_journal (operating_journal),
    get_play (play), find_my_files (files) and get_vault_status (vault), and the older areas' keywords
    (register_area_keywords)."""
    register_area_keywords(registry)
    registry.register(AssistantAction(
        name="get_vault_status", domain="vault",
        description="Whether the user's phone photos are backed up on the home computer (the Memory Vault).",
        parameters={"type": "object", "properties": {}},
        handler=_action_get_vault_status,
        trigger_phrases=("photos backed up", "pictures backed up", "memory vault", "photos safe"),
    ))
    registry.register_domain_keywords("insurance", ("insurance", "insured", "premium", "premiums", "deductible"))
    registry.register_domain_keywords("life_notes", ("promise", "promised", "promises"))
    registry.register_domain_keywords("operating_journal", ("operating",))
    registry.register_domain_keywords("play", ("played", "pickleball", "tennis", "basketball", "sports"))
    registry.register_domain_keywords("files", ("files", "folder"))
    registry.register(AssistantAction(
        name="get_insurance", domain="insurance",
        description="The user's insurance policies: insurer, cost a year, renewal date, deductible, what to look at.",
        parameters={"type": "object", "properties": {
            "policy": {"type": "string", "description": "Which policy (car, home, the truck...), or empty for all."},
        }},
        handler=_action_get_insurance,
        trigger_phrases=("my insurance", "insurance renew", "my policy", "my policies", "what does my insurance"),
    ))
    registry.register(AssistantAction(
        name="list_kept", domain="life_notes",
        description="What MIA kept for the user from what they said: promises, decisions, ideas, goals set aside.",
        parameters={"type": "object", "properties": {
            "kind": {"type": "string", "description": "promises, decisions, ideas or goals; empty for all."},
        }},
        handler=_action_list_kept,
        trigger_phrases=("what did i promise", "my promises", "what did i decide", "my decisions", "what ideas",
                         "my ideas", "what have you kept", "goals i set aside"),
    ))
    registry.register(AssistantAction(
        name="get_operating_journal", domain="operating_journal",
        description="The user's Operating Journal: how they mean to live (values, priorities, rules) and how it's going.",
        parameters={"type": "object", "properties": {}},
        handler=_action_get_operating_journal,
        trigger_phrases=("operating journal", "living how i said", "living how i want", "my values", "my priorities",
                         "my rules", "my ideal day", "my ideal week"),
    ))
    registry.register(AssistantAction(
        name="get_play", domain="play",
        description="Games and sports the user played this week, the training load, and the latest games.",
        parameters={"type": "object", "properties": {}},
        handler=_action_get_play,
        trigger_phrases=("how much have i played", "my play load", "games this week", "what have i played",
                         "my training load"),
    ))
    registry.register(AssistantAction(
        name="find_my_files", domain="files",
        description="Find documents by name in the user's own MIA folder, or list what's in it.",
        parameters={"type": "object", "properties": {
            "name": {"type": "string", "description": "Words in the file's name, or empty to list the folder."},
        }},
        handler=_action_find_my_files,
        trigger_phrases=("find my file", "find the file", "my files", "what files", "find a file"),
    ))


def _action_get_vault_status(context, arguments: dict) -> str:
    """Tool get_vault_status: whether the phone's photos are safe on the home computer: how many, how many are still
    only on the phone, and when the last ones were sent (the Memory Vault screen's own summary)."""
    from core.memory_vault import vault_page

    page = vault_page(context)
    if not page.get("available") or not page.get("on"):
        return "The Memory Vault isn't on. Turn it on in the phone app (Memory Vault → Set Up) to keep your photos safe at home."
    s = page["summary"]
    said = f"{s['on_pc']:,} of {s['photos'] + s['videos']:,} photos and videos are safe on the home computer"
    said += f"; {s['waiting']:,} still only on the phone ({s['waiting_size']})." if s["waiting"] else ", all of them."
    if s.get("last_sent"):
        said += f" Last sent {s['last_sent'][:10]}."
    return said + (f" {page['state_words']}" if page.get("state_words") else "")


def register_area_keywords(registry: AssistantActionRegistry) -> None:
    """Words that attach older areas whose everyday questions reached no tool: trips (expeditions), the lab, notes,
    the inbox, the battery (power, beside the system tools), upkeep on vehicles, rentals, and photo backups."""
    registry.register_domain_keywords("expeditions", ("trip", "trips", "expedition", "expeditions", "hike", "hiking",
                                                      "camping"))
    registry.register_domain_keywords("lab", ("lab", "experiment", "experiments"))
    registry.register_domain_keywords("notes", ("notes",))
    registry.register_domain_keywords("inbox", ("inbox", "emails"))
    registry.register_domain_keywords("power", ("battery", "propane", "generator", "solar"))
    registry.register_domain_keywords("maintenance", ("upkeep", "vehicle", "vehicles"))
    # Not "property": "a useful property of this material" is small talk.
    registry.register_domain_keywords("real_estate", ("rental", "rentals", "tenant", "tenants"))
    registry.register_domain_keywords("vault", ("backed up", "backup", "photos safe"))

