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

**1.3 Her picture of him, kept current and his to see.** M, needs Zac's go (it's the parked "self-knowledge map",
personality phase 3). One page: what she believes about him (hobbies, projects, skills and their level, what he
likes in an answer), each belief with where it came from and a button to correct or forget it. Every answer reads
it, so she stops asking what she should already know. Builds on: memory, `core/person_settings.py`, the skills
paths, answer style.

**1.4 Thinking before she speaks on hard questions.** M, no decision needed.
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

**3.1 A specialist for each of his worlds.** M each, no decision needed for the first.
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

**3.3 Hobby companions.** S each.
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
his target (14 days unless he sets one), and what to use before it expires. Days of food and power wait for records
that say what each thing feeds and what he has for power.*
What he keeps for emergencies, its dates, what to rotate into the kitchen before it expires (into meal plans), and
what's short against a target he sets (two weeks, three months). Builds on: inventory, kitchen, groceries, missions.

**4.4 The homestead year.** M, no decision needed.
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
"what should I charge for the shed?"): the build's materials priced from his workshop, his hours, rate and margin.*
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

**6.2 Debt payoff and savings plans as missions.** S-M. *Debts built 2026-11-23 (`core/debt_missions.py`, the Money page's Debts "Make It A Mission", or "make my payoff plan a mission"): a step a debt in payoff order with its month, ticked as each balance reaches zero. Savings next.* A payoff plan (avalanche or snowball, his pick) whose monthly
steps are missions with real progress. Builds on: debts, missions, learning paths' stats.

**6.3 Bank linking.** Deferred by Zac (Plaid, until MIA is further along and secure).

## 7. Automation: "she just handles it"

**7.1 Routines she proposes from what he does.** M. *Worth designing with Zac first (2026-11-23): what she may infer from his habits, and what a yes turns into, so it's never a guess.*
She notices a repeat (every Sunday he checks the budget and plans meals) and offers a routine for it; once he says yes,
it runs with an exact undo (his rule: routine actions run on their own with a precise Undo; approval only for what
goes outward or can't be undone). Builds on: `core/workflows.py`, grants (`grants.standing`), routines, the undo log.

**7.2 "When this, do that."** M, no decision needed. *Half there: `core/workflows.py` runs his workflows every
day, week or month (read, count, compare, tell, add) under a grant; what's missing is a trigger on an event ("when a
bill comes in") and the homestead's controls as a step. *Needs Zac first:* an event can come from something she
reads (an email, a page), and nothing she reads may grant her anything, so which events may start a workflow is his
call.*
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
**8.3 The glasses as a heads-up display.** Already started (DEC-0066); next: step-by-step walkthroughs shown
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
