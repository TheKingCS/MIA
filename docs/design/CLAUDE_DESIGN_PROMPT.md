# Prompt for Claude Design: the vision of using MIA

*Written by Claude (engine), 2026-10-30, at Zac's request, from the page and
app usage audit (`docs/UI_AUDIT.md`) and MIA's approved decisions. Paste
everything below the line into Claude Design. Placeholder names only; no
one's real data.*

---

Design the vision of what it's like to **use MIA** day to day: a set of
connected screens and moments across a desktop, a phone and smart
glasses, showing a person living their day with her. This is a vision
piece for the team to build toward, grounded in a product that already
exists, so it must respect the constraints below.

## What MIA is

MIA (Multifunctional Intelligent Assistant) is a personal AI companion
that runs on the person's own computer and phone, offline-first, with a
local AI model. She keeps a person's whole life in one place across about
40 apps: money and debts, a home and land (vehicles, upkeep, a
greenhouse, chickens), the kitchen (recipes, pantry, meal plan), fitness
(a training plan, workouts, skill practice like handstands), missions
and goals, a workshop and small business (things they build and sell at
a market), rentals, insurance, compliance deadlines, a journal, people
and pets, trips and maps. A game layer runs through it all (a LitRPG):
XP, levels, skills, six character stats, missions and questlines,
bosses, rewards they choose, and their paid job shown as "the Dungeon"
(shifts are runs, pay is loot, overtime is a boss). She speaks with a
warm, natural voice.

**The heart of the vision:** the person shouldn't have to dig through
apps. They talk to MIA, and she works the apps for them: she answers
detailed questions by looking across several apps at once ("Can I
afford the chicken coop this month?" uses the budget, the bills before
payday, this week's pay and the build's cost), she notices things by
putting apps together ("your electric bill is due the 3rd, but pay
lands the 5th"), she remembers what the conversation is about, and she
proposes changes the person approves. The apps are where everything
lives and can be checked; MIA is how they're used.

## Who uses it

One person first (someone with a full-time factory job, a homestead, a
fitness plan, and a goal of earning enough from his homestead and
business to leave the job), then their household; children get a
simpler, safer version. Call the person **Robin** and use placeholder
data throughout.

## The devices

1. **Desktop (the home computer):** a left sidebar of the person's apps
   in five groups (Life, goals & self · Money & business · Home,
   homestead & equipment · Outdoors & field · Knowledge, tools &
   system), the current app in the middle, and MIA's panel on the right
   (her orb, the conversation, a talk button). Wide screens.
2. **Phone:** the same apps in a mobile layout: Home, an Apps bar, and
   Talk always one tap away. Used most of all, often by voice.
3. **Meta Ray-Ban Display glasses:** a 600 × 600 additive display (light
   on transparent: black is see-through, nothing is solid), boots to
   MIA's orb; swipe through app cards, select one for a short quick-action
   menu; a heads-up feed of small cards ("+50 XP · Mission complete");
   MIA heard and spoken through the glasses. Minimal, glanceable, never
   cluttered.

## Fixed constraints (approved decisions)

- **Layout stays (DEC-0045):** the sidebar of apps, the phone's Home and
  Apps bar, Home with **Today's Focus** and **Upcoming**. Don't replace
  the navigation with new "places"; show the intelligence through MIA
  working inside this frame.
- **The look (DEC-0023, "Stark engineering interface"):** near-black
  graphite layers for depth (not borders), **one electric-cyan accent**
  (active, selected, MIA's voice, progress); muted green = done, amber =
  needs you soon, red = real errors and destructive actions only, gold =
  earned celebration only; values in white with color beside them;
  precise shapes (6 px panels, 4 px controls); circles only for the orb,
  avatars and round tick buttons; glow only on MIA's orb, the primary
  button, the current nav item and meters in progress; line icons.
- **Every change is Propose → Approve → Execute → Record → Undo:** MIA
  suggests, the person approves (a tap, a word, or a second gesture on
  the glasses), and anything can be undone ("undo that").
- **Honest answers:** when MIA answers from records, she can show what
  she used and mark what's a fact, a calculation, an estimate, or
  missing; she never invents a number.
- **Never guilt (DEC-0014):** no "you failed", no streak-loss threats; a
  missed day is just a quiet day, rest counts, a short set is still a set.
- **Her voice:** plain words, short sentences, facts first, second
  person, encouraging without cheerleading, never narrating feelings.
- **Accessible:** readable at arm's length, large touch targets, works
  in high contrast and with bigger text.

## What we learned from usage (why this matters)

Today the person opens very few apps (Settings and Missions most), most
apps hold little, and most use is talking to MIA on the phone. The
fitness plan's daily missions mostly lapse unseen. So the design should
make MIA the front door, bring the right app forward at the right
moment, and make a too-big plan easy to right-size without guilt.

## What to design

A storyboard of **one day with MIA**, then the key screens it passes
through. For each, show desktop, phone and/or glasses where they apply.

1. **Morning, phone:** Home with Today's Focus and Upcoming, MIA's
   presence, one finding she noticed across apps, and the one next step.
   Robin asks by voice "What should I focus on today?" and gets one short
   answer with a "What I used" row (the apps she looked at).
2. **A detailed question, answered across apps:** "Can I afford the
   chicken coop this month?" Show the answer card: the answer first,
   the reasoning in a line or two, figures marked as calculation or
   estimate, what's missing ("no pay rate set"), one proposed next step
   with Approve, and the apps she checked.
3. **A follow-up that holds the thread:** "What if I put $200 more a
   month toward the card?" answered in the same conversation, plus
   "yes, add it to my calendar" doing exactly that.
4. **Work, the Dungeon:** a glance on the glasses at the shift (a "run"),
   loot so far, overtime as a boss; MIA's heads-up card when a run is
   cleared.
5. **Evening workout, phone and glasses, hands-free:** "MIA, start my
   workout routine." The Active Training screen (exercise, set 2 / 3,
   reps 8 / 15, rest countdown, next up, session time) and its glasses
   card; MIA counting the pace aloud, the rest starting by itself, the
   set confirmed by voice; the finish screen with XP and the mission
   ticking over. Minimal on the glasses.
6. **An app screen with MIA's layer on it:** Money (or Garage) as it is,
   with MIA's touches: a finding pinned at the top, "Ask about this"
   examples, a proposal waiting for approval.
7. **What MIA noticed, unprompted:** a single, calm notification for one
   of the few things she may raise on her own (a bill due before payday
   with money short; upkeep due before a trip; a deadline in a packed
   week; a cheaper insurance quote near renewal), and where it leads.
8. **Approve and undo:** the shared pattern on desktop, phone (a tap)
   and glasses (a second select), and "undo that" restoring it.
9. **A plan that's too big, without guilt:** the fitness missions that
   keep lapsing, and MIA offering to right-size the plan.
10. **The Apps page and favorites:** all apps in their groups, the
    person's favorites pinned (these are also the glasses' cards).

## Deliverables

- The day as a storyboard (10 moments, one line each, the device shown).
- High-fidelity screens for moments 1, 2, 5 (phone and glasses), 6 and
  8; the others as lower-fidelity frames.
- The **answer card**, **proposal / approve / undo** and **finding**
  components as reusable pieces, with their states.
- A short note on anything in these constraints you'd challenge, and
  why (the layout itself is the owner's call, so as a question, not a
  redesign).
