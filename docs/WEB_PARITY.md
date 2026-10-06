# Web parity: all of MIA on the web (DEC-0017)

*Every screen and operation of the working MIA (the Qt app), and where
its web version stands. Claude keeps this current; a module's Qt
screen retires only when all three boxes are ticked.*

- **API**: the engine serves everything the screen reads, and every
  operation as an action kind (propose → approve → undo).
- **Works**: the web screen does everything the Qt screen does, tested
  against the real engine.
- **Look**: matches Zac's concept pictures (Muse's sign-off).

Screens: `docs/design_handoff/screens/<name>.png` (placeholder data).
"Summary only" means a web screen exists but reads only Life State's summary (before DEC-0017).

| Screen | What it does | Reference | API | Works | Look |
|---|---|---|---|---|---|
| Shell | Sidebar of apps (per person, child-safe), level and XP, date, search (Ctrl+K), Talk to MIA, the orb | `00_main_window_home` | |  | |
| Home | Greeting, Today's Focus (tick to do), quick actions, at-a-glance cards (money, maintenance, kitchen, workout, real estate, net worth, observations, captures), daily briefing | `00_main_window_home` | ✅ `/api/dashboard` (Home is MIA's face + chat; this is the Dashboard page) | ✅ greeting, focus with tick → confirm → undo, quick actions, upcoming, wins, glance (not yet: net worth, observations, captures cards; spoken briefing) | |
| Budget: Bills | List, add, edit, delete, mark paid, autopay, due dates | `budget__01_bills` | ✅ `/api/money` + money actions | ✅ list, add, edit, delete, mark paid (undo) | |
| Budget: Income sources | List, add, edit, delete, mark received | `budget__02_income_sources` | ✅ `/api/money` + money actions | ✅ list, add, edit, delete, mark received | |
| Budget: Income | Log, edit, delete income | `budget__03_income` | ✅ `/api/money` + money actions | ✅ last 90 days, log, edit, delete | |
| Budget: Expenses | Log, edit, delete, categories, business tags, receipts | `budget__04_expenses` | ✅ `/api/money` + money actions | ✅ last 90 days, log, edit, delete, find (not yet: business tags, receipt items) | |
| Budget: Debts | Payoff order (avalanche/snowball/hybrid) and why, promo APR countdowns, record payments, add/edit | `budget__05_debts` | ✅ `/api/money` + money actions | ✅ payoff order + why under avalanche/snowball/hybrid, promo countdown, record payment, add, edit, delete | |
| Budget: Summary | Monthly plan, totals, net worth | `budget__06_summary` | ✅ `/api/money` + money actions | ✅ this month, monthly plan, net worth, spending by category, next two weeks; budget targets set/change/remove | |
| Budget: Trends | Spending and income over time | `budget__07_trends` | ✅ `/api/money` + money actions | ✅ last six months in and out | |
| Budget: Bank sync | Plaid status, sync, linked accounts | `budget__08_bank_sync` | ✅ `/api/money` + money actions | status only (connect and sync need the vault passphrase: PC app) | |
| Real Estate | Properties: value, equity, mortgage, rent, cash flow, depreciation, maintenance, sell | `real_estate` | ✅ `/api/real-estate` + property actions | ✅ property cards (status, where, rent, balance, equity, payment, cash flow, this month), add, edit, delete, record rent, add expense (both into Money), track upkeep (its Maintenance asset) with Done, related missions (not yet: depreciation, sell, photos) | |
| Workshop: Components | Parts inventory: add, edit, use | `workshop__01_components` | |  | |
| Workshop: Materials | Fabrication materials | `workshop__02_materials` | |  | |
| Workshop: Jobs | Costed jobs | `workshop__03_jobs` | |  | |
| Workshop: Products | Products | `workshop__04_products` | |  | |
| Workshop: Ledger | Sales ledger | `workshop__05_ledger` | |  | |
| Garage | Vehicles and equipment: tracked, overdue, next up, asset cards with tasks | `garage` | ✅ `/api/equipment?scope=garage` + equipment actions | ✅ tracked / needs attention / next up, asset cards with tasks, Done (with meter value), add asset | |
| Asset page | One asset: overview, maintenance, missions, documents, parts, history, meter hours | `(concept: the mower page)` | ✅ `/api/assets/{id}` + document upload/download | ✅ quick stats + log readings, needs attention, Overview / Maintenance (add, edit, delete, done, log) / Missions / Documents (upload, open, remove) / Costs / History; Parts PLANNED (not tracked per asset yet) | |
| Property | House, appliances, tools | `property` | ✅ `/api/equipment?scope=property` | ✅ same as Garage, for appliances, the property and tools | |
| Greenhouse | Garden, greenhouse and aquaponics assets and tasks | `greenhouse` | ✅ `/api/equipment?scope=greenhouse` | ✅ same as Garage, for garden and plants (child-safe) | |
| Household | Routines with streaks | `(none)` | |  | |
| Maintenance: Assets | Add, edit, delete assets | `maintenance__01_assets` | ✅ `/api/equipment?scope=maintenance` | ✅ every asset, add, edit, delete (undo) | |
| Maintenance: Tasks | Recurring tasks (calendar or meter-based), mark complete, log hours | `maintenance__02_tasks` | ✅ maintenance_task actions, maintenance.done, maintenance.reading | ✅ every task, calendar or meter-based, done, log reading, add, edit, delete | |
| Maintenance: Overview | Calendar overview | `maintenance__03_overview` | ✅ calendar in `/api/equipment` | ✅ the next two months by day | |
| Maintenance: Monitor | Sensor monitor | `maintenance__04_monitor` |  | not yet (sensor graphs) | |
| Kitchen | Recipes, pantry, grocery list, meal log, suggestions, what can I make | `kitchen` | ✅ `/api/kitchen` + kitchen actions | ✅ recipe cards (missing, makeable, locked with the mission that unlocks it), view, add, edit, delete, ingredients one per line, favorite, log meal, add missing to the list; pantry add/edit/remove with use-by; grocery add, check off, clear checked; meal log; suggestions (not yet: ratings, photos) | |
| Power: Battery | Battery status | `power__01_battery` | |  | |
| Power: Energy sources | Energy and utility tracking | `power__02_energy_sources` | |  | |
| Missions | Missions with objectives, difficulty, XP and credit rewards, MIA-assigned, add/edit, tick objectives, complete | `missions` | ✅ `/api/missions` + mission actions | ✅ Active (ready first) / Daily (streaks) / Completed / Set aside; mission sheet with objectives (+1, add, remove; task and trip objectives count themselves), rewards and skills taught, MIA-assigned badge, group quest party and your part, pathway step, linked asset, recipes it unlocks; add, edit, delete, complete, give up (with why), pick back up; ask MIA for one; rewards go to whoever approves | |
| Skills | Skill tree, levels, XP, tiers, locked skills | `skills` | ✅ `/api/skills` | ✅ categories (your interests first), skill cards (level, XP, capability, this week, what a locked one needs), next honest step, pathways per skill (start), challenge chains with rarity, hidden achievements, recent achievements, prestige (not yet: drawn prerequisite lines) | |
| Character | Lifetime stats, prestige, cosmetic rewards | `character` | ✅ `/api/character` | ✅ level, prestige and emblems, lifetime XP and credits, lifetime stats, collection by rarity with the tally, top skills, latest missions (character art: later, Zac's call) | |
| Dashboard | Recent activity, missions, memories, events, projects, tasks | `dashboard` | |  | |
| Observations | What MIA noticed | `observations` | |  | |
| Workout | Exercises, templates, log a session, history, progress, PRs, rest timer | `workout` | ✅ `/api/workout` + workout actions | ✅ inline log (an exercise or a template), latest entry, daily mission with progress and streak, week/minutes/streak, exercises with PRs, templates (add/remove exercises, log it), history, progress lines (not yet: rest timer, guided session) | |
| People | People: birthdays, gift ideas, notes | `relationships__01_people` | |  | |
| Pets | Pets: vet history | `relationships__02_pets` | |  | |
| Notes | Dated, tagged notes and journal | `notes` | |  | |
| Classroom | Subjects, courses, lessons, textbooks and study | `classroom` | |  | |
| Expeditions | Trips: routes, gear, weather, distance | `expeditions` | |  | |
| Memories | Trip recaps, stats, photos | `memories` | |  | |
| Maps: Waypoints | Waypoints | `maps__01_waypoints` | |  | |
| Maps: Basemap | Offline basemap | `maps__02_basemap` | |  | |
| Maps: Trail maps | Trail map PDFs | `maps__03_trail_maps` | |  | |
| Navigation | Distance, bearing, sun and moon | `navigation` | |  | |
| Assistant | Full chat with MIA, history, voice | `assistant` | |  | |
| Inbox | Documents to file, email intake | `(none)` | |  | |
| Calendar | Events and alarms | `(inside Dashboard/Home)` | |  | |
| Knowledge | Offline reference library | `knowledge` | |  | |
| Toolbox | Calculators and conversions | `toolbox` | |  | |
| The Lab | Sensor experiments | `lab` | |  | |
| Field Kit: Devices | Connected devices | `field_kit__01_devices` | |  | |
| Field Kit: Scripts | Scripts | `field_kit__02_scripts` | |  | |
| Field Kit: Security | Security | `field_kit__03_security` | |  | |
| Files | File browser | `files` | |  | |
| Music: Library | Music library | `music__01_library` | |  | |
| Music: Playlists | Playlists | `music__02_playlists` | |  | |
| Modules | Turn apps on and off, install | `module_browser__01_modules` | ✅ `/api/apps`, `app.visibility` | ✅ every app by life area, what MIA can do in each (201 tools), open or ask MIA, show/hide per person with undo (not yet: device-wide enable/disable, install, rescan) | |
| Settings | Theme, profile, household, options | `settings` | |  | |
| Diagnostics | System health | `diagnostics` | |  | |
