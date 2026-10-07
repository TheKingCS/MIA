# Concept audit: the pictures vs. what MIA has (2026-10-07)

*Claude, at Zac's request after trying MIA on his phone. Compares both
concept sets with the screens as they are today, on a phone and the
desktop:*
- *the desktop sheet: Home, Greenhouse, Garage, Kitchen, Workout, Real Estate, Missions, Skills;*
- *the mobile set (`MOBILE_CONCEPT.md`).*

*✅ = matches · 🟡 = there, but not like the picture · ❌ = missing.
The build list at the end orders the gaps.*

## Everywhere

| In the concept | Now |
|---|---|
| Photo hero fading into the dark, round glowing icon badge, name, tagline | ✅ all 14 photos in (ChatGPT's Home and Greenhouse, Muse's twelve) |
| **Weather chip** on every hero ("☀ 72°F") | ❌ MIA has no weather source; Home shows only the date |
| Status strip: three tiles, **each with an icon** and a second line ("5 assets", "2 overdue", "3 upcoming") | 🟡 the counts are there; no icons, no second line |
| Needs-attention card with a **bulleted list** ("Prune tomatoes (overdue 5d)") | 🟡 ours is rows with Done buttons (more useful), but bulkier than the picture |
| **Photos of things** (each asset, recipe, property) | ❌ no photo field yet (Q-0014: yes, stored in the person's data folder) |
| Segmented tabs in the screen's color | ✅ |
| Desktop sidebar | 🟡 ours lists every web app; the concept's also has **Household** and **Settings** |
| Level card (avatar, level, XP) | ✅ (character art later) |
| Every card the phone's width | ✅ fixed 2026-10-07 |

## Screen by screen

| Screen | In the concept | Now | Gap |
|---|---|---|---|
| **Home** | Logo and gear; hero with date and weather; Today's Focus checklist; quick actions (Quick Add, Voice, Calendar, Journal, MIA Assistant); level card | Everything except weather. The gear menu (Profile, Settings, Log out) was added 2026-10-07. The saying card was removed at Zac's request | Weather. A real **Profile** page and **Settings** page (the menu points to Character and app management for now) |
| **Apps** | Title and search; two-column grid of big glowing tiles | ✅, plus Favorites; the Apps tile itself removed 2026-10-07 | None |
| **Greenhouse** | Strip; needs-attention bullets; an asset card with a **photo**, its tasks with due dates, and **Related Missions** beside them | Strip, needs attention, asset cards with tasks | Asset photos; related missions on the card (the asset page has them); strip icons |
| **Garage** | Asset cards with **photos** (mower, truck, car), three tasks each with due chips, an arrow to open | Cards with tasks and chips, tap to open | Photos |
| **Kitchen** | Recipe cards with a **food photo** and a **tag** ("Healthy", "Comfort"), time and servings, ingredients, View Recipe; a locked card with a lock picture and the mission to unlock; Pantry with **an icon per item** and quantities on the right; Grocery List with checkboxes and Add item | Everything except the photos, tags and pantry icons; ours also has Meal Log and Suggestions | Recipe photos; a recipe tag (diet or mood; we show the meal); pantry icons |
| **Workout** | Tabs (Exercises, Templates, **Log Session**, History, Progress); Log Session with the date shown; Latest Entry with a ✓; Daily Mission with progress, "20/20 complete" and streak; Recent History as **date columns** | ✅ all of it, Log Session first | Small: show today's date on the form; history as columns on wide screens |
| **Real Estate** | Property list with **photos**, address, rent, balance; a **detail panel** for the chosen property: beds and baths, status chip, **Entity (LLC, EIN)**, rental income, **expenses broken down** (mortgage, taxes, insurance), cash-flow summary, next maintenance with Add Task, related missions, **Sell it** | Cards with status, location, rent, balance, equity, cash flow and this month; record rent, add expense, track upkeep; Maintenance and Missions tabs | Photos; a detail panel; beds and baths; the owning entity (the engine has entities); expense breakdown; Add Task in place; **Sell** (the PC app has it) |
| **Money** | Net worth with a **trend line**; income and expense tiles; debt and savings; upcoming bills with icons | Everything except the trend line and bill icons | Net-worth history and its line; bill icons |
| **Missions** | "World Missions"; **All**, Active, Completed; an **MIA ASSIGNED** filter; rows with icon, +XP, objectives line, **streak**; a Completed panel with the XP earned | Active (ready first), Daily, Completed, Set aside; cards with progress, rewards, MIA badge | An **All** view; an MIA-assigned filter; streak on non-daily missions; compact rows option |
| **Skills** | **Capability Status** (overall level, XP bar); **Achievements 23/86**; Next Honest Step; area chips (**All**, Health, Finance, Homestead, Tech, Creative, Adventure); **one card per area** with tier, level, XP bar, Unlocked/Locked | Strip (touched, demonstrated, level); category tabs; one card per skill; next honest step, prestige, recent achievements, rewards | **Area summary cards** (tier, level and XP per area) as the first view, skills inside each; an **All** chip; achievements as a count (x of y); a capability/XP bar card |
| **Character** | (not in the concept) | Level, stats, collection, top skills | Character art (later, Zac's call) |
| **MIA Assistant** | Badge, chat, mic | ✅ on the computer. On the phone, Talk needs a model (Phase 2) | On-phone model |

## Not in the pictures, but needed (from Zac, 2026-10-07)

- ✅ **Onboarding on the phone:** create your account (name, email, password, country, interests) on first start instead of "You" (done 2026-10-07).
- **Profile page:** your name, email, password, household, photo.
- **Settings page** on the web: the PC app's Settings (theme, notifications, privacy, phone access, apps).

## Build list (in order)

1. **Onboarding (✅ 2026-10-07), Profile and Settings.** Without these, the phone app can't belong to anyone. This is Phase 2's first step.
2. **Photos of things:** one photo field and upload, shared by assets, recipes and properties. It lifts Garage, Greenhouse, Kitchen and Real Estate at once.
3. **Skills like the concept:** area cards with tier, level and XP first; All; achievements x/y; the capability bar.
4. **Missions like the concept:** All, an MIA-assigned filter, streaks on rows.
5. **Real Estate detail panel:** entity, beds and baths, expense breakdown, Sell, Add Task in place.
6. **Status-strip icons and second lines** everywhere; bulleted needs-attention on narrow screens.
7. **Weather:** a source that works offline-first (the phone's location plus a forecast when online; nothing personal leaves the phone but a rough location). Needs Zac's OK because it's MIA's first outside call for the screens.
8. **Money's net-worth trend:** daily snapshots, then the line.
9. **Small touches:** Kitchen tags and pantry icons, Workout's date on the form, Household in the sidebar.
