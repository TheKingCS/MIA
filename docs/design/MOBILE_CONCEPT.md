# The mobile concept (DEC-0018)

*The phone set ChatGPT made for Zac on 2026-10-06 is the target look.
The picture stays out of this public repo (it shows a real name and
addresses), so this file describes it, panel by panel. It's the build
checklist: each panel lists what it shows and where the data comes from.
Placeholders only.*

## Everywhere

- **Material:** a deep green-black background. Each screen opens on a
  photo (`web/img/<screen>.jpg`, `docs/design/IMAGE_REQUESTS.md`) that
  fades into the dark. Cards are dark glass with a thin glowing border
  in the screen's color. Glow is soft, never neon-bright.
- **Header:** a round glowing icon badge, the screen's name, its tagline
  under it, and a weather chip top right ("☀ 72°F").
- **Status strip:** three small tiles, each with an icon, a label and a
  count: Tracked (green), Needs attention (red), Next up (blue).
- **Needs attention:** a red-bordered card with a bulleted list
  ("Engine oil change (120d)").
- **Tabs:** a segmented bar; the active tab is filled with the screen's
  color.
- **Bottom bar (phone):** Home, Apps, Dashboard, More. The active item
  glows in the screen's color. **More** opens the menu drawer.
- **Colors:** Greenhouse green, Garage orange, Kitchen red, Workout
  blue, Real Estate teal, Finances purple, Missions and Skills gold.

## The panels

| Panel | What it shows | Data |
|---|---|---|
| **Home** | MIA logo and name with the settings gear; the photo hero with the date and weather chip, "Good morning, ‹name›" and "Another day to build the life you want."; Today's Focus as a checklist; the day's saying in its own card; quick actions (Voice, Calendar, Journal, MIA Assistant); level and XP | `/api/dashboard`, `/api/shell` |
| **Apps** | "Apps: Your modules. Your world." with search; a two-column grid of big glowing tiles (icon, name, tagline) in each app's color | `/api/apps` |
| **Greenhouse / Garage** | Header; the status strip; Needs attention; "Assets" with an arrow, as photo cards (picture, name, kind, its tasks with overdue in red, or a meter like "120h") | `/api/equipment` |
| **Kitchen** | Tabs: Recipes, Pantry, Grocery List (and Meal Log, Suggestions); recipe cards with a photo, "Healthy · 30m · 2 servings", ingredients, View Recipe; a locked recipe card ("Complete the mission … to unlock"); Pantry and Grocery List side by side, with checkboxes and Add item | Kitchen: still Life State only. Its full API is next. |
| **Workout** | Tabs: Exercises, Templates, Log Session, History; a Log Session form (exercise, reps, sets, notes, Save Session); Latest Entry; Daily Mission with progress and streak; Recent History | Workout: still Life State only. Its full API is next. |
| **Real Estate** | Tabs: Properties, Maintenance, Missions; property cards with a photo, name, place, rent per month, balance and a status chip (Rented / For Sale); Add Property | Real Estate: still Life State only. Its full API is next. |
| **Finances** | Tabs: Overview, Bills, Income, Debts; Net Worth with a trend line and change; Monthly Income and Monthly Expenses tiles; Total Debt and Savings tiles; Upcoming Bills with icons | `/api/money` (the net worth trend needs history; see the end of this file) |
| **Missions** | "World Missions" with All, Active and Completed; each mission with its icon, XP reward, a progress bar with a count (3/6) and its objectives line | Missions: H-0013 is next |
| **Skills** | Capability Status (overall level, XP to the next level); tabs by area (All, Health, Finance, Homestead, Tech); skill cards with tier, level, an XP bar, and Unlocked or Locked | Skills: H-0013 is next |
| **MIA Assistant** | MIA's badge, "Always here. Always with you.", the chat (her replies in cards, yours in green bubbles), a message box with a mic button | `/api/voice/text` (Talk) |
| **Menu drawer** | MIA logo; Home, Apps, Dashboard, Missions, Skills, Settings, Help & Support; level and XP at the bottom; a photo strip beside it ("Better Systems. Bigger Dreams.") | `/api/shell` |

## Still to build for the look (engine)

- **Weather:** MIA has no weather source yet. The chip stays hidden until one exists.
- **Photos of things:** assets, properties and recipes have no photo field yet.
- **Net worth history:** for the trend line.
- **Skill tiers, achievements and locked skills:** H-0013.
- **Kitchen, Workout and Real Estate:** full APIs.
