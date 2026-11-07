# MIA Experience Maturity Audit

*Claude, 2026-11-07, for the Experience Maturity initiative (H-0087; Zac and ChatGPT's handoff, which they numbered
H-0084: that number was already taken). Stage 1 of the handoff: investigation only, nothing redesigned. Grounded in
the code: the inventory tables (part 2) are generated from the repository, not written from memory. Counts only;
nothing personal is in this file.*

## Summary

MIA is functionally wide and experientially young. **70 web pages, 52 apps, 168 API routes and 306 action kinds**
exist, almost all with real data behind them, one shared frame (`web/shell.js`) and one token file
(`web/tokens.css`). What's missing is not capability but **finish and proof**: most screens are working forms in a
consistent dark shell ("formatting only; the look is Muse's" is written at the top of most page scripts), several
design documents contradict each other, and **almost nothing has been validated in real use** (on this PC, Home has
been opened 39 times, Settings 16, Make Something 12; Kitchen once; Workout never).

Workout and Kitchen are the right pilots: both are already at **Integrated** (level 3 of the handoff's standard):
deep data, missions, XP, voice, the phone and (Workout) the glasses. Neither is **Polished** or **Trusted**.

**Recommendation in one line:** don't build new screens first. Settle the identity (one decision on per-app
atmosphere, below), make the shared components real (so every page gets better at once), then take Workout through
design, build, *real workouts*, and refinement before Kitchen, and only then widen.

## 1. Feature maturity, assessed

The handoff's standard: **1 Exists** (the capability is in the engine) · **2 Functional** (primary workflows work) ·
**3 Integrated** (works with other MIA systems: missions, XP, voice, life state, links) · **4 Polished** (finished
interface and interaction) · **5 Trusted** (validated in real use). A passing test suite is level 2 at most on its
own.

| App | Level | Why, and what the next level needs |
|---|---|---|
| Workout | **3** | Live session shared by every surface (`core/training_session.py`), Count With Me, rest that starts itself, plan, missions, XP, PRs, the glasses' Active Training panel. **For 4:** a designed active-workout view (today it's a tab), a rest timer that's a moment not a line, the history and analytics designed. **For 5:** real workouts, and the phone's native counting voice and "workout listening" mode, which need an Android build and real-device testing (`docs/ACTIVE_TRAINING_PLAN.md` §9). |
| Kitchen | **3** | Today with planned meals and nutrition, week plan, recipes with steps, ratings and stats, pantry with use-by, grocery, meal log, suggestions, meal missions. **For 4:** a cooking mode (one step at a time, hands-free, timers), recipe pages designed for a counter top, the week plan readable at a glance. **For 5:** real meal planning and cooking. Voice-guided cooking does not exist yet. |
| Missions, Skills, Character | 3 | Deep and connected (XP, bosses, pathways, the guitar path's homework); each a long list, not yet a designed progression experience. |
| Money, Freedom, Compliance, Insurance | 3 | Real engine (Plaid in progress), actions, findings; screens are tables and forms. |
| Garage, Greenhouse, Real Estate, Workshop | 3 | Equipment pages share one design (condition bars, due tasks); the closest to "designed" today. |
| Learning paths (Guitar) | 2–3 | Built 2026-11-07: the engine is complete and tested; its page is minimal. |
| Glasses | 3 | A purpose-built surface (orb, panels, feed); waiting on real-device use. |
| Most others (Calendar, Inbox, Journal, People, Maps, Music, ...) | 2–3 | Working screens in the shared frame. |
| Desktop-only apps (Power, Toolbox, Lab, Field Kit, Diagnostics, Settings' Qt side) | 2 | No web screen (Diagnostics and Settings have web pages for their main parts). |
| Anything at 4 or 5 | **none** | |

**Connect it to her self-assessment (proposal):** a maturity register (`docs/MATURITY.md`, or a small
`core/maturity.py` table) with each app's level and the evidence for it, and a loop that reads real use
(`data/page_usage.json` per page) so "Trusted" is measured, not declared. That would be her improvement loops
(DEC-0094) applied to experience, the same way the self-audit applies them to code.

## 2. Workout, in depth

**What exists (engine):** `core/fitness_manager.py` (the plan: goals, training days and rotation, skills with steps,
meals, milestones; day totals, weight trend, bests), `core/training_session.py` (the live session: prescribed vs
performed, set by set, how each count was made: said, cadence, told, tapped, and the record never calls a count
verified), `core/training_actions.py` (`training.*`, child-safe), `core/workout_manager.py` (sessions, exercises,
PRs), `core/fitness_missions.py` (daily and weekly missions from the plan, progress from the logs),
`core/web_fitness.py` (the Fitness data), `core/plan_import.py` (paste a plan as text).

**What exists (screens):** `web/workout.html` (520 lines of script, six tabs: Today, Progress, Log Session,
Exercises, History, Personal Bests; the live session with Count With Me and the rest countdown inside Today),
`web/plan.html` (the plan editor), the glasses' Workout card with Active Training (`core/glasses.py`), the desktop
Qt Workout module (with its own older in-memory session, still to retire).

**Voice:** "start my workout", "twelve", "next set", "pause", "make that ten", "how am I doing?", "I'm done", ahead of
every other quick command.

**Gaps against the handoff's target:**
- Active workout is a section of a tab, not a full-screen mode with one thing in focus (the exercise, the set, the
  count, the rest).
- Rest timer exists as a countdown line; no designed moment (ring, sound, the next exercise previewed).
- The phone's native voice for the count and its continuous "workout listening" mode are not built (an Android
  build); the web page calls the hook already.
- Progress and analytics: the sentence, the numbers and a weight line; no volume, frequency or trend charts.
- Adaptive training proposals: phase 5, not built.
- **Integrity rule to keep in every design:** a count is labelled with how it was made; nothing shows an unverified
  count as verified performance (the handoff's own constraint, already the engine's).

## 3. Kitchen, in depth

**What exists (engine):** `core/kitchen_manager.py` (recipes, pantry with use-by, grocery, meal log, ratings, times
made, favourites), `core/kitchen_actions.py`, `core/meal_plan.py` (the week, prep sessions, allergies and dislikes
respected), `core/food_table.py` (USDA nutrition for about 7,800 foods, offline), `core/nutrition.py`, the fitness
plan's meals and lunch rotation, meal missions.

**What exists (screens):** `web/kitchen.html` (311 lines, seven tabs: Today, Week Plan, Recipes, Pantry, Grocery
List, Meal Log, Suggestions), `web/recipe.html` (a recipe's page: rating, stats, nutrition, have / on the list / to
buy, steps to tick, schedule, add to grocery, I made this).

**Gaps against the target:** no **cooking mode** (step by step, large type, timers, hands-free "next step"), no
voice-guided instructions, no substitutions, recipe discovery limited to her own book and suggestions, photos missing
(the recipe page has an image slot), pantry not updated by cooking.

## 4. Documents that disagree (reconcile before designing)

| Document | Date | What it says | Status now |
|---|---|---|---|
| `docs/design_handoff/README.md` + `screens/` | 2026-09-27 | The **desktop Qt app** as it was, for a designer to propose directions | **Obsolete as a basis**: the web is all of MIA (DEC-0017). Keep as history; the screenshots are the Qt app. |
| `docs/design/MOBILE_CONCEPT.md` (DEC-0018) | 2026-10-06 | Green-black, **photo headers**, glowing colored borders per screen | **Superseded** by DEC-0023 (no photos, one cyan accent). Its *layouts* were kept. |
| `docs/design/IMAGE_REQUESTS.md` | 2026-10-06 | Photographs for each screen's header, made by ChatGPT | **Superseded** in purpose (headers are technical plates now); its **workflow** (ChatGPT makes, Zac uploads to the repo) is the seed of the visual library below. |
| `docs/design/STARK_INTERFACE.md` (DEC-0023) | 2026-10-15 | The current look: one cyan accent, graphite layers, apps differ by icon and name, not color | **Current**, but see the per-app atmosphere decision below; and `--mod-*` per-app colors already exist in tokens.css, so practice already bends the rule. |
| `docs/design/CLAUDE_DESIGN_PROMPT.md` | 2026-10-30 | A brief for Claude Design from the usage audit | Current; to be replaced by the design-system and app specs below. |
| `web/README.md` | ongoing | The front end's contract (mia.js, actions, no logic in web/) | Current and binding. |
| This handoff | 2026-11-07 | JARVIS/EDITH, holographic, spatial, per-app atmosphere, ChatGPT as visual concept designer | Builds on DEC-0023; one real conflict (per-app atmosphere) needs Zac's call. |

## 5. Inconsistencies and usability problems found

1. **Every page is a stack of `glass money-section` panels.** The class name says money; it's every section
   everywhere. A real component (section, card, stat, list row) with names that say what they are is overdue.
2. **Tabs as the only structure.** Workout has six, Kitchen seven; on a phone that's a scrolling rail. Flagship apps
   need a home view and modes, not tabs for everything.
3. **States are uneven.** Most pages handle empty and error (part 2 table); loading is mostly a blank moment; offline
   is handled on six pages. A shared pattern for each state is missing.
4. **Literal colors**: 141 lines outside `tokens.css` (30 of them harmless black shadows).
5. **Two orbs**: Home's (`web/home.css`, moods: celebrate, needs-you, thinking) and the glasses' (`web/glasses.js`,
   states: listening, answered, idle) were built separately; the Talk panel's orb in the shell is a third use. One
   orb component with one set of states is needed.
6. **Stub pages**: `dashboard.html`, `finances.html`, `grow.html`, `maintenance.html`, `property.html` have no script
   of their own (retired screens or redirects).
7. **Six apps have no web page** (Power, Toolbox, Lab, Field Kit; Diagnostics and Settings partly).
8. **The desktop Qt Workout module keeps its own session**, a second state system the handoff rightly forbids.

## 6. Architectural constraints any design must respect

- Pages only talk through `web/mia.js`: `/api/state` and page reads, `/api/actions` to change things, `/api/live` to
  re-read. No business logic in `web/` (CLAUDE.md, DEC-0013).
- Offline: system fonts only, no web fonts or CDNs; images ship in the repo.
- Tokens only: never a hard-coded color (DEC-0023).
- Each person's data is theirs; a child sees fewer apps and no money.
- Desktop shows the same web pages (`modules/web_home`); phone in the Android app's web view; glasses have their own
  composition (`web/glasses.html`).
- One source of truth: a new screen reads what the engine already assembles; it never keeps its own state.

## 7. Decisions for Zac (summary; details in the proposals)

1. **Per-app atmosphere**: keep "one cyan accent, apps differ by icon" (DEC-0023), or allow each app a secondary
   atmosphere color and motif on top of the shared identity (the handoff's Workout/Kitchen/Workshop/Homestead idea)?
   Claude recommends: **yes, as a secondary layer** (the existing `--mod-*` tokens, formalized), with cyan still
   meaning MIA and "active" everywhere.
2. **Image generation**: start with the repository visual library (ChatGPT makes, Zac uploads), now; consider the
   OpenAI Images API later only with a key Zac creates, a monthly cap and approval per batch; also available today:
   the PC's own local image model (SDXL-Turbo, already used for the Chronicles), free and offline.
3. **The sequence**: approve Stage 2 (identity) to start with ChatGPT concept rounds before any build.
4. **The handoff number**: file it as H-0087.
5. **Retire the Qt Workout module's own session** when Workout is redesigned.

---

# Part 2: the inventory (generated)

## A. Every web page (generated from the code, 2026-11-07)

*`states` marks what the page's script handles, read from its code: E empty, R error, L loading, O offline/demo. A missing letter is a place to look, not proof of a gap. `actions` counts the action kinds it can propose.*

| Page | App | Script lines | Reads (MIA.*) | Actions | States |
|---|---|---|---|---|---|
| `apps.html` | module_browser | 128 | apps | 2 | EL |
| `asset.html` | garage | 419 | asset, download, grow, upload | 18 | ERL |
| `assistant.html` | assistant | 116 | talk, voice | 0 | ERLO |
| `business.html` | business | 155 | business, emailDrafts, image | 8 | ERL |
| `calendar.html` | calendar | 88 | calendar | 2 | EL |
| `character.html` | character | 83 | character | 0 | ERL |
| `checkin.html` | missions | 72 | checkin | 1 | EL |
| `chronicle.html` | character | 48 | chronicle, image | 0 | L |
| `classroom.html` | classroom | 54 | classroom | 4 | EL |
| `compliance.html` | compliance | 116 | compliance | 6 | EL |
| `council.html` | web_home | 74 | council, councilSay | 0 | RL |
| `dashboard.html` | — | 0 | — | 0 | — |
| `dev-window.html` | — | 483 | dev | 0 | ERL |
| `dev.html` | dev | 483 | dev | 0 | ERL |
| `diagnostics.html` | diagnostics | 28 | diagnostics | 0 | ERL |
| `dungeon.html` | dungeon | 264 | dungeon | 8 | EL |
| `expeditions.html` | expeditions | 196 | download, expeditions, image, upload | 11 | ERL |
| `files.html` | files | 126 | download, files, upload | 3 | ERL |
| `finances.html` | — | 0 | — | 0 | — |
| `flock.html` | flock | 120 | flock | 7 | EL |
| `freedom.html` | freedom | 194 | freedom | 5 | EL |
| `garage.html` | garage | 149 | equipment | 3 | ERL |
| `glasses.html` | — | 1259 | approve, firstBoot, glasses, glassesFeed, glassesOrb, glassesPanel, history, ima | 0 | ERLO |
| `greenhouse.html` | greenhouse | 365 | equipment, grow | 12 | ERL |
| `grow.html` | — | 0 | — | 0 | — |
| `guitar.html` | classroom | 102 | guitar, guitarListen | 0 | ERL |
| `household.html` | household | 30 | household | 1 | E |
| `inbox.html` | inbox | 176 | download, inbox, upload | 3 | ERL |
| `index.html` | web_home | 55 | dashboard, shell, signOut | 0 | EL |
| `insurance.html` | insurance | 160 | insurance, upload | 6 | ERL |
| `issues.html` | issues | 68 | failures | 3 | ERL |
| `journal.html` | notes | 98 | journal | 3 | EL |
| `kept.html` | life_notes | 35 | lifeNotes | 2 | EL |
| `kitchen.html` | kitchen | 311 | fitness, fitnessWeek, image, kitchen | 13 | ERL |
| `knowledge.html` | knowledge | 48 | knowledge, knowledgeArticle | 0 | ELO |
| `label.html` | — | 55 | workshop | 0 | ERL |
| `look.html` | sight | 50 | upload | 0 | ERL |
| `made.html` | made | 189 | made, madeDry, madeImport, madeList, make | 5 | ERL |
| `maintenance.html` | — | 0 | — | 0 | — |
| `maps.html` | maps | 166 | authHeaders, image, maps | 3 | ELO |
| `memories.html` | memories | 37 | memories | 0 | EL |
| `missions.html` | missions | 249 | missions | 15 | EL |
| `model-test.html` | settings | 133 | modelStep, modelTest | 0 | ERL |
| `money.html` | budget | 248 | money | 3 | EL |
| `music.html` | music | 170 | download, music, upload | 7 | ERLO |
| `navigation.html` | navigation | 45 | navigation | 1 | EL |
| `news.html` | good_news | 47 | news | 0 | EL |
| `observations.html` | observations | 31 | observations | 0 | EL |
| `operating.html` | operating_journal | 47 | operatingJournal | 3 | EL |
| `party.html` | missions | 107 | party | 5 | EL |
| `passwords.html` | passwords | 241 | passwords, vaultChange, vaultDelete, vaultImport, vaultLock, vaultReveal, vaultS | 0 | ERL |
| `people.html` | relationships | 93 | people | 1 | ERL |
| `places.html` | expeditions | 85 | places | 3 | EL |
| `plan.html` | workout | 251 | approve, fitness, kitchen, propose, reject, undo | 2 | ERL |
| `play.html` | play | 41 | play | 2 | EL |
| `presence.html` | web_home | 341 | approve, onChange, propose, reject, signIn, state, talk, undo, userSync | 0 | ERLO |
| `profile.html` | profile | 123 | changePassword, newRecoveryCode, profile, signOut | 1 | ERL |
| `property.html` | — | 0 | — | 0 | — |
| `real-estate.html` | real_estate | 145 | equipment, realEstate | 7 | ERL |
| `recipe.html` | kitchen | 209 | image, recipe, upload | 8 | ERL |
| `security.html` | security | 195 | download, image, saveCamera, security | 3 | ERLO |
| `settings.html` | settings | 163 | homeConnect, homeDisconnect, settings, signOut, syncNow | 2 | RL |
| `shop.html` | reward_shop | 76 | shop | 4 | EL |
| `showoff.html` | web_home | 86 | image, showoff | 0 | EL |
| `skills.html` | skills | 128 | skills | 2 | ELO |
| `sync.html` | web_home | 91 | userSync, userSyncStep | 0 | RL |
| `vault.html` | vault | 224 | download, image, vault, vaultFreeDone, vaultFreePlan, vaultNow | 1 | ERLO |
| `workout.html` | workout | 520 | fitness, workout | 15 | ERL |
| `workshop.html` | workshop | 396 | download, image, receiptMatch, upload, workshop | 16 | ERL |
| `worldmap.html` | expeditions | 145 | image, worldmap | 1 | EL |

**Pages with no script of their own** (5): `dashboard.html`, `finances.html`, `grow.html`, `maintenance.html`, `property.html`: redirects or retired screens (Garage, Real Estate and the Calendar absorbed them); confirm and remove or keep as redirects.

## B. Every app (core/web_surfaces.APPS)

| App | Name | Group | Web page | Assistant domains |
|---|---|---|---|---|
| `web_home` | Home | Life, goals & self | `index.html` | — |
| `dashboard` | Dashboard | Life, goals & self | `dashboard.html` | today, alarms, projects, life_events, links, why |
| `dungeon` | The Dungeon | Money & business | `dungeon.html` | dungeon, loop |
| `issues` | Fix-It Log | Knowledge, tools & system | `issues.html` | issues |
| `freedom` | Freedom | Money & business | `freedom.html` | freedom |
| `compliance` | Compliance | Money & business | `compliance.html` | compliance |
| `calendar` | Calendar | Life, goals & self | `calendar.html` | calendar |
| `greenhouse` | Greenhouse | Home, homestead & equipment | `greenhouse.html` | maintenance |
| `flock` | Chickens | Home, homestead & equipment | `flock.html` | flock |
| `garage` | Garage | Home, homestead & equipment | `garage.html` | maintenance, ownership |
| `kitchen` | Kitchen | Home, homestead & equipment | `kitchen.html` | kitchen, groceries |
| `household` | Household | Home, homestead & equipment | `household.html` | household |
| `workout` | Workout | Life, goals & self | `workout.html` | workout |
| `real_estate` | Real Estate | Money & business | `real-estate.html` | real_estate, inventory |
| `missions` | Missions | Life, goals & self | `missions.html` | missions |
| `skills` | Skills | Life, goals & self | `skills.html` | — |
| `budget` | Money | Money & business | `money.html` | budget, debts, homestead_costs, business_use, business_tags |
| `maintenance` | Maintenance | Home, homestead & equipment | `maintenance.html` | — |
| `property` | Property | Home, homestead & equipment | `property.html` | — |
| `workshop` | Workshop | Money & business | `workshop.html` | components, materials, jobs, products, ledger, goods |
| `business` | Orders & Quotes | Money & business | `business.html` | ledger |
| `insurance` | Insurance | Money & business | `insurance.html` | — |
| `security` | Security | Home, homestead & equipment | `security.html` | security |
| `power` | Power | Home, homestead & equipment | **none (desktop only)** | power |
| `character` | Character | Life, goals & self | `character.html` | — |
| `reward_shop` | Reward Shop | Life, goals & self | `shop.html` | — |
| `observations` | Observations | Life, goals & self | `observations.html` | — |
| `relationships` | People & Pets | Life, goals & self | `people.html` | relationships |
| `notes` | Journal | Life, goals & self | `journal.html` | notes, journal, private_journal |
| `classroom` | Classroom | Life, goals & self | `classroom.html` | classroom, textbooks, learning |
| `inbox` | Inbox | Money & business | `inbox.html` | inbox, email |
| `expeditions` | Expeditions | Outdoors & field | `expeditions.html` | expeditions |
| `vault` | Memory Vault | Life, goals & self | `vault.html` | vault |
| `memories` | Memories | Outdoors & field | `memories.html` | — |
| `maps` | Maps | Outdoors & field | `maps.html` | maps |
| `navigation` | Navigation | Outdoors & field | `navigation.html` | waypoints |
| `knowledge` | Knowledge | Knowledge, tools & system | `knowledge.html` | knowledge |
| `toolbox` | Toolbox | Knowledge, tools & system | **none (desktop only)** | toolbox |
| `lab` | The Lab | Knowledge, tools & system | **none (desktop only)** | lab |
| `field_kit` | Field Kit | Knowledge, tools & system | **none (desktop only)** | field_kit, security |
| `passwords` | Passwords | Knowledge, tools & system | `passwords.html` | — |
| `files` | Files | Knowledge, tools & system | `files.html` | — |
| `music` | Music | Knowledge, tools & system | `music.html` | music |
| `operating_journal` | Operating Journal | Life, goals & self | `operating.html` | — |
| `life_notes` | Kept | Life, goals & self | `kept.html` | — |
| `play` | Play | Life, goals & self | `play.html` | — |
| `good_news` | Good News Radio | Knowledge, tools & system | `news.html` | — |
| `sight` | Look | Knowledge, tools & system | `look.html` | — |
| `assistant` | MIA Assistant | Knowledge, tools & system | `assistant.html` | communication, undo, system |
| `diagnostics` | Diagnostics | Knowledge, tools & system | **none (desktop only)** | — |
| `module_browser` | Apps | Knowledge, tools & system | `apps.html` | — |
| `settings` | Settings | Knowledge, tools & system | **none (desktop only)** | accessibility, apps, starters |

## C. The engine's surface

- **API routes** (`server/app.py`): 168 (100 reads, 63 writes).
- **Action kinds** (`core/actions.py`, Propose → Approve → Execute → Record → Undo): 306 in 91 families: answer 1, app 2, asset 5, batch 5, bill 4, boss 2, budget_target 2, camera 1, character 1, communication 1, component 4, course 2, craft 7, craft_recipe 4, creation 3, customer 3, debt 4, dungeon 7, event 2, exercise 3, expedition 4, expense 3, experiment 5, failures 4, firstboot 2, fitness 11, flock 8, freedom 5, gap 2, gear 3, goods 4, grocery 5, grow 4, inbox 3, income 4, income_source 3, insurance 3, insurance_policy 3, insurance_quote 3, job 5, journal 3, lab 3, lesson 3, life_note 2, loop 4, maintenance 2, maintenance_task 3, map 4, market 2, material 4, meal 9, memory 3, mission 7, music 1, myfile 3, objective 3, obligation 6, operating 3, order 6, pantry 3, party 1, pathway 1, person 4, pet 3, place 3, plan 1, play 2, playlist 5, portfolio 1, product 5, profile 1, property 6, quest 3, quote 7, raid 2, recipe 6, records 2, routine 1, sale 2, security 2, setting 1, shop 1, shop_expense 2, shop_reward 3, subject 2, task 1, track 1, training 8, trip 4, waypoint 2, workout 2.
- **Desktop (Qt) modules**: 35: assistant, budget, character, classroom, dashboard, diagnostics, expeditions, field_kit, files_mod, garage, greenhouse, household, inbox, kitchen, knowledge, lab, maintenance, maps, memories, missions, module_browser, music, navigation, notes, observations, power, property, real_estate, relationships, settings, skills, toolbox, web_home, workout, workshop.
- **Phone app (Kotlin)**: 15 files: Engine.kt, Gallery.kt, GlassesService.kt, ListenService.kt, ListenTile.kt, MainActivity.kt, MetaGlasses.kt, Music.kt, Permissions.kt, PhoneVoice.kt, Places.kt, Relay.kt, Share.kt, Unpack.kt, Voice.kt.

## D. Design tokens and shared components

- **Tokens** (`web/tokens.css`): 128 declarations (colors as hex and as r,g,b triplets, type scale, spacing, radii, motion, per-app `--mod-*` colors, rarity colors, the orb size).
- **Shared component classes** (`web/components.css`): 41: `.attention-panel`, `.btn`, `.btn-amber`, `.btn-ghost`, `.btn-green`, `.chip-ico`, `.empty`, `.flame`, `.glass`, `.hero`, `.hero-missions`, `.hero-skills`, `.layout`, `.layout-main`, `.locked`, `.mia-line`, `.mod-estate`, `.mod-finance`, `.mod-garage`, `.mod-kitchen`, `.mod-missions`, `.mod-skills`, `.mod-workout`, `.ptabs`, `.r-common`, `.r-epic`, `.r-legendary`, `.r-rare`, `.r-uncommon`, `.rarity`, `.rarity-tag`, `.row`, `.rows`, `.sect`, `.side`, `.sign-in`, `.stag`, `.stat`, `.status-line`, `.strip`, `.xpbar`.
- **The concept layer** (`web/concept.css`, 1,793 lines): 621 classes, the page compositions.
- **Literal colors outside tokens.css**: 141 lines with a hex or numeric rgba (many are black shadows `rgba(0,0,0,...)`, which the rule allows in spirit; the rest are drift from DEC-0023's "never a hard-coded color"). First ones: components.css:363, components.css:364, components.css:365, components.css:370, components.css:371, components.css:372, components.css:479, components.css:539, components.css:540, components.css:556.
