# MIA Conversational Audit (2026-09-27)

How well MIA turns what you say into the right change in the app:
updating assets, finances, greenhouse plants, recipes, groceries,
parts, materials and products, using her tools, and knowing herself.

## How it was tested

MIA's model can't run in Claude's cloud workspace (its network blocks
the model downloads), so the audit split into two halves:

1. **Everything around the model, measured here.** A tool can only be
   used if it's *offered* to the model for that message. So the audit
   checked, for realistic sentences, whether the right tool is offered,
   whether it exists, whether it finds your records from your own words,
   and whether it changes the right data. All of that is deterministic
   and is now permanent tests:
   - `tests/assistant_routing_corpus.py`: realistic requests with the
     tool each must reach, plus small talk that must stay tool-free
   - `tests/test_assistant_routing.py`: enforces the corpus
   - `tests/test_assistant_domain_actions.py`: runs each tool against
     real data and checks the record actually changed
2. **The model's own choices, measured on your computer.**
   `tests/live_model_check.py` now has 187 cases (29 new). It checks
   that the model picks the right tool and, new, that it passes your
   actual words and numbers.

## Results

| | Before | After |
|---|---|---|
| Realistic requests reaching the right tool | **23 of 77 (30%)** | **77 of 77** |
| Requests needing a tool that didn't exist | 31 | 0 |
| Existing tools missed by natural phrasing | 21 | 0 |
| "How do I…?" questions wrongly treated as commands | 2 | 0 |
| Live-model checklist cases routing correctly (dry run) | n/a | 187 of 187 |

## What was wrong, and what changed

### 1. Whole areas MIA couldn't touch (31 requests)
**Kitchen** (recipes, meals, grocery list, pantry) and **Debts** had no
tools at all. Neither did budget targets, asset details and notes, or
quantities for parts, materials and products. You could see them in the
app but not talk to MIA about them.

**Fixed:** 24 new tools (`core/assistant_domain_actions.py`):
- **Assets:** update details (make, model, serial, purchase date),
  "tell me about my mower", and dated notes ("the deck belt is
  fraying")
- **Greenhouse and garden:** plants are Maintenance items in the
  Garden/Plant category, so they get the same tools, and "the
  greenhouse" filters to plant care
- **Debts:** add, update, list, record a payment, "which should I pay
  off first?"
- **Budget:** set a category's monthly budget
- **Kitchen:** add a recipe (with ingredient amounts parsed from speech,
  e.g. "2 lb ground venison"), list recipes, "what can I make with what
  I have?", log a meal
- **Groceries and pantry:**
  - add to the list (several items at once)
  - read the list back and check items off
  - add what a recipe needs
  - track what's in the pantry
  - "we're out of flour"
- **Workshop:** parts used or bought, materials used or bought, a
  material's price, products made

### 2. Existing tools missed how people talk (21 requests)
Tools were only offered for exact trigger phrases. "I just put 120
hours on the mower", "Sharpened the mower blades", "I watered the
tomatoes" and "Add plywood to my materials" reached nothing. "Do I
have any 555 timers?" hit Inventory's "do i have" phrase and offered
the wrong area's tools.

**Fixed:** requests now also match on:
- **Each area's vocabulary** (whole words only): "mileage", "debt",
  "plywood", "resistors", "pantry", and so on
- **The names of your own records**, by their main word: "the mower"
  finds Riding Mower, "the peppers" finds Pepper Plants. Debt names
  must match in full, so "the truck" doesn't drag in "Truck Loan".

### 3. Tools demanded exact names
Handlers only acted when the model passed the record's exact stored
name. "I changed the oil in the truck" needed "Oil change" and "Pickup
Truck", which the model has no way to know.

**Fixed:** `core/assistant_lookup.py` finds records from your own
words ("the truck", "watered the tomatoes"). It acts only when exactly
one record matches. Otherwise MIA asks which one or lists what exists.
Deletes still require the exact name. A reading like "120 hours on the
mower" with no task named now goes to the mower's hour-based task, or
its own hour meter.

### 4. How-to questions became commands
"How do I add a bill?" contains "add a bill", so MIA got the bill
tools and none of her help docs. She could have added a bill instead
of explaining.

**Fixed:** questions about *using* MIA ("how do I…", "where do I…",
"how does X work", "what does the X module do") are answered from
her help docs. Data questions ("how does my budget look?", "how much
have I spent?") still use tools.

### 5. Gaps in MIA's self-knowledge
Her help docs had nothing on Debts, the phone app, or what you can say
to her per area. **Fixed:** the Assistant help page now lists example
sentences for equipment and plants, money, kitchen and workshop, plus
phone access and what she does when unsure. Budget help covers Debts
and Bank Sync's new buttons. Confirmed her help lookup returns these
sections for the matching questions.

### Bugs found along the way
- Word matching turned "groceries" into "groceri", so "grocery" didn't
  match the Groceries category. Fixed ("-ies" → "-y").
- A former known gap in the live checklist ("Log 46000 miles for the
  Oil Change on my Truck" reached no tool) is now closed.

## Trade-offs to know about

- **Passing mentions of your things offer tools.** "I was driving the
  truck home" now offers Maintenance tools, because recognizing "the
  truck" is what makes "I changed the oil in the truck" work. The model
  still decides whether to call one, and there are live checklist cases
  checking that it *doesn't* write anything for sentences like that.
  Watch for this in real use.
- **Slightly more tools per request.** Matching more areas means about
  18 tools offered on average in the live checklist. This project has
  seen small models get worse as that number grows, so the live check
  is the real test.
- **Casual facts still become memories, not records.** If you mention
  in passing that the mower has a new battery, MIA files it as a memory
  about you. It only updates the mower's record if you say it as an
  update ("note that the mower has a new battery").

## Not covered yet

- ~~Workout, People & Pets, Household routines, Classroom~~ **covered
  (same day):** 18 tools in `core/assistant_life_actions.py`, 22 more
  corpus requests, 12 more live checklist cases (199 total).
- **Turning casual mentions into record updates**, with MIA proposing
  and you confirming (the same "propose, you confirm" pattern Discovery
  uses).
- **The live model's behavior**, until you run the check below.

## Run the live check (on your computer)

```bash
cd ~/path/to/MIA && git pull
source .venv/bin/activate
python tests/live_model_check.py
```

Ollama must be running. It uses a temporary copy of fake data, never
your real data, and never executes the tools it's testing. It prints
PASS/FAIL per case and a total; send Claude the FAIL lines.
