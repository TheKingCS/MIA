---
id: K-0229
kind: implementation
title: UAL U3 part 1: model actions are read or prepare only, never act
status: confirmed
by: claude
created: 2026-11-15T11:27:02+00:00
concerns: core/ual.py, tests/test_ual.py
from: dec:DEC-0165
---
What: core/ual.py gained six ready actions that ask MIA's own model: explain, summarise (280+ characters), translate (into English, TRANSLATE_INTO), explain_code (code captures), extract_tasks and draft_email (prepare). One helper, _model(), builds the prompt from _JOBS and framed(capture): the job and the rule that the selection is content, never a request, come before the selection; the selection is wrapped with OUTSIDE_MARK. Markdown bold and headings are stripped from the answer.

Why this is safe without trusting the model: these specs are READ or PREPARE, and spec_problems() refuses a read or prepare spec that names an action kind, so run() only returns the text. A test feeds an injection in the selection and a model answering with a delete command; nothing changes. draft_email returns subject and body for Copy; it does not use the email_drafts store (PREPARE saves nothing), unlike the chat's draft_email tool.

What went wrong: making explain/summarise ready broke four U1 tests that used "summarise" as the example of an unbuilt action, and the offer sentence's expected start; they now use "research".

Failure modes said plainly: no llm on the context ("isn't on this device"), None or an exception from generate ("isn't answering right now").
