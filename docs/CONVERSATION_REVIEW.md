# How MIA talks: what was there, what was wrong, what changed

*Claude, 2026-11-10. The findings and the build for Zac's specification `docs/specs/CONVERSATION.md` (its section
12 asks for this before and beside the work). Every answer quoted here is from the real model on the PC
(qwen2.5:14b), asked the specification's own test questions before the work and again after it. Nothing in it is a
decision: where it proposes, Zac decides.*

## The short version

Most of what was wrong had one cause. A question about MIA herself ("do you have a greenhouse app?", "what is the
Chronicle?", "how do you work with my glasses?") was handled as a help question, and the help search handed the
model whichever help pages shared a word with it. The model read those pages back as her own abilities. She had
the true records all along (her app registry, her decisions, her commit history, her own files); they were only
reached when a narrow pattern matched.

So the main change is not a new memory or a new description of her. It is `core/self_knowledge.py` reading the
records that already exist, at the moment she is asked, and handing the model those lines with where each came
from. The rest is smaller: a few rules in how she is asked to answer, a wider filter for closing lines she adds by
habit, and the chat page.

## 1. What was already there

| What the specification asks for | What MIA already had |
|---|---|
| Knowing her own apps | The app registry (`core/capabilities.py`: `capability_map`, and `capability_status` with five states: implemented, partial, planned, unavailable here, malfunctioning), built from the modules, tools and parity record, not written by hand |
| Knowing her own documents and decisions | `core/self_docs.py` (the `get_mia_docs` tool), reading `docs/` and `docs/DECISIONS.md` |
| Knowing her history | `core/dev_history.py` and `core/dev_evolution.py`: every commit, decision and task, counted |
| Knowing what she runs on | `core/service_map.py`: each outside service and whether it is set up, checked live |
| Saying who she is | `core/self_knowledge.py` `about_me()` and `grounding_block()` (DEC-0142), given only for a how-to question |
| Keeping to the subject | A bounded history of the conversation sent with every question; "yes" to an offer acts (`core/conversation_state.py`); memories chosen by relevance; notes offered and kept only on "keep it" (DEC-0054) |
| Feedback | 👍/👎 on every answer (`core/answer_ratings.py`, action `answer.rate`), the failure log and Fix-It Log (`core/failure_log.py`, DEC-0049), one trace line per turn (`core/turn_trace.py`, DEC-0067), and two-ways answers to choose a style (DEC-0138) |
| Safety net on wording | `core/response_composer.py` `polish()`: strips a stock opener or closer from a model reply |

Nothing in that table was missing. What was missing was the join between a question about her and those records.

## 2. What was wrong, with the evidence

Asked before any change (same questions as the specification's section 13):

| Asked | What she said | What is true |
|---|---|---|
| Do you have a greenhouse app? | "I don't have a separate greenhouse app" | She has one |
| Tell me about your greenhouse application. | Five features in bold: "Climate Control", "Irrigation Scheduler", "Aquaponics Cell Control"... (113 words) | Those are module names from the Homestead node's help pages, not things her app does. Her app shows the greenhouse's upkeep, and watches a node once told to take over |
| How do you improve greenhouse yields? | Seven numbered steps naming seven "modules" (222 words) | Same source. None are hers to offer |
| When did your development begin? | "I don't have specific information... check with the developers" | Her own history has the first commit, 10 July 2026 |
| What is the Chronicle? | "a digital journal where you can record... maintenance tasks, plant growth" | Invented. There are two things by that name, both in her code |
| How do you work with my glasses? | "I don't have specific features to work directly with glasses" then an offer to track eye appointments | She has a glasses app, a voice path and a camera path |
| What are your current limitations? | Not controlling glasses; not managing prescriptions | Carried over from her own wrong answer one turn earlier |
| What's the population of Montana? | "I can fetch it for you. Would you like me to look it up online?" | She has no way to look it up online |
| What did we decide about eggs? | "I don't have any decisions... about eggs recorded" | DEC-0037 is about eggs |
| Summarize this conversation | A numbered list ending "Is there anything else you'd like to discuss?" | Fine, but read from the model's short window, not the whole |

The patterns behind them:

1. **The wrong reference material.** Covered above. It caused the invented greenhouse features, the invented
   Chronicle and the "no glasses" answer.
2. **No records unless a pattern matched.** "When did your development begin" and "how were you created" reached
   the model with nothing about her.
3. **Third person and distance.** "The developers", "MIA doesn't have", "Closest match in MIA".
4. **Closers by habit.** 17 of the 21 answers the model wrote ended on a question, most of them an invitation to
   keep talking ("Would you like to know more?", "Do you need any tips?").
5. **Length by habit.** Lists and bold headings for questions that wanted two sentences.
6. **An offer she could not keep** (looking something up online).
7. **Her own earlier mistake repeated** as a fact a turn later.

## 3. What changed

**Her own records, read when she is asked** (`core/self_knowledge.py`). A list of topics (her history, her limits,
her direction, how she is built, how she learns, her memory, the glasses, the Chronicle, devices, the greenhouse).
Each names the files, decisions, apps and live checks that answer it; a test fails if any of those stops existing.
`block_for()` turns a question into lines like `[app registry, partial] Greenhouse: ...`, `[decision DEC-0049,
approved] ...`, `[my history, counted now] ...`, `[what I run on, checked now] ...`. Nothing in it is a second
description of her kept by hand: a file's line is that file's own opening, a decision's line is read from the
decision record, an app's line is the registry row and its state. One sentence is hand-kept, and a test pins it:
"Nothing of mine searches the network for devices" (true of the code as of 2026-11-10; if a scan of the network is
ever built, that sentence and its test change with it).

**A question about her no longer gets the help pages** (`core/assistant_chat.py`). Her records go in instead, and
the last line the model reads asks for first person, a few plain sentences, only what the records show.

**Describing something she has is told from looking a record up.** "Do you have a greenhouse app?" is answered in
conversation from the registry; "what is the greenhouse temperature?" still goes to the tool.

**Rules in how she is asked to answer** (the system prompt, a few sentences): first person about herself; only
what her records show, and saying she doesn't know yet is fine; for facts about the world, answer from what she
knows and say when she's unsure or it may have changed, never a made-up source or number; answer first at the
length the question deserves; don't repeat herself or their words; go with a change of subject; ask a question
only when she wants the answer. Her character lines were not touched.

**The closer filter is wider** (`core/response_composer.py`): "Would you like to know more...", "If you have any
questions..." go. An offer to *do* something ("Want me to open it?") stays, because "yes" to it acts.

**"What did we decide"** with nothing kept between her and the person now also looks in her own decision record
and says whose it is (`core/question_plans.py`).

**The greenhouse node's module list** is only given when the question is about the node's modules
(`core/greenhouse_link.py`); a general greenhouse question gets her own part and the line that the node's features
are not hers to offer.

**Wording in code** that spoke of her from outside is first person ("The closest thing I have").

**Devices** (added last): where the storage check cannot run (it uses `lsblk`, which Windows doesn't have) she now
says she only finds serial boards on this computer.

Not changed: the model, how it is loaded or benchmarked, and the wording of the action-request prompt.

## 4. The same questions afterwards

Last run 2026-11-10, same model.

| # | The specification's test | Now | Verdict |
|---|---|---|---|
| 1 | Greenhouse app | "Yes, I have the Greenhouse app... readings from the sensors once I'm connected to the greenhouse node." (41 words) | Passes |
| 2 | Devices she can discover | Says she doesn't search the network; offers the port scan of an address she's given; names what's plugged in | Passes on substance. The wording is still clumsy ("I can discover... but I don't actively search") |
| 3 | How she improves yields | 72 words, no invented modules; general upkeep advice tied to her Greenhouse app | Partly. She has no yield procedure of her own and should say that in one sentence before the advice. See 5.1 |
| 4 | Her creation | First commit 10 July 2026, counts of commits and decisions, from her history | Passes |
| 5 | The Chronicle | Names both things called that, from their files | Passes |
| 6 | Glasses | Describes the web app on the display, the phone doing the work, tap to talk, the camera for "what am I looking at" | Passes from the code. Zac should check it against the glasses in his hand |
| 7 | A factual question | "about 1 million, last I knew" (Montana); Canberra; the 1987 World Series, right | Passes within the model's limits. See 5.2 |
| 8 | A simple question | "The capital of Australia is Canberra." | Passes |
| 9 | Continue a discussion | Smokehouse, then wood, then brisket: each builds on the last without restating it | Passes |
| 10 | Change topics | Goes with it | Passes |
| 11 | Conversation summary | Reads the whole conversation, under Topics / Decided / Still open / To do | Passes. See section 6 |
| 12 | About herself | First person throughout | Passes |
| 13 | Export a conversation | Built | Passes. See section 6 |
| 14 | Copy a summary | Built | Passes. See section 6 |

Answers ending on a question: 17 of 21 before, 1 of 20 after, and that one is a real question about the subject
(which kind of smoker). The median length of a model answer fell from 75 words to 45, and the whole run from 1,590
words to 961, with more in it that is true.

## 5. What is still not right

Said plainly so nobody assumes otherwise.

1. **Yields.** She gives sensible general advice and no longer invents features, but doesn't open with "I don't
   have a yield procedure of my own yet". The greenhouse topic gives her that fact; the model doesn't always lead
   with it. Fix proposed: a code-written first sentence for "how do you improve/optimise X" when the registry has
   no tool for it.
2. **Facts about the world come from a 14B local model with no reference library behind it.** She now hedges a
   changing figure and no longer offers to look online. She can still be confidently wrong on an obscure fact.
   "Confidence earned by evidence" for world facts needs evidence she can read: her offline reference
   (`core/reference_library_manager.py`) is the place, and routing a factual question through it first is the proposal. Not built.
3. **"What can you do?" (272 words) and "Who are you?" (168 words)** are written by code, not the model, and were
   left alone because they are deliberate. They are long for a spoken answer. Proposal: a two-sentence
   spoken form with the full one on the screen.
4. **Limits.** Her answer names what isn't set up, from the live check, but the model sometimes muddles two lines
   into one ("the greenhouse node or PlatformIO" as devices).
5. **Direction** ("what are we working toward") is read from her standing nightly instruction and the latest
   decisions on record. It is as accurate as those are current, and says nothing of what Zac has in mind but
   hasn't written down.
6. **A summary is the model's reading**; the export is the exact record. The page says so.
7. **The chat page opens on a greeting**, not on the conversation in progress. Picking up is one tap (History).
8. **On a phone linked to the computer**, Save to Files for the computer's current conversation doesn't find it
   (the action runs on the phone's own store). Copy works.

## 6. The chat page (specification section 11)

- **Width.** The conversation uses the page; a single message stops at 1100px so lines stay readable. Checked at
  1760, 1280 and 390 pixels.
- **Copy** on every one of her answers, in the chat page and the floating Talk panel (`MIAShell.copyButton`). It
  copies the whole message as written, and reads "Copied ✓". Checked in a browser and in the desktop window.
- **Export** (`core/conversation_export.py`): Markdown or JSON, every kept message in order with who said it and
  when. On screen: Copy, or Save to Files (action `conversation.export`, into a Conversations folder, never over
  an earlier export). By voice or typing: "export this chat as JSON". A file download was not used because neither
  the desktop window nor the phone can take one.
- **Summary**: the whole conversation is read (a long one in parts, each part summarised, then one summary from
  all of them, so the start counts as much as the end), under four headings, with Copy Summary. Asked in talk
  ("summarize this conversation"), the request itself is left out of what's summarised. With no model running she
  says so and lists what was asked, in order.
- A message said in private is never in an export, a summary, the history list or a picked-up conversation.

## 7. Feedback and getting better (specification section 10)

The cycle the specification draws, against what exists:

| Step | Exists as |
|---|---|
| Experience | Every turn leaves a trace line: the route taken, tools offered and called, time (`core/turn_trace.py`) |
| Feedback | 👍/👎 on an answer with what was asked and said (`core/answer_ratings.py`); "that's not right" files the turn in the failure log; two-ways answers record which style was picked |
| Analysis | The Fix-It Log groups failures; the ratings and trace loops in `core/loops.py` watch the counts |
| Reflection, proposed improvement | Done by whoever works the Fix-It Log (a person or a build session). MIA does not write her own proposal from a 👎 yet |
| Testing, validation | The scripted-model harness (`tests/test_turn_harness.py`) and the real-model check; a change to how she answers goes in with a test |
| Integration | A commit, recorded in her history, which she can then read |

The gap is the middle: turning a pattern in the ratings into a written proposal. That is the natural next piece
and it fits the existing proposal path (`core/actions.py`: propose, a person approves). It is not built here.

What must stay true, and does: a 👎 changes nothing about her character or her prompt by itself. Style only
moves through the two-ways choice the person makes, and anything else is a change a person approves.

## 8. Proposed next, for Zac to choose

1. A code-written first sentence when she's asked how she does something she has no tool for (5.1).
2. Facts about the world through her offline reference first (5.2).
3. Short spoken forms of "what can you do" and "who are you" (5.3).
4. The chat page opening on the conversation in progress (5.7).
5. Her own written proposal from a pattern of 👎 (section 7).

## 9. Running the check again

The specification's questions are a script outside the repository (it needs the real model and a couple of
minutes). The lasting checks are in the suite: `tests/test_self_knowledge.py` (every topic points at things that
exist; what counts as a question about her), `tests/test_turn_harness.py` (a question about her reaches the model
with her records and no help pages; summary and export by asking), `tests/test_response_composer.py` (closers),
`tests/test_conversation_export.py`.
