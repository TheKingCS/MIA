# H-0101: Projects and Missions, Zac's concept: the data is in, the look is yours

- From: claude → To: muse (cc zac)
- Date: 2026-11-09
- Concept: `docs/design/assets/concepts/projects_and_missions.png` (Zac: "I like how the cards are organized and what
  data is present here")
- Decision: DEC-0152 (Projects and Missions connected, from Zac's architecture handoff)

## What the engine now gives each screen

**Projects (left of the concept), `/api/projects` (core/web_projects.py):** each project card has `name`,
`description`, `status`, `due`, `progress.percent` (derived from its tasks and missions: core/mission_projects.py),
`missions` (cards: `id`, `name`, `icon`, `status`, `percent`, `done`/`total`, `next`) and its mission count.
`counts.all` and `counts.by_status` (Active, Planning, On Hold, Complete) feed the filter tabs; the concept's
"Archived" is our On Hold. A project's mission card links to `missions.html#mission=<id>`, which opens that mission.

**A mission (right of the concept), `/api/missions` (core/web_progress.py):** each mission has `summary` (the
objective line), `percent` and `done`/`total`, `difficulty`, `status`, `project` (`id`, `name`: the Associated Project
card and "Back to Project", linking `projects.html#<id>`), and `guide` when something guides it
(core/mission_guide.py): `step` of `of`, `phase`, `do` (the current step's instruction), `why`, `watch` (the Quick
Tips), `check` (a checkpoint to verify), `needs`, `steps` (the vertical step list: `n`, `title`, `done`,
`current`), `actions` (Next Step / Checked / Back / Stop, or Start) and `say` (what to ask MIA). A mission nothing
guides shows its objectives as its steps. Complete Mission is `mission.complete`; Part Of A Project is
`mission.project`.

## Not in the data yet

- A picture per project and per mission: none is kept. A project's kind could pick one from `web/img/` the way
  portal art is chosen; say what you'd want and I'll add the field.
- "Estimated time": no mission records one.
- Resources and Media tabs: a Trade Master job has tools, materials, PPE and sources (core/trades.py) that could
  fill Resources; Media waits on the pictures above.
- "Pause": the closest is Stop (a job keeps where it was and offers Start again) or Give Up For Now on any mission.

## What I built for function only

The Missions page's sheet shows the project link, the guide block (step, why, watch-fors, checkpoint, its buttons,
the step list) and a Part Of A Project button; the Projects page shows each project's missions and its percent. It's
working, not the concept's look; a full mission screen (the concept's right side, rather than a sheet) is yours to
shape, and I'll wire whatever page you lay out.
