# Trade Master: proposal (DEC-0149, proposed)

Zac, 2026-11-08: "just like Homesteading is Construction. I want her to be able to organize missions and walk me
through step by step of any home construction, repair, or diagnosis jobs with industry standard professional steps
so nothing is missed and be able to reason about it all and have intelligent conversation about the process. This
same idea should be implemented for many other processes. She should become a Trade master and be able to teach an
entry level Apprentice: Carpentry, Plumbing, HVAC, Electrical, Appliances, Siding, Roofing, all of it and more."

Nothing is built yet. This is what exists, what's missing, and a first version to approve.

## 1. What MIA already has

| Needed | Already in MIA |
|---|---|
| Sourced trade knowledge | **The Construction specialist** (`core/specialists.py`, DEC-0109, `docs/specialists/construction.md`): notes Night School writes with their sources (IRC sections, ACI, OSHA), marked unconfirmed until someone checks them, with a rule that work a code or licence requires is named as such. Its first notes: sizing a header, when a project needs a permit, mixing and curing concrete. |
| Building things, with real numbers | **The plans shelf** (`core/plan_library.py`, DEC-0118: 15 sized plans), **the calculators** (`core/build_calcs.py`: quantities and cuts in code, never the model), **workshop recipes** (`core/craft_recipes.py`), and the Woodworking Studio proposal (DEC-0147: designs made of real parts). |
| Teaching a skill in stages | **Learning paths** (`core/paths.py`, DEC-0112, guitar as the first, `core/guitar.py`): understand the goal, plan stages, teach lessons, log practice, homework missions, verify by evidence, next stage. |
| Step by step, by voice | **Cooking and training sessions** (`core/cooking_session.py`, `core/training_session.py`): one step at a time, "next", "repeat". |
| Jobs as missions | **Missions** with objectives (`core/mission_manager.py`), **projects and tasks**, **maintenance** tasks per asset and property. |
| Looking at the work | **Sight** (`core/sight.py`): "how is this built?" from a photo, on the local vision model. |
| Reference books | The offline **reference library** packs. |

## 2. What's missing

1. **A professional job procedure.** For each job: its scope, when to stop and call a professional, permits
   and inspections, hazards and PPE, tools, materials (quantities from the calculators), and the phases and
   steps, each with *why*, *what to watch for* and the trade's checks. Above all **hold points**: places you
   don't go past until something is verified (power proven dead, a pressure test held, the layout checked
   square). That's how nothing gets missed.
2. **Diagnosis.** A symptom ("no hot water", "the breaker keeps tripping", "the AC runs but doesn't cool",
   "the toilet keeps running", "the dryer doesn't heat") becomes ordered checks, cheapest and safest first,
   each answer narrowing the cause, ending in a fix job or "call a pro, and here's what to tell them".
3. **An apprentice program per trade.** Stages like a real apprenticeship: safety, tools, materials and
   terms, basic techniques, then real jobs. Lessons come from the job procedures, checks are quizzes and practice
   jobs done, and the evidence is logged. It teaches; it never claims a licence or certification.
4. **Conversation grounded in all of it.** Questions in the middle of a job ("why do the joists crown up?", "can
   I use PEX here?") answered from the job's own steps, the specialist's sourced notes and the library, never
   made up by the small model.

## 3. Proposed first version

All of it is one structure, so every trade (and later any process: auto, small engines, welding, the homestead)
uses it the same way.

- **`core/trades.py`: jobs and diagnoses as data**, each step written once and reviewed, never generated on the
  fly. A job is: trade, name, scope, `stop_if` (in code, never overridden by the model: gas smell, an
  unprovable dead circuit, structural doubt, asbestos or lead in a pre-1980 house, work at height without fall
  protection, licensed work where the law requires a licence), permit and inspection notes ("check your local
  building department"), hazards and PPE, tools, materials (linked to `core/build_calcs.py` where there's a
  calculator), then phases of steps with why, watch-for, common mistakes and **hold points**. Every job carries
  its sources and a status, *drafted* until someone checks it.
- **A job session** (a third session kind beside cooking and training): one step at a time by voice or on the
  screen, "next", "why?", "what could go wrong?", "back". A hold point waits for your "checked" (and later a photo
  check through Sight). Stop rules end the session with what to do instead.
- **A job becomes a mission:** its phases as objectives, its materials onto the shopping list, and it can be
  tied to the house, a room or an asset, so maintenance and the history know about it.
- **Diagnosis sessions:** the same session runs a diagnosis tree, saying why each check comes next.
- **Apprentice programs:** one learning path per trade (`core/paths.py` Programs, like guitar), starting with
  Carpentry: stage 1 safety, tools and measuring; stage 2 layout and cutting; stage 3 framing basics. Lessons are
  drawn from the jobs, and checks are counted or said.
- **One specialist per trade** (DEC-0109) so Night School studies each: Carpentry and framing, Plumbing,
  Electrical, HVAC, Appliances, and Exterior (roofing, siding, windows). Today's Construction specialist stays as
  the general one.

**First content (proposed):** about 10 jobs and 6 diagnoses across the trades. For example:
- Jobs: frame a non-bearing wall; replace a toilet's fill valve; replace a faucet; replace a light switch or
  outlet; replace a furnace filter and clean the condensate line; replace a dryer heating element; patch
  drywall; replace damaged siding boards; fix a shingle leak; build a deck stair.
- Diagnoses: a running toilet, a tripping breaker, no hot water, the AC not cooling, the dryer not heating, a roof
  leak.
- Programs: Carpentry stages 1-3.

After that, the list grows by trade and by what your house and homestead actually need.

## 4. Safety (never the model's call)

- Stop rules live in code, and a job that hits one stops, whatever the conversation says.
- **Electrical:** prove it dead before touching (test the tester, test the circuit, test the tester again).
  Panel and service work is named as licensed work where the law requires it.
- **Gas:** smell gas, leave and call the utility from outside. Gas piping is named as licensed work where the
  law requires it.
- **Structure:** bearing walls, beams and footings get the specialist's "get an engineer when..." rules and a
  permit note.
- **Old houses:** asbestos and lead checks before cutting or sanding in pre-1980 homes.
- **Roofing:** fall protection; never alone on a roof.
- Codes vary by place, so every code reference says to check the local building department. MIA guides; it
  never certifies, and nothing is called up to code unless an inspector passed it.

## 5. Questions for Zac

1. **Approve the direction and the first version** (section 3)? Recommended: yes.
2. **Which jobs first?** Recommended: the ones your house and homestead need soon (the greenhouse, the coop, a
   shed, repairs you know are coming), plus the starter set above. Tell Claude your list, or let MIA build it
   from your maintenance tasks and plans.
3. **Licensed work.** For panel and service work, gas piping and the like: (a) teach it fully but never walk you
   through doing it; (b) walk you through it where your state lets a homeowner do it under a permit, with the
   stop rules; (c) leave it out. Recommended: (b), with the permit and inspection steps built in.
4. **Who checks the content.** Each job is drafted from published standards and manufacturers' instructions,
   with sources, and marked unconfirmed. Options: (a) you confirm each one as you use it; (b) a licensed
   tradesperson you know reviews electrical, gas and structural ones; (c) both. Recommended: (c) for electrical,
   gas and structural, (a) for the rest.
5. **Specialists:** one per trade, as above? Recommended: yes.

## 6. Risks

- **Wrong steps.** Mitigated by written-once, sourced, reviewed procedures (the model never invents a step) and
  the drafted/confirmed status shown on every job.
- **Codes differ by place.** Every code note says so and points to the local building department; nothing
  presents itself as a code ruling.
- **Scale.** "All of it" is hundreds of jobs. The structure is built once; content grows by trade, with Night
  School drafting and people confirming.
- **The small model.** Facts are assembled in code from the job, the notes and the library; the model only
  phrases them and answers within them.
