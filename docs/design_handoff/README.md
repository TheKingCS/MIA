# MIA: Design Handoff Brief

For **Claude Design** (or any designer) proposing new GUI directions for
MIA. Upload this file, the `screens/` folder, and the owner's inspiration
pictures together. Everything here describes the app as it exists on
2026-09-27. All screenshots use **fake demo data**, not the owner's
real information.

---

## 0. Paste-in prompt for Claude Design

> I'm attaching a design brief (README.md) for my desktop app MIA,
> screenshots of every current screen (`screens/`), and inspiration
> pictures. Read the brief first; it explains what each screen does and
> the technical limits a design has to respect (section 7).
>
> Using my pictures as the visual direction, give me **3 distinct GUI
> directions**. For each, design:
> 1. the main shell + Home screen (`00_main_window_home.png`),
> 2. the Debts tab (`budget__05_debts.png`),
> 3. an equipment page like Garage (`garage.png`),
> 4. the Mission Log (`missions.png`),
> 5. MIA's "presence" orb in its states: idle, listening, thinking,
>    task complete, needs attention.
>
> For each direction, also give a token table (colors with their roles,
> type scale, spacing, corner radius) and a small component sheet: card,
> stat tile, list row, tab bar, primary/secondary button, badge/chip,
> text input. Keep every direction buildable within section 7's limits.

---

## 1. What MIA is

MIA (Multifunctional Intelligent Assistant) is a personal "life OS" and
AI companion that runs **fully offline on the owner's own computer**. It
isn't a chatbot bolted onto an app. It's one companion that knows the
owner's money, homestead, equipment, goals, health, and knowledge, and
helps them act on it.

The owner uses it to run their household, a small homestead they're
building, rental real estate, and a lawn-care/contracting business.

**Where it runs:**

| Surface | What it is | Design relevance |
|---|---|---|
| **MIA Home** (this brief) | PySide6 (Qt) desktop app, typically 1600×1000 or larger, mouse + keyboard, sometimes touch | **Primary design target** |
| Phone | Small web page (PWA) over the owner's private network; today it only does login + push notifications | Future. Mention mobile adaptations only if cheap |
| MIA Core | Wearable, voice-only, no screen (a tiny e-paper status display) | Out of scope |

## 2. Design north star (the owner's own standards)

- **"MIA should not feel like software."** It should feel like a
  knowledgeable companion. Test every choice against: *does this make
  MIA feel more like a companion?*
- **Presence, not just menus.** MIA has a visual "core"/orb that reacts
  when she's listening, thinking, loading, completing a task, or has
  news. It lives on every screen, not just at boot.
- **Game-like, not gamified clutter.** Goals are *Missions* with
  objectives, XP, levels, a skill tree ("My Hero's Path"),
  achievements, streaks. It should feel like an RPG quest log /
  command center, never a corporate dashboard.
- **Voice-first.** The owner should be able to run the whole app by
  talking. When they ask for something, the GUI should visibly navigate
  to it and fill it in live. Design screens that can show "MIA is doing
  this for you" states.
- **Restraint.** Named inspirations: sci-fi command interfaces, game
  HUDs, holographic assistants, RPG menus. But "prioritize
  responsiveness over spectacle"; restraint ages better than
  maximalism.

**Two visual lineages already exist.** The owner's new pictures decide
which to keep, merge, or replace:

1. **"Dark Field" HUD**: near-black navy, teal accent, glowing panel
   edges, monospace readouts, blueprint corner marks
   (see `00_main_window_home.png`, `missions.png`).
2. **"Nature"**: photographic hero banners with a dark scrim,
   forest-green and coral, rounded translucent cards
   (see `garage.png`, `greenhouse.png`, `kitchen.png`, `workout.png`,
   `real_estate.png`, `skills.png`).

## 3. App structure

### The shell (always visible), see `00_main_window_home.png`

- **Top bar:** "M.I.A." wordmark · primary nav **Home / Missions /
  Monitoring / App Center** · Back · global **Search** (Ctrl+K,
  searches every module) · **Level badge** · profile avatar.
- **Right sidebar = MIA herself:** presence orb, status line
  ("Welcome home."), chat history, suggested-prompt chips, a text box,
  **Hold to Talk** and **Stop** buttons, conversation History.
- **Status bar** at the bottom ("MIA core online.").

### Home console

A greeting hero ("Good morning, <name>", level, missions available,
active projects, an "ALL SYSTEMS NOMINAL" pill) · a clock · a spoken
**daily briefing** card with Replay · a customizable **Widgets** area
(cards like Budget, Maintenance, Kitchen, Workout, Real Estate, Net
Worth, Observations, Field Captures) · **Open Apps** (all modules).

### Modules (screens), grouped by life area

Tabbed modules have one screenshot per tab (`name__NN_tab.png`).

**Money & business**

| Module | Purpose | Screens |
|---|---|---|
| Budget | Bills, income, expenses; **Debts** ranked by payoff priority (avalanche/snowball/hybrid, promo-APR countdowns); Summary; Trends chart; **Bank Sync** (Plaid) | `budget__01…08` |
| Real Estate | Rental properties: value, equity, mortgage, depreciation, linked maintenance | `real_estate.png` |
| Workshop & Electronics | Parts inventory, fabrication materials, jobs (costed), products, sales ledger | `workshop__01…05` |

**Home, homestead & equipment**

| Module | Purpose | Screens |
|---|---|---|
| Garage | At-a-glance vehicles and motorized equipment (e.g. mower, truck): overdue service, next up | `garage.png` |
| Property | House, appliances, tools | `property.png` |
| Greenhouse | Garden, greenhouse, aquaponics assets | `greenhouse.png` |
| Household | Daily/weekly routines (laundry, dishes) with streaks | *(no screenshot, see §9)* |
| Maintenance | The engine behind Garage/Property/Greenhouse: assets, recurring tasks (calendar or meter-based, e.g. every 50 engine hours), calendar overview, sensor monitor | `maintenance__01…04` |
| Kitchen | Recipes, pantry, grocery list, meal tracking | `kitchen.png` |
| Power | Battery, energy/utility tracking | `power__01…02` |

**Life, goals & self**

| Module | Purpose | Screens |
|---|---|---|
| Missions | Quest log: missions with objectives, difficulty, XP/credit rewards, MIA-assigned quests | `missions.png` |
| Skills | "My Hero's Path" skill tree and character progression | `skills.png` |
| Character | Lifetime stats, prestige, cosmetic rewards | `character.png` |
| Dashboard | Recent activity, missions, memories, events, projects, tasks | `dashboard.png` |
| Observations | Things MIA has noticed (patterns, overdue items, skills gone quiet) | `observations.png` |
| Workout | Guided sessions, rest timers, PRs, progress charts | `workout.png` |
| People & Pets | Relationship and pet profiles (birthdays, gift ideas, vet history) | `relationships__01…02` |
| Notes | Dated, tagged journal | `notes.png` |
| Classroom | Subjects → courses → lessons (future: textbook-backed tutoring) | `classroom.png` |

**Outdoors & field**

| Module | Purpose | Screens |
|---|---|---|
| Expeditions | Trip routes, gear, weather, logged distance | `expeditions.png` |
| Memories | Trip recaps, stats, photos | `memories.png` |
| Maps | Waypoints, offline basemap, trail map PDFs | `maps__01…03` |
| Navigation | Distance/bearing, sun/moon | `navigation.png` |

**Knowledge, tools & system**

| Module | Purpose | Screens |
|---|---|---|
| Assistant | Full chat with MIA | `assistant.png` |
| Knowledge | Offline reference library (Wikipedia/manual packs) | `knowledge.png` |
| Toolbox | Calculators, unit conversion, quick tools | `toolbox.png` |
| The Lab | Sensor experiments and graphs | `lab.png` |
| Field Kit | Connected devices, scripts, security | `field_kit__01…03` |
| Files, Music | File browser; local music library | `files.png`, `music__01…02` |
| Modules | Enable/disable/install modules; architecture diagram | `module_browser__01…02` |
| Settings, Diagnostics | Theme, profile, options; system health | `settings.png`, `diagnostics.png` |

## 4. Key workflows to design around

1. **Morning check-in**: open app → greeting + spoken briefing →
   glance at what needs attention → jump into it.
2. **Do a quest**: open Missions → tick an objective → XP gain,
   level-up, achievement celebration.
3. **Equipment care**: Garage → mower → "blades overdue 4d" → mark
   complete / log engine hours → next due date updates.
4. **Money decisions**: Budget → Debts → see which debt to pay first
   and *why* (e.g. "0% promo ends in 20d, then jumps to 24.99%") →
   record a payment. Plus bank sync status/actions.
5. **Talk to MIA**: "Add a mission to build the coop" → UI navigates
   to Missions and fills the form live while MIA asks follow-ups.
6. **Find anything**: Ctrl+K search across every module.

## 5. States every direction must handle

Empty ("Nothing here yet"), overdue/needs-attention (currently red),
due soon, all caught up, streaks, locked/unlocked items, level + XP
progress, rarity/prestige tiers, **bank-synced vs manual** data,
**promo-rate countdowns**, sensitive-data locked (vault/passphrase),
offline/online, MIA listening/thinking/speaking.

## 6. Current visual system ("Dark Field")

- **Fonts (bundled):** Inter (UI; Regular/Medium/SemiBold/Bold/
  ExtraBold) and JetBrains Mono (readouts, labels, clock).
- **Core colors:**

| Role | Hex |
|---|---|
| Background (deepest) | `#0d1116`, `#0c1017` |
| Panels / fields | `#101722`, `#111722`, `#161b22`, `#1b222e` |
| Borders / gridlines | `#232b34`, `#1f3538` |
| Accent (teal) | `#38d9c9` (brighter `#4fd1c5`, deep `#0d9488`) |
| Accent field (teal-tinted panel) | `#0f1a1c` |
| Text primary / secondary / dim | `#e7ecf3` / `#c3ccd9` / `#7c8798`, `#5b6a80` |
| Warning / critical | `#e0af68` / `#e06666` |
| Gold (badges) | `#f0b83c` |

- **v2 HUD layer:** colored panel glows, HP green, XP purple,
  blueprint corner marks (the "+" corners in `missions.png`).
- **Other themes:** Low Energy (light grey), Colored, Anime Monochrome.
  Any new direction becomes a theme alongside these.
- **Icons:** currently emoji. A real icon set is welcome.

## 7. Technical limits (so designs are buildable)

MIA's GUI is **Qt (PySide6) with Qt Style Sheets (QSS)** and custom-
painted widgets. It is **not a web page**.

**Easy:** solid/gradient backgrounds, borders, rounded corners, bundled
fonts, per-state colors (hover/pressed/checked/disabled), photos with
a painted scrim, custom-painted shapes (orbs, rings, gauges, glows made
of layered translucent strokes), simple animations (fades, pulses,
slides, color and size transitions), charts.

**Hard / avoid:** real background blur ("frosted glass"; fake it with
translucent fills), CSS-style `box-shadow` (possible but costly, use
sparingly), heavy 3D, video backgrounds, web-style responsive
grid/flex behavior (layouts are explicit), fonts not bundled.

**Architecture rules the design should fit:**
- One central theme + a small set of shared components restyle the
  whole app. Design a **system** (tokens + components), not 30 one-off
  screens.
- Target 1600×1000 and larger; nothing should break at 1280×800.
- Keep animation cheap: smooth on modest hardware beats spectacle.

## 8. What would help most in the output

- Direction name + mood in one line, and which of the owner's pictures
  drove it.
- The 5 screens in §0, the token table, the component sheet.
- Presence-orb state strip (idle/listening/thinking/complete/alert).
- Notes on anything that would violate §7, with a buildable
  alternative.

## 9. Known gaps in this package

- **Household** has no screenshot (the standalone capture tool can't
  build that screen yet). It looks like Garage: a hero banner plus
  routine cards with streaks.
- The Home **Widgets** row is empty in `00_main_window_home.png`
  because the demo profile hasn't picked widgets yet. Real use shows
  cards for Budget, Maintenance, Real Estate, Net Worth, etc.
- Screenshots are 1280×800 per module and 1600×1000 for the shell.
