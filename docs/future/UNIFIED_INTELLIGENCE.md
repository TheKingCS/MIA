# One intelligence: what a thing touches

*Zac, 2026-11-24: "I think the next major evolution should be connecting all these capabilities into a unified
intelligence layer. For example: you tell MIA you're planning to build a greenhouse. MIA understands that this
involves your available budget, your existing building materials, your garden and growing plans, your water and
electrical systems, your available time, your long-term agricultural research goals. It doesn't just answer
individual questions. It understands how the project affects the rest of your life. That's when MIA starts feeling
less like an application and more like the second consciousness. And this same principle should apply all over
MIA."*

This is the plan for that, built on what MIA already has. Nothing in it is a new app: it's how the apps she has
are read together.

## What already connects things

- **Question plans** (`core/question_plans.py`, DEC-0052): a question is answered from a *sheet* gathered in code
  from several apps' records, each line marked fact, calculation, estimate or missing. The model only words it.
  The cross-domain ones ("can I afford it", "where do my time and money go", "what do I have to work with") already
  read three to seven apps each.
- **Links** (`core/links.py`): how records relate ("the land loan funds the rental", "this mission is evidence for
  that skill"), stated by him or derived from fields the stores already have.
- **Life events** (`core/life_events.py`): what changed, when, by whom.
- **The why graph** (`core/why_graph.py`): his reasons, chained, with the facts behind each one.
- **The life state** (`assemble_life_state_v2`): the whole picture in one shape, for the web and the phone.

What was missing is the step from "a question about one thing" to "everything this thing touches".

## Step 1, built 2026-11-24: the project picture

`core/project_ripple.py`, reached as the question plan "project picture" and the tool `project_picture`.

"I'm planning to build a greenhouse" is read as a project of a kind (`KINDS`). Each kind says which areas of his
life it touches: a greenhouse touches money, materials, growing, water, power, time, goals and research; a coop
touches money, materials, the flock, water, time and goals; a shed touches money, materials, time and goals. Each
area is then gathered from what already answers for it:

| Area | Where it comes from |
|---|---|
| The build | the Library's plan for it at its size (or the size of his draft), what's still to buy against the workshop's stock, and its known cost |
| Already started | a project by that name, with its budget against what's spent; a Planner draft |
| Money | this month in and out; the freedom date with the known cost and without |
| Materials | what's on hand for it already |
| Growing | his confirmed garden plans' year; what's due to plant |
| Water | the rain he's logged this week; whether to water |
| Power | the power system |
| The flock | the hens, eggs and feed |
| Time | his open projects; this week's calendar; the build's hours (missing until he says) |
| Goals | his reasons |
| Research | the grow lab's series; learning paths |

Each area also carries one line of general guidance, marked as guidance and never as his facts ("a greenhouse needs
water at it every day in summer"), so the model can say how the areas connect without inventing anything. A part
of MIA that isn't set up is said as missing. Nothing is planned, bought or changed: the sheet ends with the offer to
draft the plan, which waits for his Confirm (`core/project_plans.py`).

## Built since (2026-11-24)

- **Step 5, the Planner page shows it**: each draft's "What It Touches" (`for_plan`, /api/planner/touches).
- **Step 2, in part**: what confirmed builds still need from the store is on the afford, priorities and projects
  sheets (`still_to_buy`), read from the plans themselves, so it needs no stored links.
- **Step 3, for confirmed builds**: a material a confirmed build had fully on hand that isn't any more is said once,
  through the daily check of what's unusual (`gone_short`, core/unusual.py). Other ripples wait on 0zl's links.
- **His stock against every plan**: "what can I build with what I have?" (`core/buildable.py`).

## The next steps

Each is the same principle applied one layer further. They're in order: each uses the one before.

1. **A confirmed plan remembers what it touches.** When he confirms a plan, MIA writes the links the picture found
   (the greenhouse USES these materials, DEPENDS_ON water at the site, SUPPORTS his growing goal) as derived links
   in `core/links.py`, from the plan itself, so they can't drift. *Question for Zac (WAITING_ON 0zl).*
2. **Other answers account for planned projects.** With those links, the money answer says "the greenhouse still
   needs about $X of materials", the garden's year shows the greenhouse's earlier starts, the materials list says
   "set aside for the greenhouse", and the week's plan counts the build's hours. Each is a line on an existing
   sheet, read from the links, never a copy.
3. **A change ripples.** When a record changes in a way that touches a planned project (the 2x4s it needed get used
   on something else, the rain gauge reads dry for weeks while the greenhouse counts on catchment, the budget month
   goes negative before the materials are bought), MIA says so once, through the communication gate, paced by what
   he opens (DEC-0171). Facts in code, never a guess.
4. **Every sheet has "also touches".** The same idea for things that aren't projects: a vehicle repair touches the
   budget, the calendar and the business's deliveries; a new debt touches the freedom date and the next dollar. Each
   question plan reads the links of the records it gathered and adds the one or two connected facts that matter.
5. **The Planner page shows it.** Each draft on the Planner page gets "What it touches", the same sheet, so the
   picture is there without asking (DEC-0125: every feature by voice and on screen).

## What stays true

- Facts are assembled in code; the model only words them. A connection the records don't show is said as guidance
  or as missing, never as a fact.
- Nothing MIA reads changes anything. The picture plans nothing; a link written from a plan is undoable; a ripple
  note is only a note.
- One owner per record (DEC-0153). The picture reads each app's records where they live and copies none.
