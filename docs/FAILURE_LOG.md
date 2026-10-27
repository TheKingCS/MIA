# The Fix-It Log: how MIA gets better without breaking

*Zac, 2026-10-27 (DEC-0049): "a log that you can be sent to audit the
users interactions with MIA, see when she fails, why she fails, when the
user runs into an issue and then use that information to fix her ...
nearly self developing in a way that doesnt break her."*

## What's recorded (`core/failure_log.py`)

Each person's own `failures.jsonl` (their folder under `data/`, never
the repo; it syncs phone ↔ PC line by line). Never an off-the-record,
journal or private turn; words are redacted (no emails, long numbers or
anything after "password").

| Kind | When |
|---|---|
| report | "MIA, report a problem: …" (answered right away), or Report A Problem on the page |
| said_wrong | "no, I meant…", "that's wrong", "not what I asked" |
| thumbs_down | 👎 under a reply in Talk (with what was wrong, optional) |
| tool_error | a tool raised (core/assistant_actions.execute) |
| model_down / garbled | no answer from the model, or a tool call written as text |
| no_tool | a command-sounding request no tool matched |
| talked_instead | the right tool was offered but the model only talked |
| rephrased | the same thing asked again in other words within 2 minutes |
| undo_soon | "undo" within 3 minutes of her answer |
| slow | an answer over 25 seconds |
| page_error | a web page threw an error (web/shell.js reports it) |

Events group into **issues** (by tool, page or kind), ranked by weight,
then recency. A fixed issue that happens again opens again by itself.

## The three tiers

1. **She learns herself, only after a yes.** After a failed attempt and
   a successful retry: "Want me to remember that “got off work” means
   this?". Or taught outright: "when I say clocked off, I mean log my
   shift". Kept per person in `failure_state.json` (undoable); routing
   attaches that tool when the words are said, and the model is told
   what they mean.
2. **She asks before changing settings.** (For now, these show up as
   issues; automatic proposals come later.)
3. **She never changes her own code.** The fix report (Apps → Fix-It
   Log, and `fix_report.md` in the person's folder once a day) lists the
   open issues with examples and **the test to write first**. Claude, on
   the PC: read it, turn each issue into a failing test (routing cases in
   `tests/test_assistant_routing.py`, bench cases in
   `data/model_bench_cases.json`), fix, run the full suite and the
   live-model bench, Zac approves, mark the issue fixed. The tests stay,
   so the same failure can't quietly come back.
