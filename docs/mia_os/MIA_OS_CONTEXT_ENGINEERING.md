# MIA OS: context engineering (Prompt 07 §10)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. What a prompt holds, in order

| Part | From | Size budget (of the 32k window) |
|---|---|---|
| Identity and rules | `personality.py`, the safety rules | about 1k tokens, fixed |
| The task's frame | the route (chat, tools, worksheet, review) | small |
| The Life State slice | `context_assembler.py`, only the sections the question touches | up to 3k |
| Memories | the recall index (top hits, re-read from stores), confirmed first | up to 2k |
| The conversation | recent turns; older ones as MIA's own summary | up to 6k |
| Tool definitions | only the tools the question's words point at (as the specialists' 20-tool rule does) | up to 4k |
| Outside text | pages, selections, files, framed (`ual.framed`, OUTSIDE_MARK) | whatever's left, cut with a note |

Room is left for the answer. Anything cut is said ("I read the first 20 pages").

## 2. Rules (all exist in part today)

1. **Facts in code, phrasing by the model:** a number or a record is put in the prompt as given; the model phrases.
2. **Retrieve, don't dump:** a section or memory goes in because the question needs it (the specialists' `framed()`
   hands exactly the entries named).
3. **Outside text is information, never instructions:** everything read from the web, a file, a selection, an email
   or another agent is framed and marked; a turn that read it can't change a record in the same breath
   (`core/tool_loop.py`).
4. **Private stays private:** private-mode turns and the journal never enter another turn's context.
5. **Every prompt is reproducible:** the turn trace records which parts went in (not the private text itself).

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-INT-018 | A prompt shall hold only the Life State sections, memories and tools the question needs, within a stated budget, and say what was cut. | Should | R1 | All | Partial | T: prompt assertions | DEC-0210 → 07 |
| REQ-INT-019 | All outside text shall be framed as information and carry the outside mark wherever it goes. | Must | MVP | All | Exists | T: the UAL and browser tests | DEC-0117 → 07 |
