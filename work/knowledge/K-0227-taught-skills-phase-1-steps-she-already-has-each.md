---
id: K-0227
kind: implementation
title: Taught skills, phase 1: steps she already has, each through its own gate
status: confirmed
by: claude
created: 2026-11-15T10:42:06+00:00
concerns: core/taught_skills.py, core/taught_skill_actions.py, core/assistant_taught_skill_actions.py, core/web_taught_skills.py, core/actions.py, core/assistant_actions.py, core/assistant_turn.py, web/taught-skills.js
from: dec:DEC-0123, dec:DEC-0167
---
What: core/taught_skills.py (DEC-0123, part of DEC-0167). A taught skill is ordered steps of five kinds: tool (an assistant tool and its arguments), action (an action kind and its params), ask (the answer gets a name, used later as {name}), you (she waits for "done"), tell. Taught by "watch me: <name>" (hooks note each tool the registry runs and each action the person approves, until "that's it") or by writing the steps as lines (parse_steps / format_steps round-trip). The store is SkillBook (personal, sealed, taught_skills.json), which also holds what's being shown and the one run in progress, so a question can wait across turns and devices.

How it stays safe: nothing in the engine decides what's allowed. A tool step runs through AssistantActionRegistry.execute; an action step through ActionCenter.propose/approve (as "mia", so it is checked, credited and undoable). While practising, every action step and every tool that may change records waits for a yes with the action's own describe sentence. Learned after 2 clean watched runs. Always asking, learned or not: action kinds matching pay/buy/send/email/publish/delete/share/profile/browser.commit (always_asks), tools marked destructive or named that way, and, because a tool's name doesn't say what its handler does, a guard in core.actions.run_as_tool: a contextvar is set while a skill runs a tool step without a yes, and an always-ask kind reached inside it is refused, the run asks, and the step reruns on yes.

Why that way: Zac asked for skills beyond what she already does, but approval must stay with a person. Composing existing gated capabilities gives new behaviour without a new way to act. The guard exists because 60+ tools call run_as_tool with kinds their names don't reveal.

What went wrong: (1) the run tool's own undo record would have made "undo that" restore the skill book instead of the step; run-state writes now go through outside_undo. (2) A tool that proposes and approves an action was noted twice while watching; mark() before the tool and truncating in observe_tool keeps the tool only. (3) A delete step whose record was gone asked for a yes to something impossible; an action that can't be described now fails the run before asking. (4) A run only takes a chat message as its answer when her last message was its question, so a person who moved on isn't held.

Not built: triggers, browser/phone/desktop steps, unattended runs (start(watched=False) exists and refuses unlearned skills, but nothing calls it), her offering after a repeat.
