# MIA's design standards: a handoff to MIA

*Claude, 2026-11-07, at Zac's request: "a document to hand off to MIA so she can understand the design principles
and specs, so that as she develops herself she can use the same standards." It gathers in one place what
`STARK_INTERFACE.md` (DEC-0023, the look that's built), `MIA_DESIGN_SYSTEM.md` and `MIA_VISUAL_IDENTITY.md` (H-0087,
proposed), `MIA_VOICE.md`, `web/README.md` and the app template (`applications/TEMPLATE.md`) agree on, plus the core
screens drawn on Zac's design canvas ("MIA Core Screens": PC, Phone and Glasses pages). Where those documents and this
one ever disagree, they win: this is a summary for you, not a new source of truth. Values live only in
`web/tokens.css`.*

**Status words used below.** **Built** = in `web/` today, follow it. **Proposed** = in DEC-0113 or the design-system
draft, waiting for Zac. Design with it only in a concept, never ship it in `web/` until Zac approves (Muse's
commitment in H-0091). **Rule** = an approved decision; it never bends.

## 1. Who MIA is, visually

MIA is a presence, not a collection of apps. Every screen is a place she's in. The interface should feel like
technology from a near future that someone careful built for themselves: precise, quiet, warm under the precision.
An inventor's own operating system.

- Words for it: intelligent, capable, confident, warm, calm, exact.
- Not: cyberpunk, neon, a gaming dashboard, a movie prop, glassmorphism for its own sake, a wall of glowing widgets.
- The one-line test for any screen: does it look like the same her on the phone, the desktop and the glasses?

## 2. The rules that never bend

1. **Tokens only** (DEC-0023). Never a hard-coded color. Use a token, or `rgba(var(--rgb-accent), 0.3)` for a faint
   version. A new value goes into `web/tokens.css` first, then gets used.
2. **One accent means MIA.** Electric cyan `--accent` #35d4ff is active, selected, her voice, progress and the
   primary action. Nothing else is cyan.
3. **Color carries meaning, sparingly.** Green `--ok` done or healthy. Amber `--attention` needs you, soon. Red
   `--bad` real errors, overdue and destructive actions only. Gold `--win` earned celebration only (a new best, a
   level, a milestone). Rarity colors only on missions, achievements and unlockables.
4. **Values are white; color sits beside them.** A number is `--text` with a colored index bar or label next to it.
   Money is the exception: in is green, out is red.
5. **Depth from layers, not borders.** Near-black field, then graphite panel layers. Lines are fine and faint. A cyan
   edge means active or hovered.
6. **Not everything glows.** Glow is for the orb, the primary button, the current nav item and meters in progress.
   Cards and text never glow.
7. **No business logic in the front end** (DEC-0013). No totals, dates, "is it overdue", permissions or money math in
   `web/`. If a screen needs a number, the engine assembles it (`core/web_surfaces.py`, Life State). Pages talk to
   the engine only through `web/mia.js`.
8. **Every change is Propose → Approve → Execute → Record → Undo** (`core/actions.py`). A screen never changes
   anything without a visible confirmation, and offers Undo after. New action kinds go in the engine, never in `web/`.
9. **Honest numbers.** Every figure in an answer says what it is: Fact, Calculation, Estimate or Missing. A workout
   count says how it was made (Said, MIA Pace, Told, Tapped) and is **never shown as verified**. Never invent a
   number; if it isn't known, say Missing.
10. **Never guilt** (DEC-0014). No "you failed", "missed", "behind", streak-loss threats. A short set is still a set;
    a quiet week is a quiet week; rest counts.
11. **The layout is Zac's** (DEC-0045). The desktop sidebar of apps, the phone's Home and Apps bar, Home with
    Today's Focus and Upcoming stay. Change navigation only when Zac asks, and ask first.
12. **Offline.** System fonts only, no web fonts, no CDNs, images shipped in the repo.
13. **Each person's data is theirs; children see less** (no money, no property). Design the empty state a child
    sees instead of hiding the gap.
14. **No real personal data** in code, docs, examples or mockups (DEC-0002). Use placeholders (the canvas uses
    "Robin").

## 3. Color tokens

| Token | Value | Use |
|---|---|---|
| `--bg` | #05070a | The field (page background) |
| `--rgb-panel` / `-2` / `-3` | 12,16,22 · 17,23,31 · 24,31,41 | Section, raised, card and focus layers |
| `--line` / `--line-strong` | line rgb 150,182,212 at 0.12 / 0.24 | Hairlines, quiet button outlines |
| `--text` | #e6eef6 | Values and body |
| `--text-dim` | #9fb0c1 | Secondary text |
| `--text-faint` | #8193a6 | Labels (still 5.3:1 or better on panels) |
| `--accent` (+ `-soft`, `-deep`, `-glow`) | #35d4ff | MIA, active, selected, progress, primary |
| `--ok` | #4fc48c | Done, healthy |
| `--attention` (= `--soon`) | #f2b33d | Needs you, soon |
| `--bad` | #ef5350 | Real errors, overdue, destructive |
| `--win` | #f6c453 | Earned celebration only |
| `--rarity-*` | | Missions, achievements, unlockables only |

**High contrast** is `[data-contrast="high"]`: black, white and full-strength cyan; glows off. Every screen must still
read in it. **Dark only** is proposed (DEC-0113); high contrast is the accessible alternative.

**Contrast floor:** body text 4.5:1, large text and UI 3:1. The measured values are in `STARK_INTERFACE.md`; a
proposed test will compute them from the tokens so a change can't break them.

## 4. Type

- Faces: `--font` (system sans) and `--font-mono` (system mono). Tabular figures everywhere.
- Scale (each times `--scale`, the person's text size): `--text-xs` 12 · `-sm` 13.5 · `-md` 16 · `-lg` 20 · `-xl` 28
  · `-2xl` 38 px. Proposed: `--text-3xl` 56 px mono, the display size for flagship moments (a rep count, a timer).
- Labels: mono, 11 px, spaced capitals (`--label-size`, `--label-track` 0.12em). Use them for status-strip labels,
  tile labels, chart keys, meal slots, form labels.
- Readouts: big numbers in mono. Section titles carry a short cyan index mark before them.
- Words on screen: Title Case for buttons, tabs and headers; sentence case for body copy (MIA_VOICE rule 14).

## 5. Shape, space and touch

- Corners: `--radius` 6 px for panels, `--radius-sm` 4 px for controls and tags, circles only for the orb, avatars
  and round tick buttons.
- Gap: `--gap` 16 px (12 on phones). Proposed: a 4 px scale `--space-1` 4 … `--space-8` 48.
- Touch targets: `--touch` 44 px minimum everywhere. **56 px or more in hands-busy modes** (active workout, cooking);
  the canvas uses 56–64 px on phone and 80 px on the cook-mode tablet for the main action.

## 6. Surfaces (proposed names, built material)

Four depths, one meaning each:

| Surface | What it is | Look |
|---|---|---|
| Base | The page | `--bg` |
| Section | A group of related things | `.glass` today (panel gradient, 1 px line, top highlight) |
| Card | One thing | `--rgb-panel-3`, faint line |
| Focus | The one thing that matters now | Brighter, larger, cyan edge, deep shadow; the rest dims slightly |

Use Focus once per screen at most. Today every section is `.glass money-section`; the proposal renames it `section`
with the old name kept as an alias.

## 7. Controls

| Role | Class today | Look |
|---|---|---|
| Primary | `.btn-green` | Solid cyan, dark text, soft glow |
| Secondary | `.btn-amber` | Cyan outline |
| Quiet | `.btn-ghost` | Fine line |
| Danger | danger | Red text and line |
| Big action (proposed) | — | Full width, 56 px+, for hands-busy modes |

One primary per view. Tabs are a rail with the current one lit from below. Focus is a 2 px cyan ring on every
focusable thing, always visible, not only on hover. Pressing nudges 1 px. Use real `<button>`, `<a href>` and
`<input>` with a `<label>`; icon-only buttons get an `aria-label`.

Icons come from `web/icons.js`: one 24-unit line set, 1.6 stroke, round joins, `currentColor`. A mission's or
skill's own emoji is the person's content and stays; emoji are never interface icons.

## 8. The orb: her presence

One component (proposed `web/orb.js`) with one set of states, used at three sizes: hero on Home, header in apps,
corner in modes. States come from one place (the shell knows when she listens and speaks), so every surface agrees.

| State | Look | When |
|---|---|---|
| Idle | Slow breath | Nothing happening |
| Listening | Rings drawn in | Mic open, following a count |
| Thinking | An orbit turns | A turn is running |
| Speaking | Core pulses with her voice | She's talking |
| Needs you | Amber | One thing waits on the person |
| Celebrate | Gold, once | Something earned |
| Offline | Dim and still | Engine unreachable |

Under the orb, the caption shows what she heard, then what she says. On the glasses the caption is the main surface.

## 9. Shared patterns

- **Finding (MIA noticed):** amber edge, "MIA Noticed" label plus its kind (Deadline, Fact, Suggestion), one-line
  headline, one line of why, a "Used:" row naming the apps she looked at, one next step as the primary button and
  Not Now. Unprompted findings only come through the communication gate (`core/communication_gate.py`, 5 a day).
- **Answer card:** the answer first in one sentence, the reasoning in one or two, the figures each tagged Fact /
  Calculation / Estimate / Missing, then "What I used: …". Follow-up suggestions as quiet chips under it.
- **Proposal → Done → Undone:** cyan-edged "Proposed" card with the action's own summary and Approve / Not Now; on
  approve a green "Done" line with Undo for a few seconds; after undo "Undone. <App> is back how it was."
- **Today's Focus row:** round tick button, what, why (where it comes from), a kind label on the right. The tick
  runs the item's own `action` (each due item carries one). Never build an action in the front end.
- **Status strip:** neutral white values with a 2 px colored index bar (green ok, amber needs you, cyan next up).
- **Meters:** 6 px, cyan while in progress, gold only when a target is hit.
- **Header plate:** graphite with a fine cyan 16 px grid, the app's icon large and faint as a schematic in a dashed
  ring, the app's badge, its name and a mono tagline. No photos (H-0036).
- **Modes (proposed):** a flagship app gets a home view plus full-screen modes instead of six or seven tabs.
  Workout: Today → Active → Rest → Done, with Progress and Plan. Kitchen: Today → Cook, with Week, Recipes, Pantry.

## 10. States every screen designs

Empty, loading, error and offline, plus active/completed where they apply, child account, and demo (`/web/?demo`).

- Empty says what's missing and the one way to start ("No recipes yet. Add one, or tell MIA a dish you like.").
- Loading is a skeleton in the shape of what's coming, never a blank moment. Busy regions get `aria-busy`.
- Error says what happened and that nothing changed, with Try Again. Red edge, plain words.
- Offline shows the dimmed orb and says where work is happening ("Working from this phone. Changes sync when the PC
  is back.").
- A section whose status is PLANNED says "coming"; it's never faked (DEC-0007).

## 11. Words on screen

Her voice guide (`MIA_VOICE.md`) applies to every label and empty state. In short: what matters first, then stop;
plain words, short sentences, second person; no "Certainly!" or "Is there anything else"; never guilt; celebrate
real things only; she suggests and the person decides; never guess at feelings. Lengths: glasses one or two spoken
sentences (about 20 words), phone a short paragraph, PC the full answer.

## 12. Devices

| Surface | Size | Composition |
|---|---|---|
| PC (`modules/web_home`) | 1280+ wide | Sidebar (brand, Home, Apps, Pinned, Life Areas collapsed, level and XP) · content · MIA's panel on the right (orb, conversation, suggestion chips, input and hold-to-talk) |
| Phone (Android web view) | 360–430 wide (designed at 390×844) | One column; bottom bar Home and Apps; MIA's orb as a floating Talk button above it; modes full screen; no fake status bar |
| Tablet / counter (cook mode) | landscape, designed at 1180×820 | One step in very large type, timers in a side column, Back and Next as 80 px targets |
| Glasses (`web/glasses.html`) | 600×600 additive | Black is see-through and nothing is solid: outlines and light only. The orb, a caption, one panel at a time. Text 22 px or larger. Never a phone page shrunk. Don't claim glasses features MIA doesn't have (DEC-0016) |

Text scales with `--scale`; layouts must survive the largest text size (titles wrap between words; money never
wraps, it shrinks).

## 13. The core screens (Zac's canvas, 2026-11-07)

These are the screens needed for MIA to be usable day to day, drawn on the canvas in the built look. Each lists its
data and the actions its buttons propose. They're **concepts** under DEC-0113: build them only after Zac approves.

**PC page**
- **Home · Desktop:** greeting and date; status strip (Tracked, Needs You, Next Up); a pinned finding; Today's
  Focus with why and kind; Upcoming; a recent win in gold; MIA's panel with "What I used". Data: `MIA.dashboard()`,
  `MIA.shell()`, `core/presence.py`. Actions: each item's own `action` (e.g. `bill.pay`, `maintenance.done`).
- **Kitchen · Cook Mode:** step n of m with a segmented progress rail, the step in 46 px type, "This Step Uses"
  chips, named timers that keep running across steps, MIA listening with the phrases she understands, Back and Next
  Step. Engine to build first: `core/cooking_session.py` and `cooking.*` actions (Kitchen brief §13).
- **Foundation:** the orb's seven states, color and atmosphere swatches, the type scale, the four surfaces, the
  control roles, the proposal → done → undone pattern, meters, answer-figure tags, and the four states.

**Phone page**
- **Home · Phone:** greeting, the finding, Today's Focus (three items), Upcoming, the orb Talk button, the Home /
  Apps bar.
- **Talk:** the question; the answer card with tagged figures and "What I used"; a proposal with Approve / Not Now,
  then Done with Undo, then Undone. Data: `MIA.talk()`, `MIA.propose()`, `MIA.approve()`, `MIA.undo()`.
- **Apps:** search, Favorites as tiles (these are also the glasses' cards), each life area as a list with a live
  one-line status from the engine. Data: `MIA.apps()`. Action: `app.favorite`, `app.visibility`.
- **Workout · Today:** header plate, Today / Progress / Plan, the week's dots (done green, rest open, today lit,
  planned outlined), the day's exercises with prescriptions, one big Start Workout, "Or say 'MIA, start my
  workout'", today's missions with meters, the last session. Data: `MIA.workout()`, `MIA.fitness()`. Action:
  `training.start`.
- **Workout · Active Set:** the Focus surface: exercise, set n of m as a rail, the count in display type with how
  it was counted, her caption, +1 Rep, Skip, Set Done (64 px), the next set and what she understands. Actions:
  `training.set`, `training.skip`, `training.pause`, `training.correct`.
- **Workout · Rest:** a draining ring with the time left, what was logged and how it was counted, Up Next, +30 s,
  Pause, Skip Rest, "A tone plays at zero." Action: `training.skip_rest`. Reduced motion keeps the number.
- **Workout · Done:** planned → done per exercise with how each was counted, a gold New Best card (only when one is
  real), XP and skill, the mission moved, no guilt for a short set. Action: `training.finish`.
- **Kitchen · Today:** tonight's dinner with what's missing and Start Cooking; today's meals with Ate It; protein
  and calories against the plan; Use Soon in amber with one suggestion. Data: `MIA.kitchen()`. Actions: `meal.log`,
  `grocery.add`, `meal.cook`.

**Phone page, every other app (added the same day, one main screen each, same plate / tabs / sections pattern)**
- Life, progress and the game: Missions, Skills, Character, Reward Shop, Party, Sunday Check-in, The Chronicle.
- Life, days, people and learning: Calendar, Journal, Kept, People & Pets, Classroom, a learning path (Guitar),
  Memory Vault, Operating Journal, Play, Observations.
- Money and business: Money, The Dungeon, Freedom, Compliance, Insurance, Real Estate, Workshop, Orders & Quotes,
  Inbox.
- Home, homestead and equipment: Garage, one asset, Greenhouse, Chickens, Household, Security, Power.
- Outdoors and field: Expeditions, Maps, Navigation, Memories, World Map.
- Knowledge and tools: Knowledge, Music, Files, Passwords, Good News Radio, Look, Toolbox, The Lab, Field Kit.
- System and account: Sign In, Profile, Settings, Fix-It Log, Diagnostics. Plus Kitchen's one-recipe page.
- Each follows §9: the header plate, tabs only where the app has them today, a status strip or Focus card for what
  needs you, rows with their action as a quiet button, honest labels (Missing, Estimate, how a count was made),
  and a line saying what's private or never done (a password shown for seconds; a port scan only when started).
  Power, Toolbox, The Lab and Field Kit have no web page yet: their screens are the proposed web versions of the
  desktop apps (`docs/WEB_PARITY.md`).

**Glasses page**
- **Orb and Feed:** the orb, "MIA · Ready", one spoken-length line, a feed card ("+50 XP · Mission complete"), dots
  for the favorites' cards. Data: `core/glasses.py`.
- **Active Training:** exercise, set and weight, the count huge, how it's counted, what's next. One panel only.

## 14. Per-app atmosphere (proposed, DEC-0113 §2)

Each app may add one secondary color for **its own data and its header motif only**. Cyan still means MIA, active
and selected everywhere; meaning colors keep their meanings; atmosphere never colors a button, a state or the orb.
The canvas shows them as a Tweaks swatch (switch to cyan to see the approved DEC-0023 look):

| Token | Proposed value | Watch out for |
|---|---|---|
| `--mod-workout` | warm orange #ff8a3d | Must stay clearly apart from `--bad` red |
| `--mod-kitchen` | amber-cream #e9d4a8 | Must stay paler than `--attention` amber |
| `--mod-workshop` | steel blue-gray #8fa7bf | Must not read as disabled text |
| `--mod-homestead` | leaf green | Too close to `--ok` green as drafted: Muse to resolve before approval |

Values are Muse's to set; these are the canvas's placeholders.

## 15. Designing a new screen yourself

When you design or change a screen (or propose one for Zac):

1. **Start from what exists.** Read the app's page script, its `MIA.*` read and its action kinds. Every function on
   today's screen must have a home in the new one.
2. **Write the spec from the template** (`docs/design/applications/TEMPLATE.md`, 18 parts): purpose, existing
   functionality, navigation, screens with data, layout, components, interactions with action kinds and undo, all
   states, voice, memory, missions, dependencies, desktop, phone, glasses, accessibility, acceptance criteria.
   Status moves brief → spec → built → accepted; only Zac accepts.
3. **Reuse before inventing.** Use the shared components in §6–9. A new component is proposed into the design system
   first, with a name that says what it is.
4. **Put the logic in core.** If the screen needs a number, a list or a decision, assemble it in the engine and
   expose it through `web/mia.js`.
5. **Check it against this list** before showing anyone:
   - Only tokens; no literal colors.
   - One primary action; cyan used only for MIA, active, selected, progress.
   - Meaning colors used for their meaning only; gold only for something earned.
   - Every number tagged honestly; nothing unverified shown as verified.
   - Empty, loading, error and offline drawn; child account considered.
   - 44 px targets (56 px+ hands-busy); visible focus ring; real buttons and labels; 4.5:1 text.
   - Works at 390 px wide and at the largest text size; glasses get their own composition.
   - Copy in her voice: Title Case labels, no guilt, what matters first.
   - Reduced motion: nothing moves without cause, and nothing moves with `prefers-reduced-motion`.
   - No real names, places or numbers from anyone's life.
6. **Concept before code.** Until DEC-0113 is approved, anything new in look stays a concept (the canvas or
   `docs/design/visual_library/`); `web/` follows the built look.
7. **Record it.** A decision goes to `docs/DECISIONS.md` as proposed; what you built and why goes in a knowledge
   entry (`work/knowledge/`); the design doc changes in the same change as the token or component (DEC-0110).

## 16. Open decisions (Zac's)

From DEC-0113, still proposed: per-app atmosphere; dark only with high contrast; the image pipeline (repository
library and ChatGPT by hand first); concept round one before any visual change is built. From the canvas: whether
cook mode lives on the PC/tablet page or the phone page; the homestead atmosphere color.

## 17. Where to look

| For | File |
|---|---|
| The values | `web/tokens.css` |
| The built look, piece by piece | `docs/design/STARK_INTERFACE.md` |
| The 15-area system, built vs proposed | `docs/design/MIA_DESIGN_SYSTEM.md` |
| Identity and directions | `docs/design/MIA_VISUAL_IDENTITY.md` |
| How she sounds | `docs/design/MIA_VOICE.md`, `core/personality.py` |
| The front end's contract | `web/README.md`, `web/mia.js` |
| App specs | `docs/design/applications/` (TEMPLATE, workout, kitchen) |
| What exists, and its maturity | `docs/EXPERIENCE_MATURITY_AUDIT.md` |
| Concept images | `docs/design/visual_library/MANIFEST.md` |
