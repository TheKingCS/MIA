# MIA Intelligence Benchmark

*Zac's Master Question Bank, Draft 1 (2026-10-30), with Claude's first
assessment of where MIA stands on each question. The questions
themselves are in `tests/intelligence_bench.py` (by ID: A1 … G15), so the
tests, the routing audit and the live bench all use the same list. This
is the yardstick for DEC-0052 (`docs/REASONING_PLAN.md`).*

## 1. What every answer should do (Zac's standard)

For every question, MIA should:

- understand the intent, however it's phrased (typed, spoken, a
  follow-up);
- retrieve from the modules that hold the answer, and connect modules
  when the question needs it;
- explain the reasoning and the calculations;
- say what's a **confirmed fact**, a **calculation**, an **estimate**,
  an **assumption** and a **recommendation**;
- name what's missing rather than invent it;
- offer a useful next step;
- keep one natural personality.

**The answer protocol (section H):** answer the actual question first;
the important reasoning; what she already knows; uncertainty and what's
missing; facts, calculations, estimates and recommendations told apart;
other opportunities only when they're genuinely useful; a next step; a
natural voice, not a database report unless asked.

**By category:**

- **A, Personal operations:** prioritize, don't list everything; why it
  matters; deadlines told apart from suggestions; the most useful next
  action.
- **B, Money:** show the numbers and the math, compare alternatives,
  the consequences of a decision; bank transactions told apart from
  estimates and hand-entered amounts.
- **C, Business and homestead:** think like a business analyst
  (materials, labour, overhead, fees, margins, inventory, cash flow);
  compare investments by profit, startup cost, risk and time; never
  present a legal requirement or a tax deduction as settled fact.
- **D, Personal development:** only real progression records; three
  styles: **Guide** (help me understand what to do), **Game Master**
  (turn it into missions), **Witness** (listen and help me process it,
  without turning it into a task); never make anyone feel punished for
  struggling, resting or being human (DEC-0014).
- **E, Memory:** tell apart what was **told** to her, what's **in a
  journal**, what's **calculated from records** and what's **inferred
  from a pattern**; dates and decisions where possible; never an
  inference presented as a memory.
- **F, Research and learning:** know when a question needs outside
  research, use reliable sources, flag outdated information, keep
  researched facts apart from her own reasoning; big projects as steps
  she offers to guide.
- **G, Cross-domain:** find the domains involved, retrieve from each,
  connect them, calculate, give one recommendation; name **the biggest
  bottleneck**, not a pile of observations.

**The ultimate objective (section J):** about almost anything in the
person's life, MIA can say **what is happening** (awareness), **what it
means** (understanding) and **what we should do about it** (reasoning
and assistance), on the desktop, the phone, by voice and on the glasses.
Not an AI that knows 200 tools: a companion who understands the person's
life well enough to know which tools, information and reasoning help.

**Development rules (section I):** for every question, record what it
needs, the modules and tools, the expected answer and reasoning, what
happens when data is missing, its status, its gaps, its automated test
and its live-model result; test several phrasings (voice, follow-ups,
questions that lean on the conversation). **Never add a tool just
because a question failed:** first decide whether the gap is data,
retrieval, cross-module integration, calculation, reasoning, memory,
external research, conversational understanding or action.

## 2. Where MIA stands today (2026-10-30)

`python -m tools.bench_audit` runs every question through MIA's real
routing (no model), the same decision a turn makes:

| Category | Questions | Answered by code | Tools offered | No tools at all |
|---|---|---|---|---|
| A Personal operations | 12 | 1 | 3 | 8 |
| B Money | 20 | 1 | 6 | 13 |
| C Business and homestead | 20 | 1 | 9 | 10 |
| D Personal development | 15 | 0 | 2 | 13 |
| E Memory | 15 | 1 | 3 | 11 |
| F Research and learning | 15 | 0 | 6 | 9 |
| G Cross-domain | 15 | 0 | 2 | 13 |
| **All** | **112** | **4** | **31** | **77** |

**What this says:**

1. **The biggest gap is retrieval, not data.** 77 of 112 questions reach
   the model with no tools at all, so it answers from the few lines of
   context every turn carries. Yet most of what they need exists already:
   `get_today`, `get_weekly_checkin`, `get_life_state`,
   `get_debt_payoff_plan`, `get_property_summary`, `get_dungeon_loot`,
   `get_freedom_progress`, `get_financial_checkin`, `get_ledger_summary`,
   `get_build_costs`, `get_learning_progress`, `show_my_why`,
   `get_journal_themes`, `get_life_events`. They're never offered,
   because tools are chosen by the words in the question, and these
   questions are phrased as people talk ("What have I been
   neglecting?"), not as tool names.
2. **Some tools offered are the wrong ones.** D8 ("progress *toward* the
   person I want to become") is offered the debt tools; E7 ("what do you
   know about my current priorities") the maintenance tools; G4 ("what
   have you noticed about me lately") 18 unrelated tools. A loose match
   is worse than none: the model is pushed toward the wrong records.
3. **Even a right tool gives a one-app answer.** A turn is one round,
   and results are said as they are (`docs/REASONING_PLAN.md` section 1).
   B10 ("the most effective use of my next $1,000") needs debts, the
   emergency fund, the freedom fund and the business together.
4. **Questions about "this"** (E1, E6, F1, F2, F7…) need to know what
   the conversation is about; today that's the model's guess from the
   history.
5. **Research (F) has no tool.** MIA has offline reference packs and
   textbooks, and no way to look things up on the internet. Questions
   about current laws, prices or products (F4, F5, F6) can't be answered
   reliably today, and she must say so.

## 3. Question by question

**Gap** uses Zac's list: Data, Retrieval, Integration, Calculation,
Reasoning, Memory, Research, Conversation, Action. **Fix** names the
DEC-0052 piece that closes it:

- **QP: name**: a question plan (section 4 below), lookups run in code
  and combined;
- **LOOP**: the tool loop, results back to the model;
- **FIND**: findings across apps;
- **STATE**: conversation state (what "this" is, what's open);
- **PROV**: memory provenance (told / journal / calculated / inferred,
  with dates);
- **RES**: outside research (a decision of its own, section 5);
- **DATA**: something MIA doesn't record yet;
- **OWN**: one owner per fact first.

### A. Personal operations

| ID | Needs | Gap | Fix |
|---|---|---|---|
| A1 | Presence, the Loop today, calendar, deadlines, goals | Retrieval, Integration | QP: today |
| A2 | Compliance deadlines, bills, upkeep, calendar | Integration (only Compliance today) | QP: today |
| A3 | missions/goals without progress, overdue upkeep, Loop rhythms missed | Integration, Reasoning | FIND + QP: neglected |
| A4 | life events, workouts, shifts, missions, sales | Integration | QP: week review |
| A5 | tomorrow's calendar and Loop, alarms, due-tonight items | Retrieval | QP: tonight |
| A6 | open tasks and objectives, proposals not approved, things said ("I'll…") | Data (said commitments aren't recorded), Retrieval | QP: open loops + DATA |
| A7 | life events this week vs last, the weekly check-in | Integration, Reasoning | QP: week review |
| A8 | due items nobody's looked at, birthdays, renewals | Integration | FIND + QP: today |
| A9 | everything due, ranked by importance and urgency (goal weight + deadline) | Calculation, Reasoning | QP: today |
| A10 | the next 2 to 4 weeks: deadlines, renewals, trips, events | Integration | QP: coming up |
| A11 | where the hours go: shifts, workouts, missions, sessions | Data (no time use outside shifts and workouts) | DATA, then QP |
| A12 | the primary goal and its why, the steps that move it, today's free time | Integration, Reasoning | QP: today |

### B. Money

| ID | Needs | Gap | Fix |
|---|---|---|---|
| B1 | income and spending this month (bank + manual) | Retrieval | QP: money month |
| B2 | spending by category | Retrieval | QP: money month |
| B3 | discretionary vs needed categories, subscriptions | Reasoning (what's "unnecessary" is the person's call: show, don't judge) | QP: money month |
| B4 | debts, rates, the payoff plan | (offered; one round) | QP: debts |
| B5 | the payoff plan with +$200: months and interest saved | Calculation (code, not the model) | QP: debts |
| B6 | rental income minus property costs | Retrieval | QP: rentals |
| B7 | rentals' income, costs, equity, upkeep | Integration, Calculation | QP: rentals |
| B8 | monthly needs vs income other than the job | OWN (pay), Integration | QP: freedom |
| B9 | the freedom fund and its pace | (offered) | QP: freedom |
| B10 | debts, emergency fund, freedom fund, business returns | Integration, Reasoning | QP: next dollar |
| B11 | income minus spending, months compared | Calculation | QP: money month |
| B12 | recurring bills and subscriptions, ranked | (offered, many tools) | QP: money month |
| B13 | interest across debts | (answered by code: list) | QP: debts (the total) |
| B14 | each debt's payoff date | (offered) | QP: debts |
| B15 | the payoff plan at a higher payment | Calculation | QP: debts |
| B16 | months of needs as a target, today's savings | Calculation, assumption stated | QP: next dollar |
| B17 | business cash, its expenses, the person's needs | Integration | QP: business month |
| B18 | a projection at today's pace, labelled an estimate | Calculation, Reasoning | QP: freedom (projection) |
| B19 | each asset's return: rentals, business, goods, investments | Data (investment returns depend on the bank sync), Integration | LOOP |
| B20 | the freedom plan's levers ranked | OWN, Reasoning | QP: freedom + FIND |

### C. Business and homestead

| ID | Needs | Gap | Fix |
|---|---|---|---|
| C1 | products' price minus cost | (offered) | QP: products |
| C2 | the recipe's materials at their cost, plus labour and overhead | Calculation | QP: product cost |
| C3 | cost + time + margin target + what similar sold for | Calculation, Reasoning | QP: product cost (a price range, assumptions named) |
| C4 | margins by product | (offered) | QP: products |
| C5 | the next market day, what's planned to sell, materials short | Integration | QP: market prep |
| C6 | goods and materials on hand at cost | (offered, Inventory only) | QP: products |
| C7 | the ledger this month | Retrieval | QP: business month |
| C8 | business-use purchases; a hint, never a ruling | Reasoning (labelled "ask a tax professional") | QP: business month |
| C9 | Compliance items not verified | (answered by code) | — (check wording) |
| C10 | return per dollar and time for each option | Reasoning, Data (options must be named) | LOOP + STATE |
| C11 | margin × demand (sales history) × time | Reasoning | QP: products + LOOP |
| C12 | tools, power, space, consumables a month | Data (workshop overhead isn't recorded as one figure) | DATA, then QP |
| C13 | business profit, cash needs, the person's needs | Integration, Reasoning | QP: business month |
| C14 | monthly needs ÷ profit per unit | Calculation | QP: products |
| C15 | job income ÷ profit per unit or per hour | OWN (pay), Calculation | QP: freedom |
| C16 | profit per hour by product | Calculation (time per product needed) | QP: products |
| C17 | material use rate, price breaks | Data (price breaks), Calculation | LOOP |
| C18 | where the hours go per product, equipment costs | Data, Reasoning | LOOP |
| C19 | sales history, stock left over, made-to-order quotes | Integration, Reasoning | LOOP |
| C20 | skills, equipment, land, sales, demand | Reasoning across apps | FIND + LOOP |

### D. Personal development

| ID | Needs | Gap | Fix |
|---|---|---|---|
| D1 | the primary goal, its why, active missions | Retrieval (context has it; no tool) | QP: progress |
| D2 | skills with recent XP | Retrieval | QP: progress |
| D3 | skills, personal bests, missions this month vs last | Integration, Calculation | QP: progress |
| D4 | stuck objectives, missed rhythms, journal themes (if shared) | Reasoning, privacy | FIND + LOOP |
| D5 | the goal's next step that fits today | Reasoning | QP: today |
| D6 | the situation, said by the person | Conversation (Game Master style) | STATE |
| D7 | the active questline's next step | Retrieval | QP: progress |
| D8 | the person's stated "who I want to be", progress toward it | Data (wrong tools offered today), Reasoning | QP: progress |
| D9 | the goal's next step, what's ready | Reasoning | QP: progress |
| D10 | levels, bosses, bests, missions finished | (offered life events only) | QP: week review |
| D11 | skills tied to the primary goal, least developed | Reasoning | QP: progress |
| D12 | rhythms kept and what followed them | Reasoning (inferred: labelled as a pattern) | FIND + PROV |
| D13 | rhythms missed and what happened instead | Reasoning (never blame) | FIND + PROV |
| D14 | the objective, broken into missions (proposed) | Action (proposals), Reasoning | LOOP + STATE |
| D15 | the Loop, the plan, recovery | Reasoning | LOOP |

The three styles (Guide, Game Master, Witness) are the conversation
modes' job (`core/conversation_modes.py`), not a tool's: D6 and D13 are
tested in each.

### E. Memory

| ID | Needs | Gap | Fix |
|---|---|---|---|
| E1 | past conversations about "this project" | Memory, Conversation | STATE + PROV |
| E2 | the goal's why (the why chain), when it was said | Retrieval | PROV |
| E3 | promises to people | Data (not recorded) | DATA |
| E4 | journal themes (if shared), stuck patterns | Memory, privacy | PROV |
| E5 | memories and conversations about "this problem" | Memory, Conversation | STATE + PROV |
| E6 | decisions about the project (notes, conversations) | Data (decisions aren't marked) | PROV + DATA |
| E7 | the primary goal and what needs them now | Retrieval (wrong tools offered today) | QP: progress |
| E8 | patterns (inferred: labelled as such) | Reasoning | FIND + PROV |
| E9 | the plan's history in life events | Integration | LOOP |
| E10 | ideas mentioned, not acted on | Data (ideas aren't marked) | PROV + DATA |
| E11 | projects not done | (answered by code: projects only) | QP: open loops (missions, builds too) |
| E12 | lessons (journal, notes) | Data, privacy | PROV |
| E13 | the person's profile and memories about them | Retrieval | PROV |
| E14 | the last big decision's reasons | Data | PROV + DATA |
| E15 | goals marked dropped, and why | Data (a goal can't be marked dropped with a reason) | DATA |

### F. Research and learning

| ID | Needs | Gap | Fix |
|---|---|---|---|
| F1 | the equipment's manual (Inbox), reference packs | Conversation ("this"), Retrieval | STATE + LOOP |
| F2 | manual, reference, upkeep history | Conversation, Retrieval | STATE + LOOP |
| F3 | the build's materials, what's on hand | Retrieval | LOOP |
| F4 | the three products, current prices | Research | RES |
| F5 | the source and its date | Research | RES |
| F6 | official sources for the person's state | Research (never stated as settled) | RES |
| F7 | the task as it's done now | Conversation, Reasoning | STATE |
| F8 | teaching mode (exists), reference | (teaching mode handles it) | STATE |
| F9 | the problem, step by step | Conversation | STATE |
| F10 | the approaches named | Conversation, Reasoning | STATE |
| F11 | the project's steps, the tools owned | Integration | LOOP |
| F12 | the plan, its costs and dates | Reasoning | STATE + LOOP |
| F13 | options and their costs | Reasoning, Calculation | LOOP |
| F14 | a project plan and bill of materials (proposed) | Action, Calculation | LOOP + STATE |
| F15 | the plan's risks | Reasoning | STATE |

### G. Cross-domain

| ID | Needs | Gap | Fix |
|---|---|---|---|
| G1 | everything that matters now, ranked; one recommendation | Integration, Reasoning | QP: today + FIND |
| G2 | the freedom plan's levers: pay, spending, business, debts | OWN, Integration, Reasoning | QP: freedom |
| G3 | sales and profit by month, trend | Calculation | QP: business month |
| G4 | findings and patterns, labelled as inferred | Reasoning (18 wrong tools today) | FIND + PROV |
| G5 | "this", then a plan | Conversation | STATE + LOOP |
| G6 | spending and saving against the goals' needs | Integration, Reasoning | QP: freedom |
| G7 | projects by goal weight, deadline, return | Reasoning | LOOP + FIND |
| G8 | the freedom plan's biggest bottleneck | Reasoning | QP: freedom |
| G9 | skills, equipment, land, goods, demand | Reasoning across apps | FIND + LOOP |
| G10 | time and money spent on what doesn't serve the goals | Data (time use), Reasoning | FIND |
| G11 | projects' profit and needs | Integration | LOOP |
| G12 | free time and money vs the goals' weights | Reasoning, Calculation | LOOP |
| G13 | skills, equipment, land, business goals | Reasoning across apps | FIND + LOOP |
| G14 | renewals, deadlines, debts, upkeep, seasons, six months out | Integration | QP: coming up (six months) |
| G15 | goals, freedom plan, business, skills: a year's plan (proposed) | Reasoning | LOOP + STATE |

## 4. The first question plans, from this bank

Each one runs its lookups in code, does its arithmetic in code, and
gives the model one fact sheet with every line marked fact, calculation,
estimate or missing. Between them they cover about half the bank:

| Plan | Lookups | Questions |
|---|---|---|
| **today** | Presence, today's Loop, calendar, deadlines, the primary goal | A1, A2, A8, A9, A12, D5, G1 |
| **week review** | life events, weekly check-in, workouts and bests, shifts and loot, missions, sales | A4, A7, D10 |
| **money month** | budget summary, spending by category, recurring bills, untagged charges | B1, B2, B3, B11, B12 |
| **debts** | debts, the payoff plan, the same plan with more a month | B4, B5, B13, B14, B15 |
| **freedom** | the freedom plan, pay (the Dungeon), needs, business profit | B8, B9, B18, B20, C15, G2, G6, G8 |
| **next dollar** | emergency fund, debts' rates, freedom fund, business returns | B10, B16 |
| **rentals** | property summary, rental income, upkeep costs | B6, B7 |
| **products** | products, costs, sales, margins, time per batch | C1, C4, C6, C14, C16 |
| **product cost** | a recipe's materials at cost, labour, overhead | C2, C3 |
| **business month** | ledger, business-use purchases, sales trend | C7, C8, C13, B17, G3 |
| **market prep** | the next market day, planned goods, materials short | C5 |
| **progress** | the primary goal and why, missions and questline, skills, bests | D1, D2, D3, D7, D8, D9, D11, E7 |
| **coming up** | deadlines, renewals, trips, events, two weeks to six months | A10, G14 |
| **tonight** | tomorrow's calendar and Loop, alarms | A5 |
| **open loops** | open tasks, objectives, unapproved proposals, builds | A6, E11 |

The tool loop takes the rest of what's in MIA's records; findings take
the "what have you noticed" questions; conversation state takes every
"this".

## 5. Gaps that need their own decision

1. **Outside research (F4 to F6).** MIA has no internet lookup. Adding
   one is a principle question (MIA is offline-first, DEC-0015's
   computer is online most of the time): a web lookup only when online,
   only when asked or clearly needed, sources cited with their date,
   researched facts kept apart from her own reasoning. Proposed
   separately, not built under DEC-0052.
2. **What MIA doesn't record yet:** commitments made to people (E3, A6),
   decisions and ideas marked as such (E6, E10, E14), a goal dropped
   with its reason (E15), time use outside shifts and workouts (A11,
   G10), workshop overhead as one figure (C12). Most belong in the user
   model (`docs/BODY_AND_RELATIONSHIP_PLAN.md` step 4), each one by
   plain conversation ("I promised Sam I'd fix his gate"), never a form.

## 6. How it's measured

- **The routing audit**: `python -m tools.bench_audit` (no model), the
  table in section 2; re-run after each change.
- **Unit tests** per question plan: the lookups it runs, its arithmetic,
  and the facts its sheet must hold, against a demo life with nothing
  personal in it.
- **The live bench** on the PC's model: each question, two or three
  phrasings (typed, spoken, as a follow-up), scored on the answer
  protocol: answered first, numbers that match the records, facts told
  apart from estimates, missing data named, a next step, nothing
  invented. Results go into this file's section 2 with the date.

**Status per question** lives in section 3 until the live bench runs;
then a results column is added there.
