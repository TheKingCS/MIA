# MIA's navigation: eight destinations, one owner each

*Claude, 2026-11-11, answering Zac's spec `docs/specs/NAVIGATION.md`
(stages 1 to 3). Decision: DEC-0153. Status: **approved by Zac the same
day, with the answers below; steps 1, 2, 4 and 5 are built.** It replaces
the proposal in section 4 of `docs/ORGANIZATION_REVIEW.md` (Zac chose his
own eight). The facts and per-app verdicts in that review still hold.*

## Zac's answers (2026-11-11)

1. **Weather:** yes, she may fetch it online.
2. **Agent Activity:** all of it, both what MIA did on her own and the
   development team's agents.
3. **The Nexus:** the third screen on the glasses. On the phone and the
   PC it is the screen that opens when you open Living Worlds under
   Recreation, to move between the worlds. It has no sidebar entry.
4. **Toolbox, Trade Master, the Lab, Field Kit:** he isn't sure what's in
   them. They stay where section 4.6 proposed (Garage, Garage, Smart
   Devices, Smart Devices) until he has seen them.
5. **Personal Tools** holds the journal, the calendar and the like,
   Memories included. No split.

He also decided three things beyond the questions:

- **Cameras** go in Smart Devices. The app now shows as "Cameras"; its id
  `security` and its page stay.
- **Upkeep becomes scheduled missions.** Home upkeep, like maintenance
  for cars and tools, is scheduled missions. Each one is attached to its
  property or asset, appears in the Calendar, and appears on a new **Your
  Week** tab on the Dashboard that shows what is due this week.
- **Businesses:** a subdashboard under Finances with a quick view of
  each business. Clicking a business opens its own dashboard. **Orders
  and quotes** become a section under each business, holding only that
  business's own.

## What's built (2026-11-11)

- **Step 1, the registry, hubs and sidebar.** `core/web_areas.py` holds
  the eight and their subdashboards: `parent`, `shortcuts`, `OLD_IDS`,
  `resolve`. Each item has one owner, and
  `tests/test_web_areas.py` fails on a second owner or an unowned page.
  A hub shows its subdashboards first, then its apps, its shortcuts and
  the way back up. The sidebar lists the Dashboard, then the
  destinations, each opening to its subdashboards and apps. The Apps page
  lists every destination and subdashboard. The phone's bottom bar is
  Dashboard, Home, Apps and Search. MIA opens on the Dashboard in every
  look.
- **Step 2, voice.** "Take me to the homestead", "open AI tools", "go to
  the dashboard" and the old names ("plants and animals") all resolve.
  "Open living worlds" opens the Nexus.
- **Step 4, the glasses.** Their three screens are the orb; the menu
  (the eight destinations, then subdashboards, then apps, with Back going
  up one level); and the Nexus (the stories). "Open the greenhouse" steps
  into Homestead.
- **Step 5, the Nexus as Living Worlds.** Each campaign has a portal, the
  ones in play first, plus "Make a World". Portal Pictures puts paintings
  on stories' portals, and the painting tools speak of stories.

**Still to build:**

- **Step 3, the Dashboard:** the Your Week tab, Agent Activity, weather
  and the active mission.
- **Step 6:**
  - upkeep as scheduled missions;
  - the Businesses page with a dashboard per business;
  - orders and quotes per business;
  - Health's meals widget.
- **Muse's handoff:** the destinations' pictures and the world portals'
  art.

This document has five parts:

1. What exists today
2. The new shape
3. Every app and page with one owner
4. Hard cases and questions for Zac
5. How to move without breaking anything

---

## 1. What exists today (counted from the code, 2026-11-11)

**Where navigation is defined.** Areas are defined in one place,
`core/web_areas.py` (DEC-0129). Four things read it:

| Reader | What it does with the areas |
|---|---|
| The sidebar (`web/shell.js` `sideLinks`, from `/api/shell`) | Lists every area |
| The hubs (`hub.html?area=<id>`, `/api/hub/<id>`) | One page per area |
| The Nexus (`core/web_nexus.py`, `web/nexus.html`, `/api/nexus`) | One portal per area |
| The glasses' ring (`core/glasses.py` `glasses_areas`, `web/glasses.js` `nexusCards`) | One ring entry per area |

Other things that depend on the area ids:

- **Voice:** "take me to the garage" is resolved by
  `core/web_nexus.wants_area`, called from `core/assistant_turn.py`.
  Nothing else in voice or action routing uses areas. Tools and action
  kinds belong to apps, not areas, so regrouping cannot break them.
- **Each area's own room:** `core/web_environments.py` (the Garage's
  bays and the other rooms).
- **Portal paintings:** `core/portal_pictures.py`, keyed by area id.
- **Studio preview:** the Theme Studio's little room uses the first
  five areas (`core/themes.py`).

**Apps.** `core/web_surfaces.APPS` holds 53 apps:

- 3 are retired (`maintenance`, `property`, `dashboard`). They are
  folded into Garage, Real Estate and Today.
- 2 have no web page of their own (`diagnostics`, `settings`). They use
  `diagnostics.html` and `settings.html`.

**Areas.** 16 areas: the 15 from DEC-0129 plus Kitchen's own (DEC-0130).
Their members:

- 53 apps, and 33 `Page` entries that aren't apps (Projects, Pets,
  Guitar, the ID Wallet...).
- Six apps sit in more than one area: Kitchen (3), Real Estate (2),
  Compliance (2), Workshop (2), Skills (2), Inbox (2).
- Two app ids are in no area: `web_home`, which is Today/Dashboard, and
  `dashboard`, which is retired.

**The 100 pages in `web/`.** 18 aren't reached from any area:

- **Frame pages:** `hub`, `nexus`, `glasses`, `presence`, `start`.
- **Detail pages:** `asset`, `recipe`, `grow`, `plan`.
- **No door at all:** the system pages `council`, `dev`, `dev-window`,
  `model-test`, `sync` and `made`.
- **Page files of door-less apps:** `diagnostics.html` and
  `settings.html`, already listed above.
- **A redirect:** `finances.html` sends you to `money.html` (it moved on
  2026-10-06). It stays as a redirect.

**What the Nexus is today.** It is MIA's spatial home: one portal per
area. The Spatial look opens on it first (`web/welcome.js`, the
sidebar's order), and so do the glasses' ring. Living Worlds itself
(`worlds.html`, `core/living_worlds.py`: universes, campaigns,
characters) is one page inside Recreation. **So today it's the reverse
of what Zac wants:** the Nexus is the way to everything, and the worlds
are one door in it.

**What the Dashboard is today.** It is `index.html`, the `web_home` app
(DEC-0129 named Today "the Dashboard"). It shows:

- what needs you and what's coming;
- a glance at each app;
- the "life cards": what's playing, today's good news, recent pictures
  and the trip.

The frame (`web/player.js`) gives every page its music bar. Gaps against
the spec:

- **Weather:** MIA has no source. The life state marks it `PLANNED`.
- **Active mission:** shown only as a count.
- **Agent Activity:** has no card.

---

## 2. The new shape

### Always there, on every page and device (Rule 5)

These live in the frame, not in a destination:

- Talk: her orb and the box.
- Search (Ctrl+K).
- Notifications.
- The music bar.
- The Dashboard link.
- Start Here.

Every destination page keeps them. Nobody has to go back to the
Dashboard to talk to her.

### The eight destinations

Subdashboards are marked ▸. An app or page is listed under exactly one
owner.

**1. Dashboard** (`index.html`, app `web_home`): an overview that owns
almost nothing.

- **Widgets:**
  - time, date and weather (weather needs a source, see 4.1);
  - the active mission (from Missions);
  - the music player (from Recreation › Music);
  - Agent Activity (see 4.2);
  - Good News Radio;
  - what needs you today;
  - notifications.
- **Owns:** Good News Radio (`good_news`, `news.html`) and the
  Notifications page (`notifications.html`). Every other card opens its
  owner.

**2. Home** (`hub.html?area=home`)

- **Home itself:** Household (`household`) and Home Upkeep
  (`upkeep_home`, see split 4.3).
- ▸ **Kitchen:** Kitchen (`kitchen`), with its Recipe page (`recipe.html`).
- ▸ **Smart Devices:**
  - Cameras (today's app `security`, see 4.4)
  - Power (`power`)
  - Sensors (`sensors.html`)
  - The Lab (`lab`)
  - Field Kit (`field_kit`)
- ▸ **Homestead:**
  - Greenhouse (`greenhouse`, with `grow.html` and the Homestead
    system behind it)
  - Chickens (`flock`)
  - Pets (`people.html?only=pets`)
- ▸ **Recreation:**
  - Music (`music`)
  - Play (`play`)
  - Expeditions (`expeditions`)
  - Maps (`maps`)
  - Navigation (`navigation`)
  - Trail Maps (`trails`)
  - Tracks (`tracks`)
  - World Map (`worldmap`)
  - My Places (`places`)
  - a door to the Nexus (Living Worlds), which is only a shortcut (see 4.5)
- ▸ **Personal Tools:**
  - Calendar (`calendar`)
  - Journal (`notes`)
  - Kept (`life_notes`)
  - Operating Journal (`operating_journal`)
  - Memories (`memories`)
  - Memory Vault (`vault`)
  - Files (`files`)
  - People (`relationships`)
  - Sunday Check-In (`checkin`)
  - Observations (`observations`)
  - Connections (`connections`)
- ▸ **Learning:**
  - Classroom (`classroom`)
  - Knowledge (`knowledge`)
  - Guitar (`guitar`)

**3. Garage**

- Garage (`garage`: vehicles, their records and upkeep)
- Toolbox (`toolbox`, see 4.6)
- Trade Master (`trades`: repairs and troubleshooting)
- The Asset page (`asset.html`): each vehicle's or tool's own record and
  upkeep, reached from the asset, never from the menu

**4. Finances**

- Money (`budget`: income, expenses, budgets, debts, reports)
- Freedom (`freedom`)
- Insurance (`insurance`)
- Compliance (`compliance`: taxes, permits, deadlines)
- ▸ **Businesses:** one card per business entity that Money already
  keeps (`BusinessEntity`). Each card shows that business's income and
  expenses from the tagged transactions. A business that has its own
  apps opens its own subdashboard:
  - ▸ **Real Estate:** Real Estate (`real_estate`: rentals, tenants,
    their buildings' upkeep).
  - ▸ **Woodworking:**
    - Workshop (`workshop`: parts, jobs, products)
    - Orders & Quotes (`business`: customers, quotes, orders)
    - Labels (`labels`)
    - Show Off (`showoff`)
  - Any other business (lawn care, the homestead's sales...) gets the
    general business page: its numbers, its assets, its missions.

**5. Health + Fitness**

- Health (`health.html`: sleep, visits, medications, records)
- Workout (`workout`)
- My plan (`plan.html`: goals, the training week, meals)
- **Widget:** this week's meals, from Kitchen. Health shows them; Kitchen
  owns them.

**6. AI Tools**

- Look (`sight`)
- Browser (`browser`)
- Look It Up Online (`lookup`)
- Inbox (`inbox`: send MIA a photo, a file or a note)
- Communications (`communications.html`: email drafts, the mailbox,
  what she said on her own)
- MIA Assistant (`assistant`): the full chat page. Talk itself stays in
  the frame.
- Made by MIA (`made.html`): the screens she builds for you (see 4.7)

**7. Missions**

- Missions (`missions`, with the active mission at the top)
- Projects (`projects.html`: DEC-0152, one record each; a Workshop job's
  build stays the Workshop's)
- The Dungeon (`dungeon`)
- Skills (`skills`)
- Character (`character`)
- Reward Shop (`reward_shop`)
- Party (`party`)
- The Chronicle (`chronicle`)
- My Why (`why`)
- My Directions (`directions`)

**8. Settings**

- **Settings itself:**
  - Settings (`settings`)
  - Theme Studio (`studio`)
  - How MIA Answers (`answers`)
  - Apps (`module_browser`, which can never be disabled)
- ▸ **Security:**
  - Passwords (`passwords`)
  - ID Wallet (`id_wallet`)
  - Sign-Ins (`signins`)
- ▸ **You and your accounts:**
  - Profile (`profile`)
  - Getting To Know You (`sync.html`)
  - Connect Apps (`connect`)
- ▸ **Your data:**
  - Your Data (`yourdata`)
  - Recent Changes (`changes`, with Undo)
- ▸ **System:**
  - Diagnostics (`diagnostics`)
  - Fix-It Log (`issues`)
  - The Council (`council.html`)
  - Development (`dev.html`, `dev-window.html`)
  - Model check (`model-test.html`)
- **About MIA** (`about`): what she is and what she knows.

### The Nexus: Living Worlds only (Rule 6)

The Nexus stops being navigation.

- **Its portals:** one per universe, each opening that world's
  campaigns. The data is `core/living_worlds.py`; the Convergence comes
  later, as that spec says.
- **The worlds page:** `worlds.html` stays as the place to make and
  manage worlds.
- **Portal paintings:** Portal Pictures (`portals.html`) moves with it,
  so a painting goes on a world's portal.
- **How you reach it:** one entry of its own in the sidebar, apart from
  the eight; a door in Recreation; "take me to the Nexus".

### The glasses: three screens

| Screen | What it holds |
|---|---|
| **The orb** | Today's glasses home (`paintHome`): her state, the one line that matters, the latest card |
| **The menu** | The eight destinations. Each opens its subdashboards, then their apps, one level at a time. Back goes up one level. |
| **The Nexus** | The ring becomes the worlds: one entry per universe, then its campaigns. Picking a campaign opens play. |

Today's area ring (`glasses_areas`) becomes the menu's data. The ring
code is kept and given worlds.

---

## 3. Ownership matrix: every app id and page to one owner

How to read it:

- **Direct:** the item moves as is.
- **Consolidate:** it was in several areas and now has one.
- **Split:** part of it moves (section 4).
- **New sub:** it needs a subdashboard that doesn't exist yet.
- **Ask:** I'm not sure of the owner (section 4).

| id | Name | Today's area(s) | New owner | Kind |
|---|---|---|---|---|
| web_home | Today / Dashboard | (frame) | Dashboard | direct |
| good_news | Good News Radio | Personal | Dashboard | direct |
| notifications (page) | Notifications | Communications | Dashboard | direct |
| household | Household | Home | Home | direct |
| upkeep_home (page) | Home Upkeep | Home | Home | split (4.3) |
| kitchen | Kitchen | Home, Kitchen, Health | Home › Kitchen | consolidate |
| recipe.html | Recipe | none | Home › Kitchen (detail) | direct |
| security | Security (cameras) | Security | Home › Smart Devices | split + rename (4.4) |
| power | Power | Home | Home › Smart Devices | new sub |
| sensors (page) | Sensors | Settings | Home › Smart Devices | new sub |
| lab | The Lab | Projects | Home › Smart Devices | ask (4.6) |
| field_kit | Field Kit | Security | Home › Smart Devices | ask (4.6) |
| greenhouse | Greenhouse | Plants and Animals | Home › Homestead | direct |
| grow.html | Greenhouse detail | none | Home › Homestead (detail) | direct |
| flock | Chickens | Plants and Animals | Home › Homestead | direct |
| pets (page) | Pets | Plants and Animals | Home › Homestead | direct |
| music | Music | Recreation | Home › Recreation | direct (player widget on Dashboard) |
| play | Play | Recreation | Home › Recreation | direct |
| expeditions | Expeditions | Recreation | Home › Recreation | direct |
| maps | Maps | Recreation | Home › Recreation | direct |
| navigation | Navigation | Recreation | Home › Recreation | direct |
| trails (page) | Trail Maps | Recreation | Home › Recreation | direct |
| tracks (page) | Tracks | Recreation | Home › Recreation | direct |
| worldmap (page) | World Map | Recreation | Home › Recreation | direct |
| places (page) | My Places | Recreation | Home › Recreation | direct |
| calendar | Calendar | Personal | Home › Personal Tools | direct (today's items on Dashboard) |
| notes | Journal | Personal | Home › Personal Tools | direct |
| life_notes | Kept | Personal | Home › Personal Tools | direct |
| operating_journal | Operating Journal | Personal | Home › Personal Tools | direct |
| memories | Memories | Recreation | Home › Personal Tools | direct |
| vault | Memory Vault | Personal | Home › Personal Tools | direct |
| files | Files | Personal | Home › Personal Tools | direct |
| relationships | People | Personal | Home › Personal Tools | direct |
| checkin (page) | Sunday Check-In | Personal | Home › Personal Tools | ask (4.8) |
| observations | Observations | Personal | Home › Personal Tools | ask (4.8) |
| connections (page) | Connections | Personal | Home › Personal Tools | ask (4.8) |
| classroom | Classroom | Learning | Home › Learning | direct |
| knowledge | Knowledge | Learning | Home › Learning | direct |
| guitar (page) | Guitar | Learning | Home › Learning | direct |
| garage | Garage | Garage | Garage | direct |
| toolbox | Toolbox | Garage | Garage | ask (4.6) |
| trades (page) | Trade Master | Home | Garage | ask (4.6) |
| asset.html | Asset | none | Garage (detail; a house appliance's opens from Home) | direct |
| maintenance | Maintenance | (retired) | each asset (already so) | none needed |
| property | Property | (retired) | Real Estate and Home (already folded) | none needed |
| budget | Money | Finances | Finances | direct |
| finances.html | (redirect to Money) | none | stays a redirect to `money.html` | none needed |
| freedom | Freedom | Finances | Finances | direct |
| insurance | Insurance | Finances | Finances | direct |
| compliance | Compliance | Finances, Business | Finances | consolidate |
| (new) | Businesses | none | Finances › Businesses | new sub (4.9) |
| real_estate | Real Estate | Finances, Business | Finances › Businesses › Real Estate | consolidate |
| workshop | Workshop | Business, Projects | Finances › Businesses › Woodworking | consolidate |
| business | Orders & Quotes | Business | Finances › Businesses › Woodworking | direct (4.9) |
| labels (page) | Labels | Business | Finances › Businesses › Woodworking | direct |
| showoff (page) | Show Off | Business | Finances › Businesses › Woodworking | direct |
| health (page) | Health | Health | Health + Fitness | direct |
| workout | Workout | Health | Health + Fitness | direct |
| plan.html | My plan | none | Health + Fitness | direct (Kitchen links to it) |
| sight | Look | Garage | AI Tools | direct |
| browser | Browser | Browser | AI Tools | direct |
| lookup (page) | Look It Up Online | Learning | AI Tools | direct |
| inbox | Inbox | Finances, Communications | AI Tools | consolidate |
| communications (page) | Communications | Communications | AI Tools | direct |
| assistant | MIA Assistant | Communications | AI Tools (Talk stays global) | direct |
| made.html | Made by MIA | none | AI Tools | ask (4.7) |
| missions | Missions | Missions | Missions | direct |
| projects (page) | Projects | Projects | Missions | direct |
| dungeon | The Dungeon | Finances | Missions | direct |
| skills | Skills | Learning, Missions | Missions | consolidate |
| character | Character | Missions | Missions | direct |
| reward_shop | Reward Shop | Missions | Missions | direct |
| party (page) | Party | Missions | Missions | direct |
| chronicle (page) | The Chronicle | Missions | Missions | direct |
| why (page) | My Why | Personal | Missions | ask (4.8) |
| directions (page) | My Directions | Personal | Missions | ask (4.8) |
| settings | Settings | Settings | Settings | direct |
| studio (page) | Theme Studio | Settings | Settings | direct |
| answers (page) | How MIA Answers | Settings | Settings | direct |
| module_browser | Apps | Settings | Settings (and the frame's "all apps") | direct |
| passwords | Passwords | Security | Settings › Security | direct |
| id_wallet (page) | ID Wallet | Security | Settings › Security | direct |
| signins (page) | Sign-Ins | Security | Settings › Security | direct |
| profile (page) | Profile | Settings | Settings › You and your accounts | direct |
| sync.html | Getting To Know You | none | Settings › You and your accounts | direct |
| connect (page) | Connect Apps | Settings | Settings › You and your accounts | direct |
| yourdata (page) | Your Data | Settings | Settings › Your data | direct |
| changes (page) | Recent Changes | Settings | Settings › Your data (Agent Activity draws on it) | direct |
| diagnostics | Diagnostics | Settings | Settings › System | direct |
| issues | Fix-It Log | Settings | Settings › System | direct |
| council.html | The Council | none | Settings › System | ask (4.2) |
| dev.html, dev-window.html | Development | none | Settings › System | direct |
| model-test.html | Model check | none | Settings › System | direct |
| about (page) | About MIA | Settings | Settings | direct |
| worlds (page) | Living Worlds | Recreation | **the Nexus** | direct (4.5) |
| portals (page) | Portal Pictures | Settings | **the Nexus** | direct |
| nexus.html | The Nexus | (frame) | **the Nexus** (worlds only) | rebuilt (4.5) |
| hub.html, presence.html, start.html, glasses.html | Frame pages | (frame) | the frame | none |
| dashboard | Dashboard (old) | (retired) | Dashboard (`dashboard.html` already retired) | none needed |

**Totals:**

- Every item above has exactly one owner.
- Nothing is removed.
- Six items are consolidated.
- Two need a split.
- Five subdashboards need building, because no area exists for them
  yet: Smart Devices, Homestead (today's Plants and Animals, renamed),
  Personal Tools (today's Personal, trimmed), Businesses, and Settings'
  four.

---

## 4. Hard cases and questions for Zac

**4.1 Weather.** MIA has no weather source. The Dashboard can show it
only once one exists, and showing a blank card would pretend otherwise.
**Ask:** may she fetch it online? Open-Meteo needs no account, and the
place would come from your region setting. If not, the card stays off
and says nothing.

**4.2 "Agent Activity" means which agents?** Two things go by that name:

1. **What MIA did on her own:** Recent Changes with Undo, screens she
   made, messages she held back. This is user-facing, and I propose it
   is the Dashboard card.
2. **The development team's agents:** The Council and the Development
   board. That's agent orchestration, which your spec puts in
   Settings › System.

**Ask:** is the Dashboard card (1), or both?

**4.3 Home Upkeep lives inside Real Estate today.** Your house's
buildings and appliances were put in Real Estate on 2026-10-16, and
"Home Upkeep" links to `real-estate.html#home`. With Real Estate moving
under Businesses, your own house shouldn't sit in a business. The split:

- **Your own house's tab** becomes Home's. Same store, same records; the
  page opens from Home.
- **Rentals stay** in Real Estate.

No data moves. A property just says whether it is your home or a
rental, which the Real Estate store already records (`property_type`: "Primary Residence", "Rental"...).

**4.4 "Security" is the cameras app.** The app named Security is the
cameras. Your spec puts cameras in Smart Devices, and "Security" in
Settings means passwords and sign-ins. **Proposal:** keep the app id
`security` and its route, show its name as "Cameras", and use the word
Security only for Settings › Security.

**4.5 The Nexus becomes Living Worlds.** This reverses part of
DEC-0130. The Nexus was the spatial home with one portal per area.

What changes:

- The Spatial look opens on the Dashboard.
- The Nexus's portals become worlds.
- The area rooms (`core/web_environments.py`: the Garage's bays and the
  rest) stay as the Spatial look of each destination's hub, so Muse's
  work there isn't lost.
- Muse's eight area paintings (`web/img/portals/`) can become the
  destinations' pictures in the menu. That's for Muse to say, as a
  handoff.

**Ask:** should the Nexus have its own sidebar entry, or be reached only
through Recreation and by voice?

**4.6 Tools that fit two places.**

- **Toolbox:** calculators, the same ones builds use. I propose Garage;
  the other choice is Personal Tools.
- **Trade Master:** a job or diagnosis walked through, for a car or a
  sink. I propose Garage ("repairs and troubleshooting"), with Home
  Upkeep linking to it.
- **The Lab:** sensor series and charts. I propose Smart Devices.
- **Field Kit:** what's plugged in, and your scripts. I propose Smart
  Devices; the other choice is Settings › System.

**4.7 Made by MIA:** the screens she makes for you. I propose AI Tools.
`docs/specs/SELF_ORGANIZATION.md` later gives it a bigger role, with her
placing what she makes inside the right destination.

**4.8 The reflective pages.**

- **Personal Tools:** Sunday Check-In, Observations and Connections.
- **Missions:** My Why and My Directions, because they're about what
  you're steering by.

Personal Tools still ends up with 11 members, the biggest
subdashboard. If that feels like the old Personal drawer, the obvious
split is Personal Tools (Calendar, Journal, Kept, Files, People) and a
Memories subdashboard (Memories, Vault, Operating Journal, Check-In).
**Ask** before splitting.

**4.9 Businesses.** Money already keeps your business entities, and
bank transactions are tagged to them (`core/business_tagging.py`).

- **Businesses page:** lists those entities, each with its income and
  expenses. That's new code in core but no new store.
- **Orders & Quotes:** one book built on the Workshop's recipes, so it
  belongs to Woodworking. If another business needs quotes later, the
  book gains a business field.
- **Real Estate's properties** already take their business's tag.

**4.10 Kitchen and Health.**

- **Meals:** Kitchen owns meal plans and recipes. Health shows this
  week's meals as a widget.
- **My plan** (training week and meals) is reached from both today. I
  propose Health owns it and Kitchen links to it.

**4.11 Skills and the Dungeon.**

- **Skills:** Missions only. Learning shows a shortcut to the skill
  being practised.
- **The Dungeon:** your debt payoff played as a run, so its numbers are
  Money's. Missions owns the game; Finances shows a shortcut ("the run:
  N% cleared").

---

## 5. How to move without breaking anything (stage 3)

### Design

- **No new registry.** `core/web_areas.py` stays the one place. `Area`
  gains:
  - `parent`, so a subdashboard is an area inside a destination;
  - `shortcuts`, links to items owned elsewhere, drawn as "from
    Kitchen", never as a copy.
- **No duplicate members.** `members` keeps meaning "owned here". A test
  fails if any app or page is a member of two areas, or of none (apart
  from the frame pages, which are listed).
- **Old ids still open.** Ids that exist today keep working:
  - unchanged: `home`, `garage`, `kitchen`, `health`, `finances`,
    `missions`, `recreation`, `learning`;
  - aliased: `plants_animals` → `homestead`, `personal` →
    `personal_tools`, `business` → `businesses`, `projects` →
    `missions`, `browser` and `communications` → `ai_tools`,
    `security` → `smart_devices`, `system` → `settings`.

  `hub.html?area=<old id>` opens the new place, so bookmarks, the
  phone's saved pages and Search keep working.
- **No route or store changes.** App ids, pages, stores, tools and
  action kinds don't change. Regrouping touches only how things are
  found.

### Order of work, each step tested and pushed on its own

1. **Registry and hubs.**
   - The eight destinations and their subdashboards go into `AREAS`,
     with the aliases and the single-owner test.
   - A destination's hub shows its subdashboards as large tiles, then
     its own apps.
   - The sidebar lists the Dashboard and the eight. The destination
     you're in opens to its subdashboards; the one you're in opens to
     its apps.
   - Tests: `test_web_areas`, plus `test_web_environments` for the
     rooms keyed by the old ids.
2. **Voice.** `wants_area` learns the eight names, the subdashboards
   ("take me to the homestead", "open personal tools") and the old
   names. "Take me to the Nexus" opens the worlds. Tests in
   `test_web_nexus`.
3. **Dashboard.**
   - Every look opens on it (`web/welcome.js`, the sidebar order, the
     desktop window's first page).
   - New cards: the active mission (its name and next objective, not a
     count) and Agent Activity (per 4.2).
   - Weather only if 4.1 is yes.
4. **Glasses.**
   - The menu becomes destination → subdashboard → app.
   - The ring is kept for the worlds.
   - Tests in `test_glasses`, and screenshots checked in demo mode.
5. **The Nexus as Living Worlds.**
   - `core/web_nexus.nexus()` returns universes.
   - Portal Pictures is keyed by universe. The old area keys are simply
     ignored, and the paintings stay in your art.
   - Its look stays Muse's: a handoff for the world portals' art.
6. **The splits:** Home Upkeep out of Real Estate (4.3), the Businesses
   page (4.9), Cameras' name (4.4) and Health's meals widget (4.10).
7. **Running files.**
   - Regenerate `docs/ATLAS.md`, `docs/PARITY.md` and `docs/LOOPS.md`
     where touched.
   - Update `docs/WEB_PARITY.md`.
   - Mark DEC-0129's areas and DEC-0130's Nexus-as-home superseded by
     DEC-0153.

### What gets checked at the end (stage 4)

- Every app and page has one owner (the test).
- Each of the eight and every subdashboard opens on example data with
  no script errors (the same 99-page sweep the organization review
  used).
- Every old `hub.html?area=` link lands somewhere.
- Voice: every destination's name, subdashboard and old name resolves.
  No tool or action kind changes, which the existing parity and routing
  tests confirm.
- The glasses' three screens, in demo mode.
- The Nexus shows worlds and no app.
- The full suite runs in a clean checkout.

### What I need from Zac before step 1

- Yes or no on this shape.
- Answers to 4.1, 4.2, 4.5, 4.6 and 4.8. The rest are my proposals; say
  if any is wrong.
