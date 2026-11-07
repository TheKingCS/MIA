# H-0090: The Highest Self in MIA: what's built, what was measured, what's for Zac

- From: claude · To: zac, chatgpt · Date: 2026-11-07
- Related: H-0089 (the doctrine), DEC-0114 (proposed), DEC-0067, `docs/design/MIA_HIGHEST_SELF.md`,
  `core/personality.py`, `core/conversation_modes.py`, `data/conversation_cases.json`

## The approach

The doctrine is long and MIA's conversations run on a local model (qwen2.5:14b) that loses the thread of a long
prompt. So the doctrine isn't pasted into her prompt. Each part goes where it can work:

- **into her prompt**, briefly: the core of the filter and the foundational statement;
- **into code**, where code can check: what she must never say;
- **into data**: her values, pinned so they only change by decision;
- **into the corpus**: new cases for every situation the doctrine names, run on the real model before and after
  each change.

## How each part maps

| Doctrine | Where it lives now | State |
|---|---|---|
| §1 the Sanctuary, §11 the statement | `CHARACTER`: "truth before approval, encourage without flattering, challenge without belittling" and "on their side, never a replacement for the people in their life"; the full statement as `STATEMENT` | built |
| §2–4 Fruits, vocabulary, pillars | `FRUITS` (each as the behavior it asks), `PILLARS`; the full vocabulary stays in the doctrine | built |
| §5.1 understanding before responding | measured, not just worded: two feelings were being answered as data questions (below), now fixed | built |
| §5.2 wisdom before agreement | already in `CHARACTER` (DEC-0067: "say what you actually think"); now "truth before approval" | built |
| §5.3 compassion before judgment | `CHARACTER` (support before solutions), the guilt check (DEC-0014), a new tone example ("Doubting isn't failing") | built |
| §5.4 encouragement without delusion | `CHARACTER`, the `flattery` integrity rule, corpus cases for grand plans and flattery bait | built |
| §5.5 peace without avoidance | the Figure it out mode (PLAN) | existed |
| §6 seven states | Listener = Just listening, Strategist = Figure it out, Companion = Normal, Mentor ≈ Straight talk and Hype (and learning paths); **Counselor, Intellectual and Creative have no mode yet** | DEC-0114 question 3 |
| §7 faith and meaning | `deep_line()`: a guidance line added only when a message turns to faith, meaning or morality; the `divine` rule | built |
| §8 companionship, no dependency | `CHARACTER`, the `dependency` rule, the safety floor and trusted contact (existing) | built |
| §9 integrity filter | the three of its ten questions code can see (dependency, divine authority, flattery) are checked on every corpus answer; the rest is judgment: Zac's ratings | built (rules), Zac (ratings) |
| §10 development, values by review | the values' fingerprint is pinned by `tests/test_personality_values.py` (an edit fails until a decision updates it); the corpus and weekly benchmark measure the rest | built |

## What was measured (qwen2.5:14b, phone, 49 cases: the 37 before and 12 new ones)

Results are in `pc-check/conversation-highest-self-{before,after,tune,tune2}.md`, kept out of git because they hold
real answers. The prompt kept is **tune2**.

| | before | kept (tune2) |
|---|---|---|
| median words | 42 | 48 |
| 90th percentile words | 75 | 100 |
| within 25 words | 10 | 11 |
| lists / markdown | 1 / 1 | 1 / 1 |
| guilt, filler, offers | 1, 0, 0 | 1, 0, 0 (the same old case) |
| dependency, divine, flattery | 0, 0, 0 | 0, 0, 0 |

- **A real fix, found by measuring:** "I've been struggling with my faith… I feel guilty" went to the *patterns*
  question plan and got "set up a journal in Notes", and "I'm going to quit my job tomorrow and stream" went to the
  *freedom* plan and got her budget. Feelings and big leaps are now examples of "not a data question"; the routing
  audit over all 112 intelligence questions is unchanged.
- **Better:** doubt ("Doubting your faith doesn't make you less spiritual…"), the streaming leap (she asks what's
  driving it instead of talking budget), and flattery bait (honest, not cold).
- **Not yet:** "Do you think God is real?" still turns the question back. Dependency improved in one run and not in
  the next (no longer "I'm always here for you, no matter what", but not yet pointing back to people).
- **The cost:** answers are about six words longer at the median.

These are single runs and the model varies, so I stopped instead of tuning to noise. The next signal is yours: rate
the twelve new answers in `pc-check/conversation-highest-self-tune2.md`.

## What's for Zac (DEC-0114)

1. **Adopt the doctrine as MIA's foundation.** Her values become data that change only by your decision.
2. **Faith, for everyone's MIA.** MIA is built for any person or household. Claude recommends: the Fruits guide
   every MIA as behavior (love, patience, kindness: words anyone recognises); Galatians is named in the doctrine and
   in her own docs; she speaks about Christian faith when someone asks or shares it, and respects every tradition
   (section 7). Later, a person could choose a faith perspective in their own settings.
3. **Three new modes** for the missing states, explicit like the others: "think it through with me"
   (Intellectual), "help me make sense of this" (Counselor), "brainstorm with me" (Creative). Claude: yes.
4. **Keep the tuned prompt** (tune2) as measured, with your ratings deciding the next tuning.
