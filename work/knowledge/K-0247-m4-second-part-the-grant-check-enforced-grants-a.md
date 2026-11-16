---
id: K-0247
kind: implementation
title: M4, second part: the grant check enforced; grants are learned skills and published workflows
status: confirmed
by: claude
created: 2026-11-16T03:40:05+00:00
concerns: core/grants.py, core/grant_actions.py, core/taught_skills.py, core/workflows.py, core/assistant_app_registry_actions.py, tests/test_grants.py
from: dec:DEC-0156, dec:DEC-0123, dec:DEC-0092
---
What: grants.require(capability, initiator, granted) raises ActionError when MIA's own initiative isn't allowed. taught_skills.guard now goes through it: inside a skill's unapproved tool step, a kind that always asks is refused (the old floor, kept), and a within-grant change is refused unless the skill is learned (held['standing'], set by _do). _needs_yes also asks for anything a manifest tiers at act_with_approval; a never tier can't be a skill's step at all (never_hers, _cannot). core/workflows.py calls require before each records.add. grants.standing(context) lists grants from where they already live (SkillBook: state learned; creations: published workflows) and take_back ends one (SkillBook.unlearn; creations.retire). grant.take_back is the action; list_grants and take_back_grant the tools; the Apps page's manage view shows the list.
Why this way: MIA already had two real standing yeses (a skill learned over two watched clean runs, DEC-0123; a workflow approved on publishing, DEC-0092). A new grants store with toggles would have been a second record of the same thing, or switches that gate nothing. So grants are a view, and the new part is the single check, the single list and the take-back. Giving a grant has no action on purpose: DEC-0156 says untrusted text can never grant, and the surest way is that nothing callable grants.
What changed in behaviour: a practising skill's tool step that looked like a read but reached a change is now held for a yes (before, only paying, sending and deleting were). Learned skills and workflows run as before.
What's left: system capabilities come with the OS prompts; network and device permissions per app aren't declared; settings that let her act alone (receipt auto-filing, World Intelligence on) aren't listed as grants.
