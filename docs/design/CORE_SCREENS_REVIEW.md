# Review: Claude Design's "MIA Core Screens" against what MIA does

*Claude, 2026-11-07, at Zac's ask ("go through the screens and take note of what you think may need to change and
check them against what MIA does"). The canvas: https://claude.ai/artifact/21C1QCV2TjdSPCizVrxdoc (66 screens: 3 PC,
61 phone, 2 glasses). Each point says what the screen shows, what MIA really does, and the change.*

## Since this review (2026-11-07, night)

The canvas session built most screens in the canvas's look (DEC-0113 approved). Done since: Kitchen Cook Mode
(steps, timers, by voice), Power, Toolbox, The Lab and Field Kit on the phone, Settings' humor as a five-step
choice, the Security cameras by voice, glasses asks for nearly every app, and "Say: …" under every screen's title
(section 4). Still true below: section 1's six design changes (none of them was built as drawn), and section 3's
missing screens (Browser, Start Here, Waiting For You, a plan's page, Recent changes).

## 1. Shown, but MIA doesn't work that way (change the design)

| Screen | Shows | What MIA does | Change |
| --- | --- | --- | --- |
| Home (PC and phone) | "Pay From Savings" on the electric-bill finding | MIA never moves money: bank data is read-only (Plaid), she marks bills paid and drafts emails | Buttons she can do: Mark Paid, Remind Me on the 5th, Draft an Email Asking to Move the Due Date |
| Talk | Proposes "Plan the coop for 15 Nov in Budgets: $340 from Homestead" | No "plan a purchase" action; the near ones are the build budget (Workshop), Freedom's build order, a calendar event | Design to one of those, or Zac asks for a planned-purchase action and Claude builds it |
| Settings | "Speak replies aloud"; Humor as an on/off switch | No speak-replies setting (the phone always speaks when you talked to it); humor is five levels (off, rare, sometimes, often, lots) | Humor as a five-step choice; drop speak-replies or make it "Speak when I typed, too" |
| Party, Profile, Sign In | A household guild leaderboard; "The Ridge House · 3 people"; "Each person in the house has their own account" | DEC-0119: MIA is for Zac alone | Cut Party (or make raids solo), drop the household lines |
| World Map | "38 sq mi cleared", "Cartographer · 50 sq mi" | Counts cleared tiles, places and photos, not square miles | Tiles, places, photos |
| Inbox | Photo, File, Note, and items waiting | Also reads his email for receipts and files them on its own, each with Undo (DEC-0120, DEC-0121), with email setup and unlock | Add "Filed by MIA From Your Email" with Undo, and the email setup and unlock card |
| Workout | "MIA Pace" as a way a rep is counted | The code calls it cadence (said, cadence, told, tapped) | Fine either way; keep the words in step |

## 2. Designed, not built yet (MIA needs building, or the design waits)

- ~~**Kitchen Cook Mode**~~: built by the canvas session (steps, timers, by voice).
- ~~**Power, Toolbox, The Lab, Field Kit on the phone**~~: built 2026-11-07.
- **The orb's seven states and the per-app atmosphere colors**: proposals (MIA_DESIGN_SYSTEM.md, DEC-0113) waiting
  on Zac. The Cook Mode and Workout screens already use the atmosphere colors.

## 3. Missing screens

- **Browser** (DEC-0117): the live view, the steps waiting for your OK, teaching a task.
- **Start Here** (the guide) and the **Waiting For You** queue the audit proposes for Today.
- **A plan's page**: the material list, cut list and shopping list (Knowledge only shows the Plans Shelf tab).
- ~~**Recent changes / Undo history**~~: built 2026-11-07 (`web/changes.html`, from Settings). Notifications still to do.
- **Glasses**: 2 screens (Home, Active Training) against 21 glasses gaps in docs/PARITY.md. Each app needs its
  glasses card and its "ask" (DEC-0125).

## 4. Voice on every screen (DEC-0125)

Some screens already say what to say ("Or say 'MIA, start my workout'", Cook Mode's "Next step · Go back", the
Navigation waypoint line). Most don't (Money, Insurance, Kept, Skills...). Suggest one pattern for all: a quiet
"Say: …" line on each screen, taken from the app's own ask (core/web_surfaces.py `App.ask`).

## 5. Matches MIA well (keep)

Freedom (the range, "one shift buys", what moves the day), the Dungeon (hard-mode tags, overtime boss), Chickens
(lay rate, feed per dozen, cartons), Insurance (quotes compared, "MIA drafts, you send"), Kept, Operating Journal,
Guitar (checks MIA hears), Compliance ("only you can mark one verified"), Files ("only this folder"), Passwords
(screen only, hides after seconds), Diagnostics ("looks only"), Fix-It Log, Observations, Security, Memory Vault,
Talk's answer figures (Fact, Calculation, Estimate, Missing) and Propose, Approve, Undo. The theme is MIA's own
(DEC-0023 tokens, copied into each screen rather than installed as a design system).

## 6. Found in MIA while checking (Claude's to fix)

- ~~**The PC can't be talked to in web mode.**~~ Fixed: Talk has a mic on every page.
- ~~**Humor has no control on a screen**~~: Fixed: Settings, "How funny MIA is".
