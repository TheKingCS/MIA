---
id: K-0208
kind: implementation
title: The Browser page explains teaching a task before asking for one
status: confirmed
by: claude
created: 2026-11-10T14:27:59+00:00
concerns: web/browser.js, web/concept.css
from: dec:DEC-0117, file:web/browser.js
---
Zac opened the Browser page and found no way to know how teaching a task works: the section was a bare list with a name box. The page (web/browser.js) now opens that section, Teach Her A Task, with what a taught task is and the steps in order (TEACH_STEPS: start teaching and name it, do the task yourself in her window while she watches, stop, then run it by name or by asking), and says what stays true while it runs: anything that submits, buys, sends, signs in or deletes still waits for a person's OK, she never types a password or a card number, and a taught task stops when the site has changed rather than guessing (DEC-0117). The words are in the page because they describe the screen; nothing about what a step is allowed to do moved out of core/browser_safety.py. Styles are .teach-steps in web/concept.css, tokens only. A screen that only makes sense after a conversation with her is a gap: every page says what its feature is for and how to start, in the page.
