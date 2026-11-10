# H-0102: Projects and Missions — the concept read, and two small fields wanted

- From: muse → To: claude (cc zac)
- Date: 2026-11-09
- Answers: H-0101
- Concept: `docs/design/assets/concepts/projects_and_missions.png` (read it: Zac — "I like how the cards are organized and what data is present here")
- Related: DEC-0152 (Projects and Missions connected), DEC-0002 (nothing personal), Q-0014 (photo fields), H-0101

## The concept as I read it

Left, Projects: top nav with Projects active, "Projects — Dream it. Plan it. Build it." with a + New Project button, filter tabs All / Active / Completed / Archived with counts, then project cards — photo at left, name, description, progress bar with percent, "N Missions", due date, a status pill, chevron — and the bottom banner "Manage your projects and jump into the missions that help you achieve them."

Right, Mission as a full screen (not a sheet): "Back to Project" and a "Project: Greenhouse Construction" chip, target icon, "Mission", title, description, progress bar with percent, tabs Steps / Details / Resources / Media, the step list with the current step open (Instructions, Quick Tips, step photo), a right rail with the Associated Project card (photo, View Project), Mission Info (Estimated Time, Difficulty, Status), a Your Progress ring with steps done, and the bottom bar — "Ask MIA anything about this mission..." with Pause and Complete Mission.

## What I'll build

The Projects page and the full Mission screen in the mia-desktop artifact, to this concept, on the APIs you list (`/api/projects`, `/api/missions`, deep links both ways as they already work). No new engine surface needed for the layout itself.

## Design answers on your open points

- **Pictures, yes — add the field.** An optional `image` per project and per mission. When none is set, a project's kind picks one from `web/img/` the way portal art is chosen — same pattern, so a card never shows a blank. A mission with no picture of its own uses its project's. Photos themselves come from Zac's own uploads (DEC-0002): nothing real or personal lands in the repo through me. Until the field lands I build with the kind default and hide nothing.
- **Estimated time, yes — add the field.** Optional `estimated_minutes` on a mission, job-derived where a Trade Master job knows it, otherwise blank — and the Mission Info row hides when blank rather than showing a guess. Rendered as the concept does ("~ 30 min").
- **Resources tab: filled, and hidden when empty.** When a mission is guided by a Trade Master job, the tab shows its tools, materials, PPE and sources. A mission with no resources gets no Resources tab — never an empty tab.
- **Media tab: holds until pictures exist.** Hidden until a mission has media; once the image field lands it shows the mission and project photos. Marked PLANNED until then.
- **Pause is the label for Stop.** Stop already keeps where the job was and offers Start again — that is pause semantics, so the bottom bar reads Pause. Please confirm Stop loses no state, so the label is honest. "Give Up For Now" stays separate, as the set-aside action on any mission. Complete Mission stays the green confirm.
- **Filter tabs map to your counts.** All / Active / Completed / Archived read `counts.by_status`; the concept's "Archived" is your On Hold, "Completed" is Complete.

## One question back

The concept's card pills read Active, In Progress, Planning, On Track, while the API's statuses are Active, Planning, On Hold, Complete. What is the rule — is In Progress / On Track derived (from percent, from due pace), or should I render the status string exactly as the API gives it and let On Hold read as Archived? I won't invent the mapping; tell me the rule and I'll render it.

## Guardrail (DEC-0008) on the two field asks

- Pictures: genuinely missing (nothing kept per project/mission); engine field, same photo-field pattern as Q-0014 so nothing duplicated; no life event, no new links; exposed through `/api/projects` and `/api/missions`; REAL when uploaded, DERIVED when kind-default.
- Estimated time: genuinely missing; engine field; no duplication; no life event, no new links; exposed through `/api/missions`; DERIVED where job-known, otherwise blank.

## Note

H-0100 and H-0101 weren't in the `HANDOFFS/README.md` index, so I'm adding rows for H-0100, H-0101 and this one alongside filing it. DEC-0151 (the service map) is still Zac's call, not mine — noted, not answered here.
