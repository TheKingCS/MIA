# Assistant Capabilities — the full record

This is the single source of truth for "what can MIA's Assistant
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
- **Spoken output.** Both the full-screen Assistant module and the
  character panel sidebar (2026-07-18: gained full voice parity) speak
  every reply aloud via Piper TTS, and the Home dashboard speaks its
  startup briefing once per launch. A Stop button on both surfaces
  interrupts playback mid-sentence
  (`core/voice_manager.py`'s `stop_playback()`). Voice is selectable in
  Settings among a curated 5-voice catalog (`core/voice_catalog.py`).
- **Voice input.** Push-to-talk in both the full Assistant module and
  the sidebar transcribes speech via Vosk and sends it as if typed (the
  sidebar's is on-screen-click only — see `gui/character_panel.py`'s
  docstring for why it doesn't share a GPIO `PushToTalkTrigger` with
  the full module).
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

- **Online/offline awareness** (2026-09-27, `core/connectivity.py`).
  A background check (never blocking a turn) tracks whether the
  internet is reachable. Conversational replies get a short system-prompt
  line with the current state; when offline it lists what still works
  and what must wait. The `get_connectivity_status` action answers "are
  you online?" / "what can you do without internet?". The online-only
  list (`ONLINE_ONLY_CAPABILITIES`) is: bank sync, phone notifications,
  new map downloads, adding trail maps from a web link, and phone access
  away from home. **Add to that list whenever a feature starts making
  network requests**, or MIA will promise it while offline. End-user
  help: `docs/user_help/offline_and_online.md`.

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
- **2026-09-10 addendum — name a new per-module doc file after its
  `module_id`, not a prettier name.** `device_help_manager.py` used to
  give the module-name confidence bonus only to the auto-generated
  one-line module description, never to `docs/user_help/*.md` content —
  so a query naming a module always preferred the terse one-liner over
  a real, richer doc chunk, even when one existed. Fixed by keying the
  same bonus off a filename convention: a file named exactly
  `<module_id>.md` (e.g. `workout.md` for module_id `"workout"`) has
  every one of its chunks treated as being about that module. A shared
  file covering several modules at once (`organizing.md`,
  `system_and_files.md`) deliberately doesn't get this — keep those for
  genuinely small/system-tier modules without much real workflow
  content of their own.
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

## How a request reaches a tool (2026-09-27 conversational audit)

A tool can only be used if it's *offered* to the model for that
message. `AssistantActionRegistry.matching_actions(prompt, context)`
offers a domain's tools when the prompt contains:
1. one of an action's `trigger_phrases` (exact phrase),
2. one of the domain's registered vocabulary words
   (`register_domain_keywords()`, whole words only), or
3. the name of one of the user's own records in that domain
   (`register_entity_names()`), matched on its head noun ("the mower"
   → "Riding Mower", "the peppers" → "Pepper Plants"). Domains whose
   names share words (debts: "Truck Loan") require every word.

How-to questions ("how do I…", "where do I…", "how does X work",
"what does the X module do") skip tools entirely and get help-doc
grounding (`looks_like_how_to_question()`).

Handlers find records with `core/assistant_lookup.resolve_by_name()`:
the user's own words, one unambiguous match only, otherwise ask or list
what exists. Destructive actions keep exact names.

**Keep it measured, not guessed.** `tests/assistant_routing_corpus.py`
holds realistic requests with the tool each must reach, plus small talk
that must stay tool-free; `tests/test_assistant_routing.py` enforces it.
Add a line there whenever MIA misses something. The live model's half
is `tests/live_model_check.py` (run on the owner's machine). Full
findings: `docs/ASSISTANT_AUDIT.md`.

## Tool registry (180 actions, 40 domains, as of 2026-09-28)

**Added 2026-09-27** (`core/assistant_domain_actions.py`):
- maintenance: `update_maintenance_asset`, `get_maintenance_asset`,
  `add_asset_note`. Greenhouse/garden plants are Maintenance assets
  in the Garden/Plant category.
- debts: `add_debt`, `update_debt`, `list_debts`,
  `record_debt_payment`, `get_debt_payoff_plan`
- budget: `set_budget_target`
- kitchen: `add_recipe`, `list_recipes`, `suggest_recipes`, `log_meal`
- groceries: `add_grocery_item`, `list_grocery_list`,
  `check_off_grocery_item`, `add_recipe_ingredients_to_grocery_list`,
  `add_pantry_item`, `update_pantry_item`, `list_pantry`
- components/materials/products: `adjust_component_quantity`,
  `adjust_material_quantity`, `update_material`, `adjust_product_stock`

**Added 2026-09-28**: `list_build_purchases` (homestead_costs): what was
bought for a build, from filed receipts' line items.

**Added 2026-09-28**: `resume_message_topic` (communication): ends the
break MIA takes from a kind of message the user kept dismissing.

**Added 2026-09-28**: `remind_when_online` (`core/online_watch.py`,
delivered when the connection returns) and `get_journal_reflection`
(`core/journal_reflection.py`, the weekly reflection; a private turn).

**Added 2026-09-28** (sorting bank charges, `core/assistant_tagging_actions.py`):
`list_untagged_charges`, `tag_charge` (domain `business_tags`,
`core/business_tagging.py`).

**Added 2026-09-28** (textbook tutor, `core/assistant_textbook_actions.py`):
`list_textbooks`, `search_textbook`, `make_textbook_course` (domain
`textbooks`). Studying and quizzing are conversation modes (Study, Quiz;
`core/textbook_study.py` puts the book's own passages, with page
numbers, into the system message), not tools.

**Added 2026-09-28** (document inbox, `core/assistant_inbox_actions.py`):
`list_inbox`, `file_inbox_item`, `dismiss_inbox_item` (domain `inbox`).
Filing by voice adds every maintenance step found in a manual unless
the owner says "without the tasks".

**Added 2026-09-28** (Finance #3, same file): `log_business_use`,
`get_business_use` (domain `business_use`, `core/business_use.py`).

**Added 2026-10-01** (`core/assistant_email_actions.py`, accounts stage
3): `draft_email` (domain `email`) writes a draft the person reviews.
Deliberately no tool sends; only a Send button does.

**Added 2026-10-01** (`core/assistant_focus_actions.py`, accounts stage
2): `set_app_focus` ("switch me to student mode"), `set_app_visibility`
("hide the Lab from my apps"), `get_app_focus` (domain `apps`). Each
changes only the speaker's own Apps screen.

**Added 2026-09-28** (`core/assistant_homestead_actions.py`, Finance #2):
`log_build_expense`, `record_tool_purchase`, `get_build_costs`,
`get_tool_costs`, `set_build_budget` (domain `homestead_costs`); and
`complete_maintenance_task` takes an optional `cost`, logged as a
Maintenance expense tagged to the item.

**Also added 2026-09-27** (`core/assistant_comm_actions.py`, Cognitive
Extension slice C): `get_held_back_messages` ("what didn't you tell me
today?") and `set_message_limit` (domain `communication`).

**Also added 2026-09-27** (`core/assistant_why_actions.py`, Cognitive
Extension slice B): `link_my_reason`, `show_my_why`,
`unlink_my_reason`, `mark_goal_achieved` (domain `why`, trigger phrases
only: goal names are everyday words, so they're never matched by name).
The Perspective mode ("remind me why") answers from
`core/why_graph.py`'s fact sheet with no tools offered.

**Also added 2026-09-27** (`core/talk_it_out.py`, Cognitive Extension
slice A): `read_private_journal`, `get_journal_themes` (domain
`private_journal`; they answer "locked" until the journal is unlocked,
and their turns are never written to conversations.json). Conversation
modes are a fourth path beside action/info/teaching: see
`core/conversation_modes.py` and `docs/COGNITIVE_EXTENSION_PROPOSAL.md`.
The safety floor (`core/safety_floor.py`) runs before all of them.

**Also added 2026-09-27** (`core/assistant_life_actions.py`):
- workout: `log_workout` (parses "3x10 squats at 185"),
  `get_workout_summary`, `get_personal_record`
- relationships: `add_person`, `update_person` (birthday, favorite
  things, gift ideas, dated notes), `get_person`,
  `list_upcoming_birthdays`, `add_pet`, `update_pet` (dated medical
  history), `get_pet`
- household: `list_household_routines`, `log_household_routine`,
  `add_household_routine` (recurring mission templates, category
  "Household")
- classroom: `add_course`, `add_lesson`, `complete_lesson`,
  `add_lesson_notes`, `get_learning_progress`

The per-domain list below predates these additions (last full pass
2026-07-18).

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
| `add_alarm` |  | Create a new alarm in MIA |
| `delete_alarm` | Yes | Delete an existing alarm in MIA by its label. |
| `list_alarms` |  | List the user's current alarms in MIA |

### `calendar` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_calendar_event` |  | Add a new event to MIA's Calendar. |
| `delete_calendar_event` | Yes | Delete an existing Calendar event in MIA by its title. |
| `list_calendar_events` |  | List the user's upcoming/scheduled Calendar events in MIA — what's coming up today, this week, or on any date. Not for past activity — see recall_recent_activity for that. |

### `components` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_component` |  | Add a new electronic component to MIA's Workshop & Electronics component database. |
| `delete_component` | Yes | Delete an existing electronic component in MIA by name. |
| `list_components` |  | List or search the user's electronic components in MIA |

### `expeditions` (11)

| Action | Destructive | Description |
|---|---|---|
| `add_expedition` |  | Start a new Expedition (a dated outing that can hold multiple trips) in MIA's Expeditions module. |
| `add_gear_item` |  | Add an item to a Trip's gear checklist in MIA |
| `add_trip` |  | Add a new Trip (one hike, paddle, ride, fishing trip, etc.) under an existing Expedition in MIA |
| `add_trip_log_entry` |  | Add a dated journal/log entry to a specific Trip in MIA, optionally recording weather/conditions. Use this instead of add_note when the user is logging something about a specific trip/outing (arriving somewhere, conditions encountered, etc.), not a general-purpose note. |
| `delete_expedition` | Yes | Delete an existing Expedition in MIA by name. |
| `delete_trip` | Yes | Delete an existing Trip in MIA by name. |
| `get_trip_summary` |  | Get a Trip's logged distance, average speed, and planned route distance in MIA |
| `list_expeditions` |  | List the user's Expeditions in MIA |
| `list_trips` |  | List the user's Trips in MIA, optionally filtered to one Expedition by name. |
| `recall_expedition` |  | Get a detailed recap of ONE Expedition in MIA's Memories: duration, distance/pace per activity type, waypoint categories visited, latest journal/conditions entry, and photo count. This is a single-Expedition summary, NOT a bare list — use list_expeditions instead for 'what expeditions do I have'-style questions. Leave name empty for the most recent Expedition. |
| `toggle_gear_packed` |  | Mark a gear checklist item on a Trip as packed or not packed (toggles its current state). |

### `field_kit` (2)

| Action | Destructive | Description |
|---|---|---|
| `list_connected_devices` |  | List currently connected external USB storage and serial devices in MIA's Field Kit. |
| `list_scripts` |  | List the user's saved scripts in MIA's Field Kit script library. |

### `inventory` (4)

| Action | Destructive | Description |
|---|---|---|
| `add_inventory_item` |  | Add a new item to MIA's general Inventory tool. |
| `adjust_inventory_quantity` | Yes | Change the quantity of an existing inventory item by an amount (positive to add more, negative to use/remove some), e.g. 'I used 5 M3 bolts' -> delta -5. Quantity never goes below zero. Use add_inventory_item instead for a brand-new item. |
| `delete_inventory_item` | Yes | Remove an item entirely from MIA's Inventory tool by name. |
| `list_inventory` |  | List or search MIA's Inventory tool, including quantities. Use this to answer 'how many X do I have' questions about inventory items. Leave query empty to list everything. |

### `jobs` (4)

| Action | Destructive | Description |
|---|---|---|
| `add_job` |  | Start a new production Job in MIA's Workshop pipeline. |
| `consume_material` |  | Record that an existing Job consumed some quantity of an existing Material — deducts that quantity from the Material's own stock automatically. |
| `list_jobs` |  | List the user's production Jobs in MIA's Workshop pipeline. |
| `produce_product` |  | Record that an existing Job produced some quantity of an existing Product — credits that quantity onto the Product's own stock automatically. |

### `ledger` (2)

| Action | Destructive | Description |
|---|---|---|
| `get_ledger_summary` |  | Get the user's total revenue, expenses, and net profit from MIA's Workshop Ledger. |
| `record_sale` |  | Record a sale of an existing Product in MIA's Workshop Ledger — deducts the sold quantity from the Product's stock and logs the revenue. |

### `maps` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_trail_map_from_url` |  | Download a trail map PDF from a direct URL and add it to MIA's trail map catalog. Not for offline tile/basemap downloads — those are only available from the Maps module's own UI, since they can take too long to run as part of a chat reply. |
| `delete_trail_map` | Yes | Delete a cataloged trail map PDF from MIA's Maps module by park name. |
| `list_trail_maps` |  | List the trail map PDFs cataloged in MIA's Maps module, optionally filtered by park name or state. |

### `materials` (2)

| Action | Destructive | Description |
|---|---|---|
| `add_material` |  | Add a raw Material to MIA's Workshop production pipeline (Materials tab). |
| `list_materials` |  | List the user's raw Materials in MIA's Workshop production pipeline. |

### `missions` (6)

| Action | Destructive | Description |
|---|---|---|
| `add_mission` |  | Start a new gamified Mission in MIA (e.g. a 'Master Angler' mission for a fishing trip). Optionally link it to an existing Trip by name. |
| `add_objective` |  | Add an Objective to an existing Mission in MIA — either a manually-tracked tally (e.g. 'catch 3 fish') or a target computed automatically from time spent on the mission's linked trip (e.g. 'spend 2 hours fishing'). |
| `complete_mission` |  | Mark an existing Mission as completed in MIA by name. |
| `delete_mission` | Yes | Delete an existing Mission in MIA by name. |
| `list_missions` |  | List the user's Missions in MIA, including each objective's progress. |
| `log_mission_progress` |  | Log progress toward a tally-type Objective on a Mission in MIA — e.g. recording a catch, a species identified, or any other manually-counted goal. Only works for tally-type objectives; trip_duration_hours objectives track themselves automatically and never need this. |

### `notes` (3)

| Action | Destructive | Description |
|---|---|---|
| `add_note` |  | Add a new journal/note entry in MIA's Notes module. |
| `delete_note` | Yes | Delete an existing journal/note entry in MIA's Notes module by its title. |
| `list_notes` |  | List or search the user's journal/note entries in MIA's Notes module. Leave query empty to list everything, most recently updated first. |

### `power` (1)

| Action | Destructive | Description |
|---|---|---|
| `get_power_status` |  | Get this device's current battery/power status. |

### `products` (2)

| Action | Destructive | Description |
|---|---|---|
| `add_product` |  | Add a finished Product to MIA's Workshop production pipeline (Products tab). |
| `list_products` |  | List the user's finished Products in MIA's Workshop production pipeline. |

### `projects` (7)

| Action | Destructive | Description |
|---|---|---|
| `add_project` |  | Start a new Project (a container for tasks) in MIA's Project Manager tool. |
| `add_task` |  | Add a new Task under an existing Project in MIA's Project Manager tool. |
| `delete_project` | Yes | Delete an existing Project (and unlink, but not delete, its Tasks) in MIA by name. |
| `delete_task` | Yes | Delete an existing Task in MIA by title. |
| `list_projects` |  | List the user's Projects in MIA's Project Manager tool. |
| `list_tasks` |  | List the user's Tasks in MIA, optionally filtered to one Project by name. |
| `mark_task_done` |  | Mark an existing Task as done (complete) or not done in MIA by title. |

### `security` (4)

| Action | Destructive | Description |
|---|---|---|
| `calculate_subnet` |  | Calculate subnet/CIDR details (network address, broadcast, netmask, usable host range) for an IPv4 or IPv6 CIDR. |
| `check_password_strength` |  | Estimate a password's strength (entropy-based rating and warnings). For a real account password, prefer MIA's Field Kit Security tab (a masked input field) over pasting it into chat — chat history isn't masked/hidden the way a password field is. |
| `identify_hash` |  | Identify the likely algorithm(s) for a hash string (e.g. bcrypt, MD5, SHA-256) by its format. |
| `scan_ports` |  | Quickly check whether 3 common ports (22 SSH, 80 HTTP, 443 HTTPS) are open on a host. This is a fast, limited check — for a fuller scan of more ports, use MIA's Field Kit Security tab instead. |

### `system` (7)

| Action | Destructive | Description |
|---|---|---|
| `get_device_profile` |  | Tell the user which MIA EDITION (hardware/software variant) this device is running: Core (Pi 5 + AI HAT+ 2 field edition) or Home (desktop workstation edition). This is about the device/installation itself, NOT about user accounts — use list_profiles for the people set up on this device. |
| `get_system_health` |  | Get a live snapshot of this device's system health: CPU, memory, disk, temperature, and network usage. |
| `list_profiles` |  | List the user ACCOUNTS/PEOPLE set up on this MIA device (e.g. 'Zac', 'Guest'). This is about user accounts, NOT the device's Core/Home edition setting — use get_device_profile for that. |
| `open_module` |  | Open/navigate to a MIA module by its module_id. |
| `recall_recent_activity` |  | Look up what the user has recently done in MIA (modules opened, notifications, profile switches), optionally filtered by a keyword. Use this for questions like 'what have I been doing' or 'what did I do with notes recently'. |
| `set_birthday` |  | Remember the current user's own birthday, so MIA can recognize and celebrate it. Use this whenever the user tells you their birthday in conversation — do not ask for it unprompted. |
| `set_theme` |  | Change MIA's visual theme. |

### `toolbox` (2)

| Action | Destructive | Description |
|---|---|---|
| `calculate_ohms_law` |  | Solve Ohm's Law (V = I x R) for voltage, current, or resistance, given the other two values, using MIA's Ohm's Law calculator. |
| `convert_units` |  | Convert a numeric value between two units of measurement using MIA's Unit Converter (length, area, volume, weight, temperature, speed, pressure, energy, power, time, data storage, angle, or fuel economy). Unit names can be everyday words (e.g. 'miles', 'celsius') — no need for exact formatting. |

### `waypoints` (5)

| Action | Destructive | Description |
|---|---|---|
| `add_waypoint` |  | Save a new named waypoint (location) in MIA's Navigation module. |
| `delete_waypoint` | Yes | Delete an existing saved waypoint in MIA's Navigation module by name. |
| `get_sun_moon_info` |  | Get today's sunrise/sunset times and moon phase for a saved waypoint's location — real survival-relevant info (how much daylight is left, moon phase for night navigation). |
| `list_waypoints` |  | List or search the user's saved waypoints (named locations) in MIA's Navigation module. |
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
