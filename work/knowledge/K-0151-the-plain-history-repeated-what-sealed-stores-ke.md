---
id: K-0151
kind: security-finding
title: The plain history repeated what sealed stores keep; now each line is sealed as appended
status: confirmed
by: claude
created: 2026-11-08T21:34:35+00:00
concerns: core/at_rest.py, core/life_events.py, core/your_data.py, core/sync.py, tests/test_at_rest.py, tests/test_life_events.py
from: dec:DEC-0126
---
DEC-0126, 2026-11-08. A scan of every core file naming a SEALED file for life-event calls found nearly every sealed store writing its records' names into the plain life_events.jsonl: on_change's default names the record ('Added a person: Sam'), and many record() calls format titles in. So the people, places, policies, goals and journal titles sealed in their own files were in clear text in the history. Fix without breaking 'never rewrite it': at_rest.LINE_SEALED (life_events.jsonl, every folder: the household's log too), seal_line() before each append, open_text() opening line by line for these names (open_lines: plain lines from before read as they are; a line that won't open stays as it is and the reader skips it, never the whole history), open_bytes() noticing a sealed line anywhere (the first line may be plain), and seal_text() sealing line by line when a sync merge is written back. Cost measured: 2,247 lines open in ~5 ms. Checked on the real logs read-only: both open identically. Residual: lines before today stay plain until a one-time rewrite with MIA closed (Zac's call, WAITING_ON). Any reader of the history, tests included, must use at_rest.open_text: six tests read it raw and broke.
