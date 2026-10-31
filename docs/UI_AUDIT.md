# Page and App Usage Audit

*Claude, 2026-10-30, at Zac's request ("audit page usage and app usage
and create a prompt for Claude Design"). Step 2 of
`docs/BODY_AND_RELATIONSHIP_PLAN.md` (the UI inventory). The design brief
it feeds is `docs/design/CLAUDE_DESIGN_PROMPT.md`. Counts only: nothing
personal is in this file.*

## 1. What MIA could measure, and what she couldn't

| Evidence | What it holds | On this PC |
|---|---|---|
| App opens on the desktop (`data/module_usage.json`, `core/usage_tracker.py`) | each desktop app's first and last open and count | since 2026-10-19 |
| The activity log (`data/activity_log.json`) | a narrative of what happened (5,000 entries kept) | 21 entries |
| Life events (each person's history) | what was done (missions, practice, weigh-ins...) | 24 events |
| Conversations | what was said to MIA | 20 conversations, 15 things asked |
| Records in each app | how much each app holds | below |
| **Web pages opened** | **nothing recorded anywhere** | **none** |

**The gap:** the web screens are now most of MIA (the phone, the
glasses, and the desktop's Home through `web_home`), and none of them
counted a visit, so which pages are used was unknowable. **Fixed today:**
every web screen counts itself when it opens (`web/shell.js` →
`/api/usage/page` → `data/page_usage.json`: count, first, last; nothing
about what was on the page). Re-run this audit after a few weeks of use.

Also: Zac used MIA mostly on his phone while he was away from the PC,
and the phone keeps its own data (DEC-0019), so this PC's numbers are a
small slice. The phone's own `page_usage.json` starts counting once it
runs this version.

## 2. What the evidence shows

- **Desktop apps opened (6 of 44):** Settings 6, Missions 5, Diagnostics,
  Observations, Greenhouse and Money once each.
- **What's in the apps (this PC):** missions 19 (most of them the fitness
  plan's), recipes 7, a vehicle with its oil change, a property, an
  expedition, two grocery items; no bills, debts, spending, calendar
  events, projects, notes, memories or people yet.
- **What happens:** 18 of the 24 history events are missions that quietly
  lapsed (the fitness plan's daily missions), 2 skill practices, a
  weigh-in, a plan change, one mission completed.
- **What's asked of MIA:** 15 questions; the ones on screen were about
  what she can do, the calendar, and adding things.

**Read honestly:** MIA is barely used yet on this computer. The most
used things are Missions (the fitness plan's daily missions, mostly left
to lapse) and Settings (setting things up). Money is empty until the
banks are linked (the Plaid session is first on the list). The heavy
use, by Zac's account, is talking to MIA, on the phone.

## 3. The structure (what exists and how it's reached)

| | Count |
|---|---|
| Apps | 47 (3 retired: Dashboard, Maintenance, Property) |
| With a web screen | 31 |
| Desktop only (no web screen yet) | 13: Household, Power, Observations, Classroom, Memories, Maps, Navigation, Knowledge, Toolbox, The Lab, Field Kit, Diagnostics, Settings |
| Web pages | 51 |
| Pages that aren't an app's own screen | 17: asset, checkin, chronicle, finances, glasses, grow, label, model-test, party, places, plan, presence, profile, recipe, settings, showoff, worldmap |
| Sidebar groups | 5: Life, goals & self · Money & business · Home, homestead & equipment · Outdoors & field · Knowledge, tools & system |

**Findings:**

1. **Two pages nothing links to:** `finances.html` (titled "Money") and
   `grow.html` (titled "Greenhouse") look like earlier versions of the
   Money and Greenhouse screens (`budget.html`, `greenhouse.html`).
   Verify, then retire them.
2. **`presence.html`** is the leftover of DEC-0044, reverted by DEC-0045
   (one link left). Retire it.
3. **Settings** has a web page (`settings.html`, reached from 2 places)
   but the app list still calls Settings desktop-only: the list is out of
   date, or the page is partial (`docs/WEB_PARITY.md` decides).
4. **Sub-pages reached from one place only:** the Sunday check-in, the
   Chronicle, Party, World Map, Recipe, Label, Show-off. Each is fine as a
   sub-page, but most people won't find them by browsing: they're
   reached best by MIA ("show me my chronicle", "start the check-in").
5. **Thirteen apps aren't on the phone or glasses at all** (desktop
   only): the reason for DEC-0017's web parity work, still open.
6. **Breadth vs use:** 44 apps for a person who uses a handful. DEC-0045
   keeps the apps as the layout, so the answer isn't fewer apps on the
   page: it's MIA reaching into them, by voice and in Talk, so the person
   doesn't dig (and favorites pinning what they use, which exists).
7. **Missions lapse quietly:** 18 lapsed fitness missions in two weeks
   says the plan asks for more than is being done. Not a UI fault, but
   a design question: how MIA shows a plan that's too big, without guilt
   (DEC-0014), and offers to right-size it.

## 4. What to measure next

After two to four weeks with page counting on: each page's opens per
week on each device; apps never opened; how often a thing is done by
voice vs on a screen (the actions record `proposed_by`: "mia" for voice
and quick commands); which sub-pages are reached at all. Then score each
screen (used, findable, does its job) as the body plan's step 2 intends.
