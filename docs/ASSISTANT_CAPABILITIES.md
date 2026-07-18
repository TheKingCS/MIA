# Assistant Capabilities — the full record

This is the single source of truth for "what can M.I.A.'s Assistant
actually do right now" — created 2026-07-15 because no such record
existed; every prior answer to that question required reading
`core/application.py` directly or reconstructing it from
`docs/ROADMAP.md`'s scattered milestone history.

**Two kinds of capability, and they work completely differently:**

1. **Tool actions** — discrete, callable things (add a mission, check
   battery level, delete a waypoint). These are what the Assistant can
   *do*. Attached to a chat request only when the prompt's own
   `trigger_phrases` match (domain-scoped attachment,
   `core/assistant_actions.py` — see "Why not just attach everything"
   below), never all at once.
2. **Standing behaviors** — things the Assistant *is*, always true,
   never conditionally attached. These are the ones most likely to be
   "forgotten" by the model itself unless explicitly told, because
   there's no tool call to hang them on — see "The self-knowledge
   problem" below.

## Standing behaviors (not tool calls — always true)

- **Persistent, multi-turn memory.** Conversations are saved
  (`core/conversation_manager.py`) and real chat history (not just the
  latest message) is sent on every turn (`core/assistant_chat.py`).
  Separately, specific facts the user states get extracted and stored
  long-term (`core/user_memory_manager.py`, reviewable/deletable via
  the "🧠 Memories" button in the Assistant module).
- **Spoken output.** The full-screen Assistant module (not the sidebar)
  speaks every reply aloud via Piper TTS, and the Home dashboard speaks
  its startup briefing once per launch. Voice is selectable in
  Settings among a curated 5-voice catalog (`core/voice_catalog.py`).
- **Voice input.** Push-to-talk in the full Assistant module transcribes
  speech via Vosk and sends it as if typed.
- **A warm, curious personality** on conversational (non-action)
  replies — deliberately absent from the action-request path, see
  "Why not just attach everything" below.
- **Proactive behaviors**, each firing at most once per day
  (`core/daily_occasions.py`, `core/application.py`'s
  `_check_daily_occasions()`): birthday celebration, a same-day Calendar
  digest, and an evening "haven't heard from you today" check-in.
- **Celebratory notifications** on Mission/objective completion
  (`core/mission_manager.py`), independent of whether the Assistant was
  involved in that completion at all.
- **Self-knowledge for "how do I use X" questions** — grounded (RAG)
  against `docs/user_help/*.md`, a genuine end-user doc corpus, separate
  from this project's own developer docs (`core/device_help_manager.py`).
  This is retrieval-based specifically so it scales without bloating
  every prompt — see "The self-knowledge problem" below for why that
  matters.
- **Intent classification gates which of two prompt shapes gets used**
  (`modules/assistant/module.py`'s `looks_like_action_request()`): an
  info question gets personality + memory + help-grounding and no
  tools; a request that looks like an action gets a bare identity line
  and only the matching domain(s)' tools. They're mutually exclusive on
  purpose — mixing them has caused real, measured regressions (see
  `docs/ROADMAP.md`'s gotcha #7).

## The self-knowledge problem (read before adding a new capability)

**A capability with no tool call attached to it is invisible to the
model unless something explicitly tells it.** This is not hypothetical
— found live, 2026-07-15: asked "Can you speak?", the Assistant
answered "I don't know how to speak in the classical sense... I'm a
text-based AI," despite TTS being fully wired up. The system prompt
simply never mentioned it.

**The fix was deliberately narrow, not a bulk injection, and that's the
standing policy going forward:**

- **Do NOT dump the full capability list (this document, or the tool
  registry) into the system prompt.** This codebase has hit repeated,
  measured regressions from longer prompts — a longer grounding
  preamble made the model *more* likely to falsely say "I don't know"
  (docs/ROADMAP.md, `device_help_manager`'s `GROUNDING_INSTRUCTION`
  history), and growing the tool-count attached to a single request has
  caused outright hallucinated tool calls more than once (gotchas #9,
  #12). More context is not free, and on a 3B on-device model there's
  no slack to spend carelessly.
- **Tool actions stay covered by domain-scoped attachment** (already
  the right mechanism — a tool call itself proves the capability to the
  model the moment it's attached).
- **"How do I use X" questions stay covered by `docs/user_help/*.md`
  retrieval** — cheap to extend (add a paragraph to a help file, no
  prompt-length cost on unrelated questions), and already the
  established pattern.
- **Only a handful of the most foundational, near-universal-to-ask
  facts belong hardcoded directly in the system prompt** — currently
  just "you can speak your replies aloud"
  (`core/assistant_chat.py`'s `_IDENTITY_WARMTH`, info-question path
  only, never the action path). Add to this list *sparingly* — each
  addition is prompt-length spent on every single info-question reply,
  forever.
- **Whenever a new standing behavior ships, check two things**: (1) is
  it foundational/near-universal enough to belong in
  `_IDENTITY_WARMTH`, or (2) does `docs/user_help/*.md` need a new
  paragraph so retrieval can answer it? Most new capabilities should be
  (2), not (1) — reserve (1) for things a user would plausibly ask
  about in their very first minute with the Assistant.

## Why not just attach every tool to every request

`core/assistant_actions.py`'s docstring covers this in full — short
version: the model gets noticeably less reliable at picking the right
tool as the number of *attached* tools per request grows, independent
of how many are registered in total. Domain-scoped attachment
(`matching_actions()`) keeps a typical request down to ~10 tools (the
matched domain(s) plus a small always-on "system" set) instead of
attaching the full registry to every message.

## Tool registry (74 actions, 19 domains, as of 2026-07-18)

**Do not hand-edit this section.** Regenerate it with:

```bash
python tools/dump_assistant_capabilities.py
```

and paste the output over everything below this line, whenever the
registry changes (`core/application.py`'s `_register_assistant_actions()`).

<!-- Generated by tools/dump_assistant_capabilities.py — 74 actions, 19 domains -->

### `alarms` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_alarm` |  | Create a new alarm in M.I.A. |
| `delete_alarm` | Yes | Delete an existing alarm in M.I.A. by its label. |
| `list_alarms` |  | List the user's current alarms in M.I.A. |

### `calendar` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_calendar_event` |  | Add a new event to M.I.A.'s Calendar. |
| `delete_calendar_event` | Yes | Delete an existing Calendar event in M.I.A. by its title. |
| `list_calendar_events` |  | List the user's upcoming/scheduled Calendar events in M.I.A. — what's coming up today, this week, or on any date. Not for past activity — see recall_recent_activity for that. |

### `components` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_component` |  | Add a new electronic component to M.I.A.'s Workshop & Electronics component database. |
| `delete_component` | Yes | Delete an existing electronic component in M.I.A. by name. |
| `list_components` |  | List or search the user's electronic components in M.I.A. |

### `expeditions` (11)

| Action | Destructive | Description |
|---|---|---|
| `add_expedition` |  | Start a new Expedition (a dated outing that can hold multiple trips) in M.I.A.'s Expeditions module. |
| `add_gear_item` |  | Add an item to a Trip's gear checklist in M.I.A. |
| `add_trip` |  | Add a new Trip (one hike, paddle, ride, fishing trip, etc.) under an existing Expedition in M.I.A. |
| `add_trip_log_entry` |  | Add a dated journal/log entry to a specific Trip in M.I.A., optionally recording weather/conditions. Use this instead of add_note when the user is logging something about a specific trip/outing (arriving somewhere, conditions encountered, etc.), not a general-purpose note. |
| `delete_expedition` | Yes | Delete an existing Expedition in M.I.A. by name. |
| `delete_trip` | Yes | Delete an existing Trip in M.I.A. by name. |
| `get_trip_summary` |  | Get a Trip's logged distance, average speed, and planned route distance in M.I.A. |
| `list_expeditions` |  | List the user's Expeditions in M.I.A. |
| `list_trips` |  | List the user's Trips in M.I.A., optionally filtered to one Expedition by name. |
| `recall_expedition` |  | Get a detailed recap of ONE Expedition in M.I.A.'s Memories: duration, distance/pace per activity type, waypoint categories visited, latest journal/conditions entry, and photo count. This is a single-Expedition summary, NOT a bare list — use list_expeditions instead for 'what expeditions do I have'-style questions. Leave name empty for the most recent Expedition. |
| `toggle_gear_packed` |  | Mark a gear checklist item on a Trip as packed or not packed (toggles its current state). |

### `field_kit` (2)

| Action | Destructive | Description |
|---|---|---|
| `list_connected_devices` |  | List currently connected external USB storage and serial devices in M.I.A.'s Field Kit. |
| `list_scripts` |  | List the user's saved scripts in M.I.A.'s Field Kit script library. |

### `inventory` (4)

| Action | Destructive | Description |
|---|---|---|
| `add_inventory_item` |  | Add a new item to M.I.A.'s general Inventory tool. |
| `adjust_inventory_quantity` | Yes | Change the quantity of an existing inventory item by an amount (positive to add more, negative to use/remove some), e.g. 'I used 5 M3 bolts' -> delta -5. Quantity never goes below zero. Use add_inventory_item instead for a brand-new item. |
| `delete_inventory_item` | Yes | Remove an item entirely from M.I.A.'s Inventory tool by name. |
| `list_inventory` |  | List or search M.I.A.'s Inventory tool, including quantities. Use this to answer 'how many X do I have' questions about inventory items. Leave query empty to list everything. |

### `jobs` (4)

| Action | Destructive | Description |
|---|---|---|
| `add_job` |  | Start a new production Job in M.I.A.'s Workshop pipeline. |
| `consume_material` |  | Record that an existing Job consumed some quantity of an existing Material — deducts that quantity from the Material's own stock automatically. |
| `list_jobs` |  | List the user's production Jobs in M.I.A.'s Workshop pipeline. |
| `produce_product` |  | Record that an existing Job produced some quantity of an existing Product — credits that quantity onto the Product's own stock automatically. |

### `ledger` (2)

| Action | Destructive | Description |
|---|---|---|
| `get_ledger_summary` |  | Get the user's total revenue, expenses, and net profit from M.I.A.'s Workshop Ledger. |
| `record_sale` |  | Record a sale of an existing Product in M.I.A.'s Workshop Ledger — deducts the sold quantity from the Product's stock and logs the revenue. |

### `maps` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_trail_map_from_url` |  | Download a trail map PDF from a direct URL and add it to M.I.A.'s trail map catalog. Not for offline tile/basemap downloads — those are only available from the Maps module's own UI, since they can take too long to run as part of a chat reply. |
| `delete_trail_map` | Yes | Delete a cataloged trail map PDF from M.I.A.'s Maps module by park name. |
| `list_trail_maps` |  | List the trail map PDFs cataloged in M.I.A.'s Maps module, optionally filtered by park name or state. |

### `materials` (2)

| Action | Destructive | Description |
|---|---|---|
| `add_material` |  | Add a raw Material to M.I.A.'s Workshop production pipeline (Materials tab). |
| `list_materials` |  | List the user's raw Materials in M.I.A.'s Workshop production pipeline. |

### `missions` (6)

| Action | Destructive | Description |
|---|---|---|
| `add_mission` |  | Start a new gamified Mission in M.I.A. (e.g. a 'Master Angler' mission for a fishing trip). Optionally link it to an existing Trip by name. |
| `add_objective` |  | Add an Objective to an existing Mission in M.I.A. — either a manually-tracked tally (e.g. 'catch 3 fish') or a target computed automatically from time spent on the mission's linked trip (e.g. 'spend 2 hours fishing'). |
| `complete_mission` |  | Mark an existing Mission as completed in M.I.A. by name. |
| `delete_mission` | Yes | Delete an existing Mission in M.I.A. by name. |
| `list_missions` |  | List the user's Missions in M.I.A., including each objective's progress. |
| `log_mission_progress` |  | Log progress toward a tally-type Objective on a Mission in M.I.A. — e.g. recording a catch, a species identified, or any other manually-counted goal. Only works for tally-type objectives; trip_duration_hours objectives track themselves automatically and never need this. |

### `notes` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_note` |  | Add a new journal/note entry in M.I.A.'s Notes module. |
| `delete_note` | Yes | Delete an existing journal/note entry in M.I.A.'s Notes module by its title. |
| `list_notes` |  | List or search the user's journal/note entries in M.I.A.'s Notes module. Leave query empty to list everything, most recently updated first. |

### `power` (1)

| Action | Destructive | Description |
|---|---|---|
| `get_power_status` |  | Get this device's current battery/power status. |

### `products` (2)

| Action | Destructive | Description |
|---|---|---|
| `add_product` |  | Add a finished Product to M.I.A.'s Workshop production pipeline (Products tab). |
| `list_products` |  | List the user's finished Products in M.I.A.'s Workshop production pipeline. |

### `projects` (7)

| Action | Destructive | Description |
|---|---|---|
| `add_project` |  | Start a new Project (a container for tasks) in M.I.A.'s Project Manager tool. |
| `add_task` |  | Add a new Task under an existing Project in M.I.A.'s Project Manager tool. |
| `delete_project` | Yes | Delete an existing Project (and unlink, but not delete, its Tasks) in M.I.A. by name. |
| `delete_task` | Yes | Delete an existing Task in M.I.A. by title. |
| `list_projects` |  | List the user's Projects in M.I.A.'s Project Manager tool. |
| `list_tasks` |  | List the user's Tasks in M.I.A., optionally filtered to one Project by name. |
| `mark_task_done` |  | Mark an existing Task as done (complete) or not done in M.I.A. by title. |

### `security` (4)

| Action | Destructive | Description |
|---|---|---|
| `calculate_subnet` |  | Calculate subnet/CIDR details (network address, broadcast, netmask, usable host range) for an IPv4 or IPv6 CIDR. |
| `check_password_strength` |  | Estimate a password's strength (entropy-based rating and warnings). For a real account password, prefer M.I.A.'s Field Kit Security tab (a masked input field) over pasting it into chat — chat history isn't masked/hidden the way a password field is. |
| `identify_hash` |  | Identify the likely algorithm(s) for a hash string (e.g. bcrypt, MD5, SHA-256) by its format. |
| `scan_ports` |  | Quickly check whether 3 common ports (22 SSH, 80 HTTP, 443 HTTPS) are open on a host. This is a fast, limited check — for a fuller scan of more ports, use M.I.A.'s Field Kit Security tab instead. |

### `system` (7)

| Action | Destructive | Description |
|---|---|---|
| `get_device_profile` |  | Tell the user which M.I.A. EDITION (hardware/software variant) this device is running: Core (Pi 5 + AI HAT+ 2 field edition) or Home (desktop workstation edition). This is about the device/installation itself, NOT about user accounts — use list_profiles for the people set up on this device. |
| `get_system_health` |  | Get a live snapshot of this device's system health: CPU, memory, disk, temperature, and network usage. |
| `list_profiles` |  | List the user ACCOUNTS/PEOPLE set up on this M.I.A. device (e.g. 'Zac', 'Guest'). This is about user accounts, NOT the device's Core/Home edition setting — use get_device_profile for that. |
| `open_module` |  | Open/navigate to a M.I.A. module by its module_id. |
| `recall_recent_activity` |  | Look up what the user has recently done in M.I.A. (modules opened, notifications, profile switches), optionally filtered by a keyword. Use this for questions like 'what have I been doing' or 'what did I do with notes recently'. |
| `set_birthday` |  | Remember the current user's own birthday, so M.I.A. can recognize and celebrate it. Use this whenever the user tells you their birthday in conversation — do not ask for it unprompted. |
| `set_theme` |  | Change M.I.A.'s visual theme. |

### `toolbox` (2)

| Action | Destructive | Description |
|---|---|---|
| `calculate_ohms_law` |  | Solve Ohm's Law (V = I x R) for voltage, current, or resistance, given the other two values, using M.I.A.'s Ohm's Law calculator. |
| `convert_units` |  | Convert a numeric value between two units of measurement using M.I.A.'s Unit Converter (length, area, volume, weight, temperature, speed, pressure, energy, power, time, data storage, angle, or fuel economy). Unit names can be everyday words (e.g. 'miles', 'celsius') — no need for exact formatting. |

### `waypoints` (5)

| Action | Destructive | Description |
|---|---|---|
| `add_waypoint` |  | Save a new named waypoint (location) in M.I.A.'s Navigation module. |
| `delete_waypoint` | Yes | Delete an existing saved waypoint in M.I.A.'s Navigation module by name. |
| `get_sun_moon_info` |  | Get today's sunrise/sunset times and moon phase for a saved waypoint's location — real survival-relevant info (how much daylight is left, moon phase for night navigation). |
| `list_waypoints` |  | List or search the user's saved waypoints (named locations) in M.I.A.'s Navigation module. |
| `waypoint_distance` |  | Get the distance and compass bearing between two of the user's saved waypoints, by name. |

## Capabilities named in the vision but not built yet

Per `docs/VISION.md`'s companion-philosophy update — listed here so
"is X a capability" has one place to check regardless of whether the
answer is yes or not-yet: Intelligent UI Navigation (the GUI opening/
filling a form live while talking), Smart Suggestions (proactive
recommendations beyond the 3 daily-occasion checks above), Memory
Palace (categorized/cross-referenced memory, today's `UserMemory` is
flat), Workout, Kitchen, Finance, Relationship Profiles, Pet Profiles,
interactive onboarding, the modular tutorial system, and multi-platform/
browser/XR frontends. None of these should be assumed present in the
system prompt or anywhere else until they're actually built and this
document is updated.
