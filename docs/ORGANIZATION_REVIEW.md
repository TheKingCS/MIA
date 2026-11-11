# Organization review: what MIA holds, and how it could be grouped

*2026-11-11: Zac chose his own eight destinations (DEC-0153, `docs/specs/NAVIGATION.md`); the architecture is `docs/NAVIGATION_ARCHITECTURE.md`. This review's section 4 is superseded; its counts and per-app verdicts still hold.*

*Claude, 2026-11-10. A proposal for Zac. Nothing in the app has been
moved: the areas, the Nexus and every page are as they were. The
choices in section 6 are his.*

Zac, 2026-11-10: "so much of the foundation is laid ... but the
organization and kind of decluttering needs work. Right now MIA feels
like a collection of cool ideas and software when she should feel like
an advanced Intelligence. I like the nexus but I don't think 15
different areas makes sense."

This is the measurement behind an answer, then the answer.

## 1. How this was measured

- The areas and their apps were read from `core/web_areas.py` (the one
  place they're defined, DEC-0129).
- Every web page was opened in a headless browser **on the example
  data** (`docs/schema/*.example.json`), and its headings, controls,
  word count and errors were recorded. 99 page views, no script errors.
- For each app, the number of things MIA can do for it by voice (tools)
  was set beside the number of things its screen can do (action kinds).

What that can and can't tell: it shows what each screen offers and how
the whole is arranged. It doesn't show which screens Zac opens, or how
they look with his own data. "Thin" below means thin on the example
data. No screen was judged on its looks.

One fault turned up on the way: the Projects page failed on its example
data ("This page couldn't load"). The example was missing a field the
page reads; fixed in 45bfbc6a. The page worked on real data throughout.

## 2. What is there

| | Count |
|---|---|
| Portals in the Nexus | 16 (DEC-0129's fifteen areas, plus Kitchen, DEC-0130) |
| Apps and pages listed in areas | 83 |
| Things she can do by voice | 376 tools |
| Things the screens can do | 434 action kinds |
| Pages in `web/` that belong to no area | 21 |

Area sizes: Settings and Diagnostics 13, Personal 13, Recreation 11,
Finances 7, Business 6, Missions 6, Home 5, Security 5, Learning 5,
Communications 4, Garage 3, Plants and Animals 3, Health and Fitness 3,
Projects 3, **Kitchen 1, Browser 1**.

## 3. Why it reads as a collection

1. **The areas are uneven.** Two portals hold one app each; two hold
   thirteen. A portal that opens onto one app is a longer way to that
   app, and a hub of thirteen is a list again.
2. **Six apps live in more than one area** (Kitchen in three; Real
   Estate, Compliance, Workshop, Inbox and Skills in two). Each was put
   there on purpose (DEC-0129), but the effect is that the same card
   turns up in different rooms and no room feels like *the* place for it.
3. **Several areas are named for a kind of software, not a part of
   life.** Browser, Security, Communications, Projects and Settings
   describe what the program is. Home, Garage, Finances and Health
   describe Zac's life. Mixing the two is most of the "collection" feel.
4. **MIA herself is scattered.** What she is and how she answers (About,
   How MIA Answers) sit in Settings; what she noticed and what she tied
   together (Observations, Connections) sit in Personal; where she went
   wrong, what she changed and how she's running (Fix-It Log, Recent
   Changes, Diagnostics) sit in Settings again; her messages sit in
   Communications. Seven pages about the intelligence, in three areas,
   none of them called MIA.
5. **Several jobs are split across pages that grew one at a time:**
   - *Looking back and steering:* Journal, Kept, Operating Journal,
     Sunday Check-In, My Why, My Directions (six pages).
   - *Where I've been:* Memories, Memory Vault, World Map, My Places,
     Tracks (five).
   - *Maps:* Maps, Navigation, Trail Maps, Tracks (four).
   - *Readings:* The Lab, Sensors, Power, and the Greenhouse's water
     tab (four places a number from a sensor can live).
   - *The game:* Missions, Skills, Character, Reward Shop, Party, The
     Chronicle in Missions; Living Worlds in Recreation; The Dungeon in
     Finances.
   - *What reached me:* Communications, Notifications, Inbox.
6. **Personal is the drawer for whatever didn't fit**: the calendar, a
   radio station, files, photos, people, six reflective pages and two
   pages of MIA's own thinking.
7. **Twenty-one pages belong to no area.** Some are right not to
   (a recipe, an asset, a project plan: pages you reach from their
   app). Some are leftovers or redirects (`dashboard`, `finances`,
   `grow`, `maintenance`, `property`, `hub`, `nexus`). Some are for
   building her (`dev`, `dev-window`, `model-test`). And some are
   features with no door: **The Council** and **Made By MIA**.

None of this is broken. Every page loads and does something. The cost is
that finding a thing means knowing which of sixteen rooms it was filed
in, and that she appears as a tool in each room rather than as the one
who runs the house.

## 4. Proposed shape

Three layers instead of one ring of sixteen.

### Layer 1: MIA, always there (not a room)

- **Today**: the one thing, what needs you, the day's calendar. Calendar
  belongs here, not in Personal.
- **Talk** and **Search**, on every page as now.
- **One page called MIA**, with what is now spread over seven: what she
  is, how she answers, what she's noticed, what she's tied together,
  what she's said to you, what she's changed (with Undo), where she
  went wrong, how she's running.
- **Her browser** as one of her abilities (reached from her page and
  from Talk), not a room of Zac's life.

This is the part that makes her read as an intelligence: one place that
is *her*, and her judgment at the top of every room (what needs you
here), instead of a card among cards.

### Layer 2: eight rooms, each app in exactly one

| Room | Holds | From today's |
|---|---|---|
| **Home** | Household, Home Upkeep, Kitchen, Power, the cameras, Trade Master | Home, Kitchen, Security (cameras) |
| **Land** | Greenhouse, Chickens, Pets | Plants and Animals |
| **Shop** | Garage, Workshop, Projects, The Lab (with Sensors' readings), Toolbox, Look, Orders & Quotes, Labels, Show Off | Garage, Projects, Business |
| **Money** | Money, Freedom, The Dungeon, Insurance, Real Estate, Compliance, Inbox (paperwork) | Finances, Business |
| **Body** | Health, Workout | Health and Fitness |
| **Out There** | Expeditions, one Maps app (map, navigation, trail maps, tracks), one "been there" app (Memories, World Map, My Places), Play, Music, Good News Radio, Living Worlds | Recreation, Personal |
| **Growth** | Missions, Skills, Character, Reward Shop, Party, The Chronicle, Classroom, Knowledge (with Look It Up), learning paths (Guitar) | Missions, Learning |
| **Me** | Journal, Kept, Operating Journal with Why / Directions / Sunday Check-In as one "how I mean to live" app, People, Files, Memory Vault, ID Wallet, Passwords | Personal, Security |

An app has one home. Where it matters elsewhere it's *linked*, not
filed twice: Body shows today's meals from Kitchen; Money shows what the
Workshop earned. That is a line on the room's page, drawn from the same
data, not a second card.

### Layer 3: the machine (under Settings, no portal)

Settings, Profile, Theme Studio, Portal Pictures, Connect Apps, Sensors
(setting them up), Sign-Ins, Your Data, Apps, Field Kit, Diagnostics.
Things you set once or check when something's wrong.

### What this changes and what it keeps

- Sixteen portals become eight, of similar weight (2 to 9 things each).
- Every app ID, route, page and store stays as it is. Only
  `core/web_areas.py` and the pages that are merged change, and a
  merged page keeps its old address as a way in.
- The Nexus stays. It has fewer, fuller portals.
- It reverses two of Zac's own decisions from 2026-11-08: fifteen areas
  with apps in more than one (DEC-0129), and Kitchen's own portal
  (DEC-0130). That is his to do or not.
- It fits the saved spec `docs/specs/SELF_ORGANIZATION.md` (no second
  registry: the areas file stays the one place) and would be the
  starting arrangement that spec lets her tend afterwards.

## 5. Each app: what it's for, and whether its screen does it

Read from the screens on example data. **Works**: the screen shows the
state and has controls for its main jobs. **Voice-heavy**: far more can
be done by voice than on the screen (the gaps are each decided in
`work/parity.json`; this only says where they cluster). **Read-only**:
shows, doesn't act. **Thin**: little on the screen. **Fold**: its job
overlaps a neighbour's.

**Home**

| App | For | Screen | Verdict |
|---|---|---|---|
| Household | routines that keep the house running | routines with Did It, pause, add | Works |
| Home Upkeep | the house and appliances, cared for | a tab of Real Estate | Works; it is Real Estate's page under another name, which is confusing from Home |
| Kitchen | meals, recipes, pantry, groceries | seven tabs, 20 actions | Works; the fullest app in MIA |
| Power | energy sources and battery | sources, readings | Works; small |
| Security | the cameras | four tiles, pictures, set-up | Works for cameras; the area's name promises more than cameras |
| Trade Master | any job, step by step | jobs and a walk-through | Works; long page, could open on "what are you doing?" |

**Land**

| App | For | Screen | Verdict |
|---|---|---|---|
| Greenhouse | what to grow and what needs doing | seven tabs, Needs You first | Works; the model for a room's page |
| Chickens | eggs and the flock | quick counts, cartons | Works |
| Pets | animals, care, vet visits | People, filtered | Works; thin |

**Shop**

| App | For | Screen | Verdict |
|---|---|---|---|
| Garage | vehicles and gear kept ready | assets, due lists | Voice-heavy (16 by voice, 3 on screen) |
| Workshop | parts, jobs, products | seven tabs | Works |
| Projects | plans, budgets, tasks | projects with money and tasks | Works; its projects are the Workshop's builds and jobs, seen as plans |
| The Lab | experiments and readings | series and readings | Works; Fold with Sensors |
| Toolbox | calculators, timers | many small tools | Works |
| Look | show her something | photo and three questions | Works; a button in Talk more than an app |
| Orders & Quotes | customers, quotes, orders | four tabs | Works |
| Labels | print a label | one form | Works; belongs inside Workshop |
| Show Off | what you've made, to share | a slideshow | Thin; belongs inside Workshop |

**Money**

| App | For | Screen | Verdict |
|---|---|---|---|
| Money | where it goes | seven tabs | Voice-heavy (31 by voice, 5 on screen): mostly a display |
| Freedom | the way out, in numbers | the fund, the builds, why | Works |
| The Dungeon | work as a game | runs, loot, hard mode | Works |
| Insurance | covered, for less | policies, shopping | Works |
| Real Estate | properties | properties and upkeep | Works |
| Compliance | every deadline | overdue first, verify | Works |
| Inbox | paperwork, handled | capture and file | Works |

**Body**

| App | For | Screen | Verdict |
|---|---|---|---|
| Health | sleep, visits, medications | logs and records | Works |
| Workout | training | seven tabs | Works |

**Out There**

| App | For | Screen | Verdict |
|---|---|---|---|
| Expeditions | plan the trip | packing, plans | Works |
| Maps | know the ground | one map | Fold: four map pages |
| Navigation | find the way | saved routes | Fold |
| Trail Maps | park PDFs offline | list and add | Fold |
| Tracks | walks and drives from GPX | list | Fold |
| Memories | remember the trip | one trip, read-only | Voice-heavy (14 by voice, none on screen) |
| World Map | everywhere you've been | a map, "I'm Here" | Fold with Memories and My Places |
| My Places | places and quests there | list, add | Fold |
| Play | games and sports, counted | log a game | Works; thin |
| Music | your music | library, playlists, the shared player | Works (player made to carry across pages today) |
| Good News Radio | what went right | station, stories, follow | Works (built out 2026-11-10) |
| Living Worlds | campaigns and character | worlds and quests | Works |

**Growth**

| App | For | Screen | Verdict |
|---|---|---|---|
| Missions | what to do next | five tabs | Works |
| Skills | levels earned by doing | the tree | Read-only, rightly |
| Character | your story so far | crest, buffs | Read-only |
| Reward Shop | spend what you earn | buy, add | Works |
| Party | raids and quests | raids | Works |
| The Chronicle | your story told back | weekly, yearly | Read-only; Fold with Character |
| Classroom | what you're learning | subjects, courses, books | Works |
| Knowledge | the offline library | a search box, packs, plans shelf | Thin until searched; Fold with Look It Up |
| Look It Up | search the web | a search box | Fold with Knowledge |
| Guitar | a learning path | tuner, stages | Works; should sit with other paths as they come |

**Me**

| App | For | Screen | Verdict |
|---|---|---|---|
| Journal | write it down | entries, talk it out | Works |
| Kept | what you said you'd do | list, done, forget | Works; Fold candidates below |
| Operating Journal | how you mean to live | lines, weekly rating | Fold: with Why, Directions, Check-In |
| My Why | what it's all for | goals linked | Fold |
| My Directions | what you're steering by | directions | Fold |
| Sunday Check-In | the week, looked back on | one debrief | Fold |
| People | the ones who matter | birthdays, people | Voice-heavy (7 by voice, 1 on screen) |
| Files | your files | upload, folders | Works |
| Memory Vault | photos kept safe | photos, set-up | Works |
| ID Wallet | IDs and cards | cards with photos | Works |
| Passwords | every login, locked | locked until opened | Works |

**MIA (layer 1)**

| Page | For | Screen | Verdict |
|---|---|---|---|
| Home / Nexus | where you arrive | the portals, each with its count of what needs you | Works; she counts there but says nothing |
| MIA Assistant | talk with her | chat, history | Works |
| About MIA | what she is | long read | Read-only; Fold into the MIA page |
| How MIA Answers | length, layout, tone | choices | Works; Fold |
| Observations | what she noticed | list with why | Read-only; Fold |
| Connections | what she tied together | list, don't raise | Works; Fold |
| Communications | her messages, email drafts, people | one screen | Works |
| Notifications | what she told you | list, reminders | Fold with Communications |
| Fix-It Log | where she stumbled | open, worst first | Works; Fold |
| Recent Changes | what changed, with Undo | list | Works; Fold |
| Diagnostics | how she's doing | checks | Works; Fold |
| Browser | she browses, you approve | controls, taught tasks | Works |
| The Council | (no door) | one box, "nobody's ready" | Decide: give it a door or remove it |
| Made By MIA | screens she builds from a file | bring a file | Decide: this is the seed of the self-organization spec; no door today |

**The machine (layer 3)**

Settings, Profile, Theme Studio, Portal Pictures, Connect Apps, Sensors,
Sign-Ins, Your Data, Apps, Field Kit: each does its one job. Settings is
the longest page in MIA (30 fields on one scroll) and would read better
in sections. Field Kit is voice-only for actions (6 by voice, none on
screen).

### What the table adds up to

- Most screens do their job. The decluttering is in how they're
  grouped, and in about twenty pages that should be tabs of a
  neighbour, not in rebuilding apps.
- Four screens are mostly displays for things only voice can change:
  Money, Garage, Memories, People. Those are the parity gaps most worth
  closing first.
- The pattern worth copying is Greenhouse and Compliance: the page opens
  on what needs you, then the rest. A room's page should do the same
  for the whole room.

## 6. Decisions for Zac

1. **Fewer rooms?** Eight rooms plus MIA's own page and the machine
   under Settings, as in section 4, or a different cut. This replaces
   DEC-0129's fifteen.
2. **One home per app?** Today an app can be in several areas
   (DEC-0129). The proposal is one home and links from other rooms.
3. **Kitchen's portal** (DEC-0130): keep it as its own, or let Kitchen
   be the first thing in Home.
4. **A page that is MIA.** Bring the seven pages about her together.
5. **Merges.** Which of the folds to do: Maps (4 into 1), "been there"
   (3 into 1), "how I mean to live" (4 into 1), Knowledge with Look It
   Up, Notifications into Communications, Labels and Show Off into
   Workshop. Each can be done on its own.
6. **The Council and Made By MIA**: a door, or out.
7. **Names.** Land, Shop, Body, Out There, Growth and Me are my
   placeholders. The names are his.

If he says yes to 1 and 2, the first step is small and undoable: change
`core/web_areas.py`, and the Nexus, the sidebar, the hubs and the Apps
page all follow from it. The merges come after, one at a time.
