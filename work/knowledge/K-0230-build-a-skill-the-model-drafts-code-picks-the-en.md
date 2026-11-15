---
id: K-0230
kind: implementation
title: Build A Skill: the model drafts, code picks the ending, a person approves
status: confirmed
by: claude
created: 2026-11-15T11:33:05+00:00
concerns: core/ual.py, core/path_actions.py, web/shell.js, web/selection.js
from: dec:DEC-0165, dec:DEC-0167, dec:DEC-0112
---
What: core/ual.py _build_skill (PREPARE). The model gets the selection framed, plus only the tools the registry's own matching_actions() picks for the selection's words (at most SKILL_TOOLS = 20, without the taught_skills and ual domains), and replies with JSON {name, steps, missing}. Code parses the steps with taught_skills.parse_steps, checks them with step_problems, and refuses any tool that wasn't in the offered list (so a real but unrelated tool can't be slipped in). Steps that hold and use at least one tool -> result.follow = taught_skill.add ("Teach It To MIA"); anything else, or a non-empty missing -> result.follow = lab.propose ("Build It In The Lab"), with the selection as evidence.

Why a `follow` instead of an act action: whether the skill is teachable is only known after the model drafts it, and an act action's kind is fixed in the catalogue. A prepare result naming one follow-up {kind, label, params} keeps the tier rule (prepare changes nothing) and the contract (the follow is proposed only when pressed, then approved). The kind is chosen in code from two fixed options, never by the model.

Learn This Myself became ACT with a new kind path.draft (core/path_actions.py), because paths.draft() keeps the draft in the person's store: a write, so a proposal with undo. It names an existing program instead of drafting when find_program matches. Not child_ok (DEC-0119: new work needn't design for children), which the child-actions test enforces.

Known limit: paths.draft uses its own _ollama call to qwen2.5:14b on the PC, so on the phone the draft fails with its plain message.
