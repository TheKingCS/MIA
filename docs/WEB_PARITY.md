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
| Budget: Bills | List, add, edit, delete, mark paid, autopay, due dates | `budget__01_bills` | |  | |
| Budget: Income sources | List, add, edit, delete, mark received | `budget__02_income_sources` | |  | |
| Budget: Income | Log, edit, delete income | `budget__03_income` | |  | |
| Budget: Expenses | Log, edit, delete, categories, business tags, receipts | `budget__04_expenses` | |  | |
| Budget: Debts | Payoff order (avalanche/snowball/hybrid) and why, promo APR countdowns, record payments, add/edit | `budget__05_debts` | |  | |
| Budget: Summary | Monthly plan, totals, net worth | `budget__06_summary` | | summary only | |
| Budget: Trends | Spending and income over time | `budget__07_trends` | |  | |
| Budget: Bank sync | Plaid status, sync, linked accounts | `budget__08_bank_sync` | |  | |
| Real Estate | Properties: value, equity, mortgage, rent, cash flow, depreciation, maintenance, sell | `real_estate` | | summary only | |
| Workshop: Components | Parts inventory: add, edit, use | `workshop__01_components` | |  | |
| Workshop: Materials | Fabrication materials | `workshop__02_materials` | |  | |
| Workshop: Jobs | Costed jobs | `workshop__03_jobs` | |  | |
| Workshop: Products | Products | `workshop__04_products` | |  | |
| Workshop: Ledger | Sales ledger | `workshop__05_ledger` | |  | |
| Garage | Vehicles and equipment: tracked, overdue, next up, asset cards with tasks | `garage` | | summary only | |
| Asset page | One asset: overview, maintenance, missions, documents, parts, history, meter hours | `(concept: the mower page)` | |  | |
| Property | House, appliances, tools | `property` | |  | |
| Greenhouse | Garden, greenhouse and aquaponics assets and tasks | `greenhouse` | |  | |
| Household | Routines with streaks | `(none)` | |  | |
| Maintenance: Assets | Add, edit, delete assets | `maintenance__01_assets` | |  | |
| Maintenance: Tasks | Recurring tasks (calendar or meter-based), mark complete, log hours | `maintenance__02_tasks` | |  | |
| Maintenance: Overview | Calendar overview | `maintenance__03_overview` | |  | |
| Maintenance: Monitor | Sensor monitor | `maintenance__04_monitor` | |  | |
| Kitchen | Recipes, pantry, grocery list, meal log, suggestions, what can I make | `kitchen` | | summary only | |
| Power: Battery | Battery status | `power__01_battery` | |  | |
| Power: Energy sources | Energy and utility tracking | `power__02_energy_sources` | |  | |
| Missions | Missions with objectives, difficulty, XP and credit rewards, MIA-assigned, add/edit, tick objectives, complete | `missions` | | summary only | |
| Skills | Skill tree, levels, XP, tiers, locked skills | `skills` | | summary only | |
| Character | Lifetime stats, prestige, cosmetic rewards | `character` | |  | |
| Dashboard | Recent activity, missions, memories, events, projects, tasks | `dashboard` | |  | |
| Observations | What MIA noticed | `observations` | |  | |
| Workout | Exercises, templates, log a session, history, progress, PRs, rest timer | `workout` | | summary only | |
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
