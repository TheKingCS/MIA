# MIA, the Jarvis build-out: brainstorm (2026-11-23)

Zac, 2026-11-23: "I want her AI polished and extremely intelligent, conversational, and aware. I want smooth
conversation and knowledgeable and integrated with and about my hobbies and interests and able to be the ultimate
tool offline and online for survival skills, homestead skills, my businesses skills, finance skills, automation of as
much as possible ... like Jarvis, super capable, super helpful, super advanced and futuristic. Please brainstorm on
ideas that fit our overall vision for MIA and we will start working on building her out in those areas as well."

Nothing here is approved until Zac picks it (like `docs/future/IDEAS.md`). Each idea says what it is, what it does
for him, what MIA already has to build it on (so nothing is built twice), its size (S: a session, M: a few, L: a
phase), and whether it needs him first. The rules MIA keeps stay true for every one: facts worked out in code and
only phrased by the model; unprompted messages through the communication gate; nothing she reads grants her
anything; email drafted, never sent; no money moved, nothing bought or committed without his press; his data his.

**What she already is (so the ideas start from there):** about 360 tools in 81 areas on a local model (qwen2.5:14b);
a 221 GB offline library (74 Kiwix packs: Wikipedia, WikiHow, iFixit, Stack Exchange, USDA canning, medicine,
gardening...) with her own index and a reader that answers from the page, safety floors included; the Planner (builds
and gardens planned together, then missions); learning paths; Trade Master's walkthroughs; the homestead control system;
budget, ledger, debts, business book; her browser behind a safety gate; memory, recall, life events and links; the
communication gate; grants; the phone, the glasses and MIA OS.

---

## 1. Intelligence and conversation: "she gets it, and it flows"

**1.1 Conversation that flows (barge-in and back-channel).** S-M, no decision needed. *(a) built 2026-11-23 on the
web: one voice per page, and the mic, a new turn or Escape stops her mid-sentence (`web/shell.js` `stopSpeaking`);
(b) in part: her orb says what a lookup is for ("Thinking · Reading your library"), spoken words still to come;
(c) built the honest way (`core/speech_split.py`): the answer is still checked whole (figures, the floors), then only
its first sentence is voiced before it's sent and the page voices the rest while it plays, so her first words come
sooner; streaming the model's own words would skip those checks;
the glasses page too. (b) and (c) to come.*
Talking to her today is turn by turn: he speaks, waits, she answers in full. Jarvis-feel comes from three small things:
(a) he can cut in ("stop", "no, the other one") and she stops speaking at once and takes the new words;
(b) a short spoken acknowledgement while a slow answer is being worked out ("Looking in the canning guide..."), from
what the turn is actually doing (the tool it's running), never invented; (c) her first sentence spoken while the rest
is still being written (streaming speech). Builds on: `core/voice_loop.py`, `core/tts_worker.py`, `core/orb_state.py`
(she already knows when she's thinking), the tool loop's steps.

**1.2 The follow-through memory: "what did we say about..."** M, no decision needed. *First part built 2026-11-23
(`core/left_off.py`): "where were we?" and the front of "catch me up" say the missions he's been on with their next
step, Planner drafts waiting, open promises and recent decisions, from the records. Next: a conversation's own open
questions picked up next time.*
Every conversation ends with what was settled kept as facts with their source (the decision, the number, the next
step), so "what did we decide about the coop door?" is answered from what was actually said, a week later, on any
device. Builds on: `core/life_notes.py` (promises, decisions, ideas, offered after a reply), `core/recall_index.py`,
`core/links.py`. The new part: a conversation's open threads, picked up next time ("Last time you were deciding
between the 2x6 and the 2x8 for the coop floor; did you settle it?"), paced by the gate.

**1.3 Her picture of him, kept current and his to see.** *Built 2026-11-23 on his yes (DEC-0290): the You page
(`core/picture_of_you.py`, `web/you.html`), and "what do you know about me?" says it.* M, needs Zac's go (it's the parked "self-knowledge map",
personality phase 3). One page: what she believes about him (hobbies, projects, skills and their level, what he
likes in an answer), each belief with where it came from and a button to correct or forget it. Every answer reads
it, so she stops asking what she should already know. Builds on: memory, `core/person_settings.py`, the skills
paths, answer style.

**1.4 Thinking before she speaks on hard questions.** M, no decision needed. *Mostly there (checked 2026-11-23): 33 question
plans gather the facts by code, compose when a question joins domains, carry a follow-up, and say how sure they are
(`core/question_plans.py`). The gap found and fixed: "can I buy a $900 welder and still pay off the loan?" now
gathers both plans and works the purchase as the same money on the debt instead (`instead`), never as $900 more a
month.*
For a question with several steps ("can I afford the greenhouse expansion this spring and still pay down the card?")
she plans first: which facts she needs, fetches them with her tools, works the numbers in code, then answers with
the reasoning shown in two or three lines. Today the model chooses tools in one go. Builds on: `core/tool_loop.py`,
`core/question_plans.py` (already plans some questions), the calculators.

**1.5 A bigger mind when the PC can afford one.** S to try, needs Zac (it's his hardware and disk).
qwen2.5:14b is good; a newer local model (a 2026 generation 14B to 32B, or a mixture-of-experts model that runs fast
on his GPU) could be markedly smarter in conversation. A fair test on his own questions decides it: the conversation
check (`python -m tools.conversation_check`) and the 👍/👎 ratings already exist to measure. Builds on:
`core/model_store.py`, the model queue, the fallback chain (FW-12).

**1.6 Learning from his ratings.** L, later. The 👍/👎 and corrections become a small fine-tune (a LoRA on his
PC) so she sounds more like what he likes. Parked already in the personality plan; needs 1.5 settled first.

## 2. Awareness: "she knows what's going on"

**2.1 "What's going on?", made whole.** S-M, no decision needed. *Built 2026-11-23 (`core/needs_now.py`): "catch
me up" now starts with what needs him (greenhouse alerts, tonight's weather, an update waiting), what the gate is
holding, and what she did on her own since yesterday with how to undo it.*
Half there: "catch me up" / "what's going on with me" already answers from the life state (wins, what's in the way,
what waits on what, the monthly plan). Missing: the homestead (greenhouse readings, the flock), the weather's effect
on today, what she did on her own overnight with its undo, and an order by what needs him first; spoken short, shown
long, the same on the second monitor. Builds on: `core/context_assembler.py` (`describe_life_state_v2`),
`core/homestead_manager.py`, `core/ambient.py`, `core/weather.py`, the undo log.

**2.2 Weather that changes plans.** S, no decision needed. *Built 2026-11-23 (`core/weather_watch.py`): frost,
hard freeze and cold nights against the garden, heat and freezing water against the flock, and (the same day)
rain likely tomorrow against a Planner build in progress.*
She reads the forecast against what he's planned: a frost tonight against the seedlings in the Planner, rain against
the roofing mission, heat against the flock, wind against a burn. One gate message, with the action ("Cover the
tomatoes? I'll make it a mission."). Builds on: `core/weather.py`, the Planner, missions, the greenhouse snapshots.

**2.3 Noticing what's unusual.** M, no decision needed. *First check built 2026-11-23 (`core/unusual.py`): the
hens laying far below their own normal, judged only on logged days, said weekly with the causes to check; on the
Chickens page and in "how are the hens?". Second, the same day: a spending category already half again past its usual whole month. Next: a bill that didn't
come.*
A change from his normal is worth a word: spending in a category far above its usual, the greenhouse water
temperature drifting, egg count down three days running, a bill that didn't arrive, a mission stalled for weeks.
Each is a small check in code with its own normal learned from the history (`core/life_events.py`), offered through
the gate with what she thinks it means and what to check first. Builds on: life events, budget, flock, greenhouse,
the loops' pacing.

**2.4 Cameras and sight that understand.** M-L, needs Zac (cameras and a vision model).
"Is the coop door closed?", "what's this plant?", "what's wrong with this outlet?" answered from a photo or a camera,
by a local vision model, with the offline library behind the answer. Builds on: `apps/sight`, the camera actions,
`core/ocr.py`, the glasses' camera.

## 3. Knowledge of his hobbies and interests

**3.1 A specialist for each of his worlds.** M each, no decision needed for the first. *In progress in another session
(`docs/specialists/`): not built twice here.*
When he talks about the homestead, construction, the businesses, money, she answers as that specialist: the right
reference packs first, its own safety floor, its vocabulary, the questions a pro would ask back. Builds on:
`docs/specialists/` (being started now in another session: construction, homesteading, strategy), the offline
library's per-pack index, Trade Master. The specialists should all read his own records (his plans, tools,
inventory, budget) so an answer is about his place, not a textbook's.

**3.2 Ask the library like an expert friend.** S-M, no decision needed. *"Show me where it says that" built
2026-11-23 (`core/show_source.py`): the article (or PDF page) her last library answer came from opens on the Knowledge
page. Following up on the same passage already works ("tell me more about that": `read_reference`). Sources that disagree: her reading guidance already tells her to say so
(`HOW_TO_TALK`); a code check comparing figures across sources is worth building only if she's seen to miss one.*
Follow-up questions about the same passage ("and if it's a pressure canner without a gauge?"), "show me where it says
that" (the page opened at the passage), and a comparison across sources when they disagree ("the USDA says 25
minutes; this older guide says 20; go by the USDA, it's newer and tested"). Builds on: `core/reference_reader.py`.

**3.3 Hobby companions.** S each. *Built 2026-11-23 on his answer (DEC-0289): learning programs for woodworking,
gardening and homesteading, fitness, and survival and bushcraft (`core/woodworking.py`, `gardening_path.py`,
`fitness_path.py`, `bushcraft.py`), beside guitar.*
Guitar already has a learning path (`core/guitar.py`). The same shape for each hobby he names: a practice log, the
next stage, weekly homework missions, her honest read on progress. Needs his list of hobbies to start.

## 4. Survival and homestead, offline first

**4.1 Grid-down mode.** M, no decision needed. *Note 2026-11-23: her offline posture already exists
(`core/connectivity.py`: she knows she's offline and says what still works); what's left needs his preparedness
records (4.3) to count days of water, food and power.*
When the internet or the power is out, she changes posture on her own: says so, works fully from the library and
his records, and opens a "grid-down" page: days of water and food on hand (from the pantry and inventory), power left
and what's drawing it, the flock's and greenhouse's needs without power, a checklist for the first hour, day and week,
and the radio frequencies he keeps. Every number worked out in code from his records. Builds on:
`core/connectivity.py` (she already knows when she's offline and what that stops), the offline library,
kitchen/pantry, inventory, the homestead system, `core/safety_floor.py`.

**4.2 First aid with a safety floor.** M, no decision needed (the floor follows the canning one). *First part built
2026-11-23 (`core/first_aid_floor.py`): an emergency happening now gets the emergency number and the first steps in
fixed words before any model. Second part, the same day: a first-aid answer from her library always ends with when to call and the number
(`library_floor`).*
Step-by-step first aid from the library's medical packs (wilderness and field medicine), with a floor in code that
always says when to call emergency services (by his country, `core/region.py`) and never gives a dose the page
doesn't. Builds on: the canning floor's pattern in `core/reference_reader.py`, `core/safety_floor.py`.

**4.3 Preparedness inventory and rotation.** S-M, no decision needed. *First part built 2026-11-23
(`core/preparedness.py`, "how prepared am I?"): days of drinking water from the pantry at a gallon a person a day against
his target (14 days unless he sets one), what to use before it expires, and (the same day) days of food from the
staples he logs by weight at USDA calories. Power waits for what he has for power.*
What he keeps for emergencies, its dates, what to rotate into the kitchen before it expires (into meal plans), and
what's short against a target he sets (two weeks, three months). Builds on: inventory, kitchen, groceries, missions.

**4.4 The homestead year.** M, no decision needed. *Built 2026-11-23 (`core/homestead_year.py`, the Planner's
"The Year Ahead", "what's coming this year on the homestead?"): his garden plans' dates and his recurring upkeep,
month by month over twelve months. The flock's seasons and firewood join it as their records exist.*
One calendar of the whole year from his own place: planting and harvest by his frost dates, the flock's seasons,
canning windows, firewood, maintenance by season, each becoming missions at the right time. Builds on: the Planner,
garden plans, maintenance, `core/seasons`, missions.

**4.5 Radio and mesh, for when nothing else works.** M-L, needs Zac (hardware).
A Meshtastic or LoRa node so his phone and MIA can still talk across the property with no internet or cell; later,
a scanner feed she listens to for weather alerts. Builds on: MIA OS, the device fabric.

## 5. His businesses

**5.1 The business brain: quotes, jobs, customers.** M, no decision needed for the first part. *Mostly there
already (checked 2026-11-23): `core/business_book.py` has customers, quotes priced from a recipe's materials, hours,
labor rate and margin, orders whose payments go to the ledger, and market days. What's left: a quote from a Planner
build's own material list, and the invoice drafted from an order.* *The first built 2026-11-23 (`core/plan_price.py`,
"what should I charge for the shed?"): the build's materials priced from his workshop, his hours, rate and margin.
The invoice too (an order's Email Invoice: what's paid, what's left, when it's due; drafted, he presses Send).*
For a build or repair job: a quote from the materials and hours (worked out in `core/build_calcs.py`, priced from his
own records), the job as a mission, the customer and what was promised, the invoice drafted (never sent without his
press), and paid or not. Builds on: business book, Trade Master, build calcs, email drafts.

**5.2 What's actually profitable.** S-M, no decision needed. *Mostly there already: each build's profit and
profit per hour (`core/craft_recipes.build_result`), the Workshop's best earner per hour, market days' takings
(`core/goods.py`), the flock's feed cost per dozen, homestead costs per hour. What's left: the stand's goods ranked
the same way.*
Per product and per business: what it really earns once his hours, feed, jars and fuel are counted, so he knows which
eggs, wood goods or plant starts are worth more of his time. Builds on: business book, homestead costs, the ideas list's
businesses.

**5.3 The stand and the market.** M, later. *Mostly there already: market days, what sold, and how many to bring next time from what sold out (`core/goods.demand`).* What sold, when, at what price; what to bring next Saturday; a price check
against the season.

## 6. Finance

**6.1 The next 90 days of money.** M, no decision needed (from his entered records; Plaid stays off). *Built
2026-11-23 (`core/money_ahead.py`): 13 weeks of bills, income and debt minimums by week, the tight ones first; the
Money page's Ahead tab and "what does money look like the next few months?". A balance joins it with bank linking.*
"Can I afford it?" already exists (a question plan that checks a purchase against his freedom date). Missing: the
day-by-day picture it stands on: the next 90 days from bills, income, debt payments and planned purchases, the
lowest point and when, and what a purchase pushes back. Worked in code. Builds on: budget, debts, ledger,
`core/question_plans.py`'s afford plan, `net_worth_history.py`.

**6.2 Debt payoff and savings plans as missions.** S-M. *Debts built 2026-11-23 (`core/debt_missions.py`, the Money page's Debts "Make It A Mission", or "make my payoff plan a mission"): a step a debt in payoff order with its month, ticked as each balance reaches zero (by the debt's id; completed when all are). Savings were already there: the Freedom
plan (`core/freedom.py`, DEC-0038) saves toward a date, worked out in code.* A payoff plan (avalanche or snowball, his pick) whose monthly
steps are missions with real progress. Builds on: debts, missions, learning paths' stats.

**6.3 Bank linking.** Deferred by Zac (Plaid, until MIA is further along and secure).

## 7. Automation: "she just handles it"

**7.1 Routines she proposes from what he does.** M. *Built 2026-11-23 on his answer (DEC-0294,
`core/habit_offers.py`): the same thing on the same weekday three weeks running is offered as a weekly reminder, once.*
She notices a repeat (every Sunday he checks the budget and plans meals) and offers a routine for it; once he says yes,
it runs with an exact undo (his rule: routine actions run on their own with a precise Undo; approval only for what
goes outward or can't be undone). Builds on: `core/workflows.py`, grants (`grants.standing`), routines, the undo log.

**7.2 "When this, do that."** M, no decision needed. *Half there: `core/workflows.py` runs his workflows every
day, week or month (read, count, compare, tell, add) under a grant; what's missing is a trigger on an event ("when a
bill comes in") and the homestead's controls as a step. *Needs Zac first:* an event can come from something she
reads (an email, a page), and nothing she reads may grant her anything, so which events may start a workflow is his
call.* *Built 2026-11-23 on his answer (DEC-0293): a workflow may start on an event in his history; one from something
she read runs with every change waiting for his yes. The homestead's controls as a step need Zac first: today MIA only reads the homestead's snapshots (DEC-0145), so a step that works its pumps or vents is a new control path into real equipment (WAITING_ON 0zj).*
Rules he says out loud: "when the greenhouse goes over 90, tell me and open the vents", "when a bill comes in, add
it to the budget". Each a workflow with its tier from the manifest; the risky ones ask. Builds on: workflows, the event
bus, the homestead's controls, grants.

**7.3 Errands on her browser.** M, partly built. She already browses behind the gate; the next step is whole errands
("find the cheapest 50 lb bag of layer feed within 20 miles") ending at the commit button for his press.

**7.4 Inbox triage.** In progress in another session (`core/email_inbox.py`, `email_extract.py`): bills, orders and
appointments pulled from email into their places.

## 8. Futuristic presence

**8.1 A wall MIA.** *There already (checked 2026-11-23): the ambient view (`core/ambient.py`, `web/ambient.html`,
DEC-0231) is exactly this, on his second monitor today and on any tablet's browser.* S-M, no decision needed: a kiosk view (big clock, what's due, Talk, the situation report), for a
tablet or a salvaged screen (the Echo Show idea in NEXT_SESSION section 3).
**8.2 Her voice everywhere in the house.** M, needs hardware: Pi satellites with a mic array and wake word.
**8.3 The glasses as a heads-up display.** *Mostly there (checked 2026-11-23): a Trade Master job is walked by voice
("next", "what's next": `core/trade_actions.py`) from any Talk, the glasses' included, and the glasses' Home shows
the mission's next step.* Already started (DEC-0066); next: step-by-step walkthroughs shown
hands-free while he works (Trade Master's steps on the glasses, "next step" by voice).
**8.4 A 3D view of the property.** L, later: the land, buildings, greenhouse and sensors as one map she can point at.

---

## Claude's recommendation for the order

Start with what makes every conversation better, then what makes her aware, then the big domains:

1. **2.1 "What's going on?"** and **2.2 weather that changes plans**: one session, felt every day.
2. **1.1 conversation that flows** (barge-in, spoken acknowledgements, first sentence spoken early).
3. **4.1 grid-down mode** and **4.2 first aid with a floor**: the offline promise, made real.
4. **1.2 follow-through memory** and **2.3 noticing what's unusual**.
5. **6.1 money forecast**, **5.1 quotes and jobs**, **7.1/7.2 automation**.
6. With Zac: **1.5 a bigger model** (his hardware), **1.3 her picture of him** (his go), **3.3** (his hobby list).

Questions for Zac (each is the Q he answers to unlock it):
- Which hobbies should get a companion first (3.3)?
- May she build the "picture of you" page (1.3)?
- Try a bigger local model on your PC (1.5)? It's a download of 10 to 20 GB.

---

## Round 2 (2026-11-23, after the first round was built)

New ideas, each checked against what's there first:

- **This week in the garden** (S, no decision): built 2026-11-23 (`core/garden_week.py`): his garden plans' steps in
  the next seven days, once a week through the gate, and "what's due in the garden this week?".
- **Seed inventory against the plans** (S-M): what seeds he has (the pantry or inventory) against what his garden
  plans need, said before the starting dates. *Built 2026-11-23 (`core/seed_check.py`): crops starting in the next
  month with no seeds logged (pantry or inventory) are named in the garden's weekly message.*
- **The canning shelf** (S-M): jars put up, by date, from his kitchen records, with the USDA's best-quality window
  ("use within a year") said as they near it. Builds on the pantry's expiry dates. *Partly there: "how prepared am I?" lists
  what expires in the next 30 days (`core/preparedness.rotate`).* *Built 2026-11-23 (`core/canning_shelf.py`): "I put up 7
  quarts of tomatoes" keeps a dated batch in the pantry, best by a year on; "what's on my canning shelf?" says the
  oldest first, what's past or nearing a year, and never to taste a jar whose seal failed.*
- **Equipment hours to service** (S): the hour meters he logs (core/maintenance_manager.py meter tasks) said a week
  before a service falls due, through the gate. *Already there: `core/maintenance_insights.py` says a meter task
  trending toward due soon.*
- **Water made safe with bleach** (S, no decision): built 2026-11-23, a calculator (`core/eng_calcs.py`
  `water_bleach`): the EPA's drops of unscented bleach for the gallons and the bleach's strength, 30 minutes' contact.
- **How long the feed lasts** (S, no decision): built 2026-11-23 (`core/feed_runway.py`): from the last bag and how
  fast his flock really eats (else a quarter pound a hen a day), on the Chickens page and in "how are the hens?", and
  said once a bag when it's down to five days.
- **The day before a market** (S, no decision): built 2026-11-23 (`core/market_eve.py`): what to bring from what
  usually sells (his own closed markets), beside what's on hand and what's short, the day before a market day he set.
- **A quiet evening wrap**: *built 2026-11-23 on his yes (DEC-0292, `core/evening_wrap.py`), and "wrap up my
  day".* (M, his say: it's a new daily message): what got done today, tomorrow's first thing, the
  weather for it, in two sentences, at the hour he usually winds down.

## Round 3 (2026-11-23)

- **The 72-hour kit** (S, no decision): built 2026-11-23 (`core/ready_kit.py`, "check my emergency kit"): Ready.gov's
  basic kit against his inventory and pantry by whole words, water and food against three days (from
  `core/preparedness.py`), what isn't in his records said as that, and what only he can check (medicine, glasses,
  cash, papers). Read-only.
- **A purchase against the debts** (1.4's gap): built the same day, see 1.4.
- **Power in "how prepared am I?"** (S, no decision): built 2026-11-23 (`core/power_ready.py`): gasoline, diesel,
  kerosene and propane from his inventory and pantry, in gallons, and his generator's days on it at his burn rate and
  hours a day; the people, target days and generator are set by voice (`set_preparedness`).
- **Who owes me** (S, no decision): built 2026-11-24 (`core/receivables.py`, "who owes me?"): what's still unpaid on
  his orders (price less payments taken), oldest due first, the overdue and the delivered-but-unpaid named as the
  ones to chase, with the invoice draft he already has as the next step. Read-only.

## Round 4 (2026-11-24, checked against the code first)

- **Eggs in the incubator** (S, no decision): built 2026-11-24 (`core/hatch_tracker.py`): "I set 12 chicken eggs
  in the incubator today" makes a mission with that bird's dated candling, lockdown and hatch-day steps (chicken 21
  days, duck and turkey 28, goose 30, guinea 27, quail 17); "how's the hatch going?" says the day and what's next.
- **Firewood for the winter** (S-M, no decision): cords on hand (inventory) against what a winter takes, from his
  own burn record (logged loads, the stove's use) once there's a season of it; until then a stated estimate he can
  correct. *Built 2026-11-24 (`core/firewood.py`, "do I have enough firewood?"): cords and face cords from his
  inventory against his own winter figure ("I burn 4 cords a winter"); without it the usual range is said as only that.*
- **Seed saving** (S, no decision): seeds saved from his own plants (which bed, the year, how many), kept with the
  pantry or inventory seeds so the seed check (`core/seed_check.py`) counts them, with how many years each kind
  stays viable. *Built 2026-11-24 (`core/seed_life.py`, "are my tomato seeds still good?"): each kind's usual span,
  and his packets dated by a year in their names said good, worth a germination test, or past it.*
- **The brooder** (S, after the hatch): chicks' temperature by week (start near 95 F, down about 5 F a week), as the
  hatch mission's next steps once they're out. *Built 2026-11-24: the hatch mission's last step.*
- **The offline library on Windows** (needs Zac, WAITING_ON 0zh): Smart App Control blocks its reader; the options
  are written there.

## Round 5 (2026-11-24, checked against the code first)

- **Should I water today?** (S, no decision): built 2026-11-24 (`core/weather_watch.watering`): rain now or likely
  tomorrow says hold off, a hot dry day says water deeply in the morning, every answer ends with the soil check.
- **What can I plant now?** (S, no decision): built 2026-11-24 (`core/planting_now.py`): from his last spring frost,
  what's due to start indoors, transplant or sow now, and one crop's next step and date ("when do I plant
  potatoes?"); his frost date is asked for, never assumed.
- *Found already there:* feed cost per dozen eggs (`core/flock.py`, on the Chickens page and in "how are the hens?").
- **What's left in a budget** (S, no decision): built 2026-11-24 (`budget_left`): this month's budget targets, spent
  and left, from the Money page's own figures.
- **Mixing feed to a protein** (S, no decision): built 2026-11-24 (`core/feed_mix.py`): the Pearson square, parts,
  shares and a batch's pounds of each.
- **A rain gauge log** (S, no decision): rainfall he reads off a gauge, kept by day, so "should I water?" counts
  the week's real inches instead of only the forecast. *Built 2026-11-24 (`log_rain`, kept in the data logger;
  "should I water?" leads with the week's inches).*
- **Meat birds' processing day** (S, no decision): a batch of broilers as a mission dated from hatch (Cornish cross
  around 8 weeks, slower breeds later), with the feed they'll eat to get there. *Built 2026-11-24
  (`core/broiler_batch.py`).*
- *Built 2026-11-24 too:* his rain gauge (`log_rain`, counted by "should I water?") and a batch of meat birds to
  processing day (`core/broiler_batch.py`).

## Round 10 (2026-11-24, night): survival at home, money and automation, checked against the code

- **The power's out** (no decision): *built 2026-11-24 (`core/outage.py`, "the power went out at 6 am", the Power
  page's The Power's Out).* A clock from when it went out: the fridge's 4 safe hours and the freezer's 24 or 48 as
  time left (FoodSafety.gov), the generator's fuel days, the fish tank's air pump first, the hens' water, the well;
  "the power's back" says what to throw out.
- **A boil-water or no-water day** (no decision): *built 2026-11-24 (`core/water_day.py`, the tool
  `water_emergency`: his drinking water in days, his tanks never said as drinkable, the hens' share, the CDC's boil
  and bleach).* the same shape for water: stored water against his household's
  gallons a day (one a person, more for the animals), the rain barrels and cistern (core/water_budget.py), and how to
  make water safe offline (boil one minute; the library's pages when it runs).
- **A storm coming** (his say: an unprompted heads-up through the gate): the forecast's wind, ice or heavy rain two
  days out turned into one checklist from his records: fuel for the generator, the greenhouse's battery, the flock
  shut in, the outage kit, what to pick before a frost.
- **The monthly bills that change** (no decision): *built 2026-11-24 (`core/utility_bills.py`, the tool
  `why_bill_high`).* electric, propane and fuel bills read against the same month last
  year and his meter readings, so "why was power so high?" has an answer from his own numbers.
- **Automation he can see** (his say on each): routines that already run on their own (core/routines) listed with
  what they did this week and what they'd do next, so "what's MIA handling for me?" has one honest answer.

## Round 9 (2026-11-24, evening): after the game layer and the greenhouse's command path

Checked against today's code; each says whether it needs Zac's say.

- **The Chronicle tells the homestead, songs and wins** (no decision): *built 2026-11-24 (`core/chronicle.py`).* The
  week's and year's story now has a Homestead thread (eggs once a day, jars put up), Music (songs learned) and Wins
  (achievements and mission rewards, named among the highlights).
- **Achievements for the business and the money** (no decision, read from records): *built 2026-11-24 (Trade: a
  first sale to 1,000; Debt Free: a debt paid to nothing, 3, 5; core/life_milestones.py).* a first sale, 10 and 100
  products sold (core/business), a debt paid off, the freedom date moved a month nearer (core/freedom.py), the
  first month under budget. The same chains as harvest and eggs, so the card and the log come for free.
- **"How's the pH against its target?"** (no decision): *built 2026-11-24 (`core/greenhouse_adjust.against_targets`).*
  the greenhouse's readings beside the targets MIA now reads
  from the node (`mia_directions.targets`), said as inside, drifting or outside, with how long; awareness, read only.
- **A song reward fills the songbook** (no decision: a reply to his own action): *built 2026-11-24
  (`core/mission_trophies.songbook_offer`; Play Along on Music's Can Play tab plays the saved YouTube song named
  like it). Both seen working in the real app (a throwaway MIA in Edge).* finishing a mission whose reward is
  a song asks "can you play it now?" and adds it on yes; a saved YouTube song can be linked to a songbook song for
  play-along practice.
- **Canning as a skill** (no decision): *built 2026-11-24 (Preserving (Canning), under Food Production; each batch
  put up grants it XP).* a Canning (Preserving) skill in the skill tree, so jars put up and canning
  missions grow it, as gardening and carpentry already grow.
- **"Almost there"** (his say: a new kind of unprompted message, through the gate): when a tier is within a little
  of done (3 jars from First Batch, 12 lb from Market Gardener), MIA offers one mission for it, paced like every
  other suggestion.
- **The card on the phone and the glasses** (his say for a phone notification): the achievement card as a push to
  his phone and a tile on the glasses, the same card the PC shows.
- **Greenhouse targets suggested from evidence** (his say: MIA's own initiative on the greenhouse, DEC-0185/0156):
  when the node's trends or an experiment's result point to a better band, MIA proposes the adjustment with the
  evidence; it still goes through his yes and the node's own check.

## Round 8 (2026-11-24, after the live check): the same principle, further

Checked against the code first; each says whether it needs Zac's say.

- **Am I ready for winter?** (no decision): *built 2026-11-24 (the question plan "winter").* One sheet before his
  first fall frost: firewood against his winter
  figure (core/firewood.py), fuel and the generator's days (core/power_ready.py), the 72-hour kit, the flock's
  water in a freeze, what's still in the garden and the canning shelf. The same shape as the project picture, for a
  season instead of a build.
- **Which products should I raise prices on?** (no decision): *built 2026-11-24 (`core/product_pricing.py`).* each product's price against its materials and the
  hours its builds took (core/hourly_earnings.py), the ones selling below his quoting rate named, with what the
  price would be at it. His businesses, from his own records.
- **What if I quit at the end of next year?** (no decision, a read): *built 2026-11-24 (the question plan "quit
  by", `core/freedom.quit_by`).* the freedom plan run with a date he names
  against his debts, the homestead's goods, the business's real hourly and who owes him: what's covered, what
  isn't, and the gap a month. Read-only; the biggest "one intelligence" question there is.
- **Rain catchment** (no decision): *built 2026-11-24 (`core/rain_catchment.py`, "how much rain could I catch off a
  400 square foot roof?").* a roof's square feet and his logged rain into gallons a month (0.6 gallons a
  square foot an inch), against what the greenhouse and garden drink; the project picture's water line gets a
  number instead of guidance.
- **A follow-up to a quiet customer, drafted** (his say: drafted only, never sent): from "who are my best
  customers", the regulars gone quiet get a short email draft he can read and send himself (the drafting already
  exists; only the offer is new).
- **The month's money story** (his say: a new monthly message): on the first, two sentences: the month against his
  usual, the freedom date's move, the one thing that changed it. Paced by the gate like the evening wrap.
- **A rainy-day plan** (no decision): *built 2026-11-24 (the weekend plan names a wet day for indoor work).* the weekend plan already reads the forecast; on a wet day it could lead with
  his learning path's next practice (guitar, the woodworking lesson) and indoor shop work from the cut list.
- **Hear every plan's answer on the real model, weekly** (no decision): the live check now covers today's tools;
  the same for each question plan's sheet (does the answer go area by area, does it invent a number), so a prompt
  change never quietly makes her vaguer. Night School could run it.
- **A bigger model where it counts** (WAITING_ON 0zi): five tool mix-ups the descriptions can't fix (rental income
  without a property, "are we on budget", a mower's make, business use, "mission" as an ordinary word) are the
  14b model's limit.

## Round 7 (2026-11-24): one intelligence (Zac: "connecting all these capabilities into a unified intelligence layer")

- **What a project touches** (no decision): built (`core/project_ripple.py`): "I'm planning to build a greenhouse"
  gathers the build's materials and cost against stock, money and the freedom date, growing, water, power, the flock,
  time, goals and research onto one sheet; each Planner draft shows the same as "What It Touches". The plan for the
  rest of the layer: `docs/future/UNIFIED_INTELLIGENCE.md` (WAITING_ON 0zl, 0zm).
- **Confirmed builds in money answers** (no decision): built: "can I afford it?", priorities and projects say what
  confirmed builds still need from the store, against the stock now.
- **What can I build with what I have?** (no decision): built (`core/buildable.py`): the Library's builds closest
  to done from the workshop's stock, what's left to buy and its cost.
- **Harvests by voice** (no decision): built (`core/harvest_log.py`): "I harvested 5 pounds of tomatoes" goes on his
  grow lab batch of that crop (one added when there isn't), and "what has the garden produced this year?" adds it up
  by crop, valued at store prices he recorded in the same unit.
- **What should I do this weekend?** (no decision): built (the question plan "weekend"): each weekend day's forecast
  (the weather now reads a week), what's due, the garden, learning and projects.
- **What do I really make an hour?** (no decision): built (`core/hourly_earnings.py`): finished jobs' sales less
  materials and expenses over their hours, the best and lowest, beside his quoting rate.
- **Who are my best customers?** (no decision): built (`core/best_customers.py`): customers by what they've paid on
  their orders, each one's share, and the regulars with no order in six months.

## Round 6 (2026-11-24): the bigger steps, each needing Zac's say

Checked first and already there: business miles and a tool's business use (`core/business_use.py`), feed cost per
dozen (`core/flock.py`). The small everyday answers are now mostly built; what would move MIA furthest next are these,
each his call:

- **Hear her on his real phrasing** (needs Zac, at the PC or phone): the routing tests hold about 120 everyday
  sentences, all written by Claude. A week of his own would find what no probe does. *The most valuable next step,
  and already wired:* `core/failure_log.py` keeps each miss she can see (a correction, the same thing asked again, a
  matched tool not used, an undo, a thumbs-down) and `fix_report()` ranks them with a test case each; a session at
  the PC reads it and turns them into fixes.
- **A morning briefing on the glasses or phone at a set time** (his say: a new daily message): the day's first thing,
  the weather against his plans, what the gate holds, in three sentences, spoken.
- **Shop mode** (S-M, his say on how it's started): hands-free in the shop: the build's cut list read out one cut at a
  time ("next"), timers by voice, a measurement converted on the spot; Trade Master already walks a job by voice.
- **The offline library on the PC** (WAITING_ON 0zh): every survival and homestead how-to answer gets better with
  her packs searchable again.
- **A model that fits the new PC** (WAITING_ON 0zi): the comparison is ready for him to read.
- **Is the homestead making or losing money?** (his say: what counts): the builds, tools and feed against eggs and
  goods sold and market days are all recorded, but which expenses and sales are "the homestead" (the truck? the
  garden's groceries saved?) is his to define before she adds them up. Asked 2026-11-24, it reaches nothing yet.
