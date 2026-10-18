# Handoffs

*Bigger pieces of work passed between Zac, ChatGPT, Muse and Claude
(rules: `docs/COLLABORATION.md`). One file each, named
`H-0000_from-to-to_subject.md`. Never put real personal data in a
handoff: use placeholders.*

## Template

```
# H-0000: <subject>
- From: <name> · To: <names> · Date: <date>
- Related: <DEC-, Q-, H- IDs, files>

## Context
## What's needed
## Constraints
## Acceptance criteria
```

## Index

| ID | From → To | Date | Subject | Where |
|---|---|---|---|---|
| H-0001 | chatgpt → claude, muse | 2026-10 | System architecture handoff: engine first, surfaces consume it | Not in the repo (relayed by Zac); its outcome is DEC-0003, DEC-0005, DEC-0006 |
| H-0002 | muse → claude | 2026-10-05 | MIA Engine Kickoff Spec | Not in the repo: it contained real personal seed data (DEC-0002). Answered by `docs/ENGINE_PHASE1_PLAN.md` |
| H-0003 | claude → muse | 2026-10-05 | Where MIA is, and how design connects to the engine | [`H-0003_claude-to-muse_where-mia-is.md`](H-0003_claude-to-muse_where-mia-is.md) |
| H-0004 | muse → claude | 2026-10-05 | Life State v2 schema gaps: vehicles, kitchen, workout missing from the read model | [`H-0004_muse-to-claude_life-state-schema-gaps.md`](H-0004_muse-to-claude_life-state-schema-gaps.md) (DONE, claude 2026-10-05) |
| H-0005 | claude → zac, muse, chatgpt | 2026-10-05 | Where MIA is, what she needs, and a Phase 2 proposal (web front end) | [`H-0005_claude-to-all_where-mia-is-and-phase-2.md`](H-0005_claude-to-all_where-mia-is-and-phase-2.md) |
| H-0006 | muse → zac, claude, chatgpt | 2026-10-05 | Review of H-0005 and the Phase 2 proposal | [`H-0006_muse-to-all_phase-2-review.md`](H-0006_muse-to-all_phase-2-review.md) |
| H-0007 | claude → muse (cc zac, chatgpt) | 2026-10-05 | The foundation is ready: build MIA's Home on it | [`H-0007_claude-to-muse_foundation-ready-build-home.md`](H-0007_claude-to-muse_foundation-ready-build-home.md) |
| H-0008 | claude → zac, muse, chatgpt | 2026-10-05 | The glasses platform (Meta Ray-Ban Display) and how MIA gets there | [`H-0008_claude-to-all_glasses-platform-and-plan.md`](H-0008_claude-to-all_glasses-platform-and-plan.md) |
| H-0009 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Home build accepted — plan, Life State mapping, questions | [`H-0009_muse-to-claude_home-build-accepted.md`](H-0009_muse-to-claude_home-build-accepted.md) |
| H-0010 | chatgpt → claude (cc muse, zac) | 2026-10-05 | Answers to current MIA questions (Q-0001, Q-0002, Q-0006, Q-0003/Q-0011) + architectural verdict | [`H-0010_chatgpt-to-claude_answers-to-current-questions.md`](H-0010_chatgpt-to-claude_answers-to-current-questions.md) |
| H-0011 | chatgpt → zac, claude, muse | 2026-10-05 | Decisions on Q-0001 (non-punitive), Q-0002 (child safety escalation), DEC-0014 extension | [`H-0011_chatgpt-decisions_q0001-q0002-dec0014.md`](H-0011_chatgpt-decisions_q0001-q0002-dec0014.md) |
| H-0012 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Design review: DEC-0016 and the glasses composition (response to H-0008) | [`H-0012_muse-to-claude_glasses-design-review.md`](H-0012_muse-to-claude_glasses-design-review.md) |
| H-0013 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Engine data gaps found building the concept screens (missions, skill XP, character level, rarity) | [`H-0013_muse-to-claude_engine-gaps-concept-screens.md`](H-0013_muse-to-claude_engine-gaps-concept-screens.md) |
| H-0014 | claude → muse (cc zac, chatgpt) | 2026-10-05 | The public preview (GitHub Pages) is set up; notes on Home, Missions, Skills | [`H-0014_claude-to-muse_public-preview-and-review.md`](H-0014_claude-to-muse_public-preview-and-review.md) |
| H-0015 | muse → claude (cc zac, chatgpt) | 2026-10-05 | Both H-0014 notes handled (font, Home links) | [`H-0015_muse-to-claude_h-0014-notes-handled.md`](H-0015_muse-to-claude_h-0014-notes-handled.md) |
| H-0016 | claude → muse, chatgpt (cc zac) | 2026-10-06 | Getting the front end on track: all of MIA, in the concept's look (DEC-0017) | [`H-0016_claude-to-all_full-parity-plan.md`](H-0016_claude-to-all_full-parity-plan.md) |
| H-0017 | claude → muse (cc zac, chatgpt) | 2026-10-06 | DEC-0017 approved: the shared frame and the dashboard Home are in | [`H-0017_claude-to-muse_dec-0017-frame-and-home.md`](H-0017_claude-to-muse_dec-0017-frame-and-home.md) |
| H-0018 | claude → muse (cc zac, chatgpt) | 2026-10-06 | Home is MIA again, a ⋯ menu, and Money is complete | [`H-0018_claude-to-muse_home-menu-money.md`](H-0018_claude-to-muse_home-menu-money.md) |
| H-0019 | claude → muse (cc zac, chatgpt) | 2026-10-06 | Garage, Property, Greenhouse, Maintenance and the asset page are working | [`H-0019_claude-to-muse_equipment-screens.md`](H-0019_claude-to-muse_equipment-screens.md) |
| H-0020 | claude → muse (cc zac, chatgpt) | 2026-10-06 | Kitchen, Workout and Real Estate are working | [`H-0020_claude-to-muse_kitchen-workout-real-estate.md`](H-0020_claude-to-muse_kitchen-workout-real-estate.md) |
| H-0021 | muse → claude (cc zac, chatgpt) | 2026-10-06 | Review of H-0019/H-0020: reviewer role per DEC-0018, look sign-off, photo fields via Q-0014 | [`H-0021_muse-to-claude_h-0019-h-0020-review.md`](H-0021_muse-to-claude_h-0019-h-0020-review.md) |
| H-0022 | claude → muse (cc zac, chatgpt) | 2026-10-06 | Missions, Skills and Character are working (closes H-0013) | [`H-0022_claude-to-muse_missions-skills-character.md`](H-0022_claude-to-muse_missions-skills-character.md) |
| H-0024 | claude → muse (cc chatgpt) | 2026-10-07 | The rest of the screen photos | [`H-0024_claude-to-muse_screen-photos.md`](H-0024_claude-to-muse_screen-photos.md) |
| H-0026 | muse → claude (cc zac, chatgpt) | 2026-10-12 | Fitness + nutrition plans as daily missions (engine spec) | [`H-0026_muse-to-claude_fitness-nutrition-missions.md`](H-0026_muse-to-claude_fitness-nutrition-missions.md) |
| H-0027 | claude → muse (cc zac, chatgpt) | 2026-10-12 | The fitness + nutrition engine is ready for your screens (closes H-0026) | [`H-0027_claude-to-muse_fitness-engine-ready.md`](H-0027_claude-to-muse_fitness-engine-ready.md) |
| H-0028 | muse → claude (cc zac, chatgpt) | 2026-10-12 | Fitness + nutrition screens: Muse's design (responds to H-0027) | [`H-0028_muse-to-claude_fitness-screens-design.md`](H-0028_muse-to-claude_fitness-screens-design.md) |
| H-0029 | claude → muse (cc zac, chatgpt) | 2026-10-14 | Fitness screens built, plus Zac's recipe page | [`H-0029_claude-to-muse_fitness-screens-built.md`](H-0029_claude-to-muse_fitness-screens-built.md) |
| H-0030 | claude → muse (cc zac) | 2026-10-14 | Put Zac's plan into MIA ("Paste a plan" text) | [`H-0030_claude-to-muse_paste-zacs-plan.md`](H-0030_claude-to-muse_paste-zacs-plan.md) |
| H-0031 | muse → claude (cc zac, chatgpt) | 2026-10-14 | Fitness screens look review, plus the reps field | [`H-0031_muse-to-claude_fitness-screens-look-review.md`](H-0031_muse-to-claude_fitness-screens-look-review.md) |
| H-0032 | muse → claude (cc zac) | 2026-10-14 | Zac's plan in Paste-a-plan text (responds to H-0030) | [`H-0032_muse-to-claude_paste-a-plan-confirmed.md`](H-0032_muse-to-claude_paste-a-plan-confirmed.md) |
| H-0033 | muse → claude (cc zac) | 2026-10-14 | Correction to H-0032; reps: yes | [`H-0033_muse-to-claude_h-0032-correction-reps-yes.md`](H-0033_muse-to-claude_h-0032-correction-reps-yes.md) |
| H-0034 | claude → muse (cc zac, chatgpt) | 2026-10-15 | MIA's new look: the Stark engineering interface (DEC-0023) | [`H-0034_claude-to-muse_stark-interface.md`](H-0034_claude-to-muse_stark-interface.md) |
| H-0035 | muse → claude (cc zac, chatgpt) | 2026-10-15 | Stark look review: technical plates, icons kept, gold rule settled | [`H-0035_muse-to-claude_stark-look-review.md`](H-0035_muse-to-claude_stark-look-review.md) |
| H-0036 | muse → claude (cc zac) | 2026-10-15 | Zac's call: technical plates | [`H-0036_muse-to-claude_technical-plates.md`](H-0036_muse-to-claude_technical-plates.md) |
| H-0037 | muse → claude (cc zac) | 2026-10-15 | Zac's PC specs for DEC-0022 | [`H-0037_muse-to-claude_zacs-pc-specs.md`](H-0037_muse-to-claude_zacs-pc-specs.md) |
| H-0038 | muse → claude (cc zac) | 2026-10-15 | PC uptime answer for DEC-0022 | [`H-0038_muse-to-claude_pc-uptime-answer.md`](H-0038_muse-to-claude_pc-uptime-answer.md) |
| H-0039 | claude → muse (cc zac) | 2026-10-15 | Technical plates are in; the gold rule applied; titles never break mid-word | [`H-0039_claude-to-muse_plates-and-spacing.md`](H-0039_claude-to-muse_plates-and-spacing.md) |
| H-0040 | muse → claude (cc zac) | 2026-10-15 | H-0039 accepted: plates, gold rule, no mid-word breaks | [`H-0040_muse-to-claude_h-0039-accepted.md`](H-0040_muse-to-claude_h-0039-accepted.md) |
| H-0041 | muse → claude (cc zac) | 2026-10-15 | Glasses app-cards plan approved by Zac; engine ask: per-app glance actions | [`H-0041_muse-to-claude_glasses-app-cards-plan.md`](H-0041_muse-to-claude_glasses-app-cards-plan.md) |
| H-0042 | claude → muse (cc zac) | 2026-10-16 | Glasses quick action menus for every app (H-0041 Phase 2), working | [`H-0042_claude-to-muse_glasses-quick-menus.md`](H-0042_claude-to-muse_glasses-quick-menus.md) |
| H-0043 | muse → claude (cc zac) | 2026-10-16 | Glasses quick menus — design answers on H-0042, pin list PROPOSED for Zac | [`H-0043_muse-to-claude_glasses-menus-design-answers.md`](H-0043_muse-to-claude_glasses-menus-design-answers.md) |
| H-0044 | muse → claude (cc zac) | 2026-10-16 | Zac approves glasses pin list (most important/most used first) + all three panels | [`H-0044_muse-to-claude_glasses-pins-approved.md`](H-0044_muse-to-claude_glasses-pins-approved.md) |
| H-0045 | claude → muse (cc zac) | 2026-10-16 | Glasses pins are favorites (Zac), Household/People/Inbox panels, line icons | [`H-0045_claude-to-muse_glasses-pins-and-panels.md`](H-0045_claude-to-muse_glasses-pins-and-panels.md) |
| H-0046 | claude → muse (cc zac) | 2026-10-16 | Glasses re-laid out to Zac's direction: orb alone, Saturn rings, two moves, no scrolling, Missions card | [`H-0046_claude-to-muse_glasses-zacs-layout.md`](H-0046_claude-to-muse_glasses-zacs-layout.md) |
| H-0047 | muse → claude (cc zac) | 2026-10-16 | Glasses layout + pins — design review of H-0045/H-0046, accepted with polish notes | [`H-0047_muse-to-claude_glasses-layout-design-review.md`](H-0047_muse-to-claude_glasses-layout-design-review.md) |
| H-0048 | claude → muse (cc zac) | 2026-10-16 | Missions after the orb with sorted due lists, the Calendar, Kitchen recipes and photos, Garage tabs, Title Case | [`H-0048_claude-to-muse_missions-calendar-kitchen-titlecase.md`](H-0048_claude-to-muse_missions-calendar-kitchen-titlecase.md) |
| H-0049 | claude → muse (cc zac) | 2026-10-16 | Maintenance and Property folded into Garage and Real Estate (DEC-0025); the chat bar fits a phone | [`H-0049_claude-to-muse_three-ownership-apps-chat-bar.md`](H-0049_claude-to-muse_three-ownership-apps-chat-bar.md) |
| H-0050 | claude → muse (cc zac) | 2026-10-16 | Journal, Workshop, Expeditions, Music and Files on the web; Home replaces the Dashboard | [`H-0050_claude-to-muse_five-screens-and-home.md`](H-0050_claude-to-muse_five-screens-and-home.md) |
| H-0051 | claude → muse (cc zac, chatgpt) | 2026-10-17 | The game layer's first four pieces: Reward Shop, gear condition bars, boss battles, real character stats (DEC-0028) | [`H-0051_claude-to-muse_game-layer.md`](H-0051_claude-to-muse_game-layer.md) |
| H-0052 | claude → chatgpt, muse (cc zac) | 2026-10-17 | Expansion audit done; ALICE picks (What I Used, MIA Remembers, one conversation, voice guide) and crafting recipes built | [`H-0052_claude-to-all_expansion-audit-alice-crafting.md`](H-0052_claude-to-all_expansion-audit-alice-crafting.md) |
| H-0053 | muse → claude (cc zac, chatgpt) | 2026-10-17 | Look pass on game layer, crafting, What I Used, MIA Remembers, buffs; voice-guide additions; DEC-0031 tour flag | [`H-0053_muse-to-claude_game-layer-crafting-look-pass.md`](H-0053_muse-to-claude_game-layer-crafting-look-pass.md) |
| H-0054 | claude → muse (cc zac) | 2026-10-17 | H-0053 look pass applied: boss border by kind, build photo stage colors; checks answered | [`H-0054_claude-to-muse_look-pass-applied.md`](H-0054_claude-to-muse_look-pass-applied.md) |
| H-0055 | claude → muse (cc zac) | 2026-10-17 | Three new screens: Orders & Quotes, Grow Lab, Show Off | [`H-0055_claude-to-muse_orders-grow-showoff.md`](H-0055_claude-to-muse_orders-grow-showoff.md) |
| H-0056 | claude → muse (cc zac) | 2026-10-17 | The rest of the game layer is built (DEC-0032): a look pass | [`H-0056_claude-to-muse_game-layer-finish.md`](H-0056_claude-to-muse_game-layer-finish.md) |
| H-0057 | muse → claude (cc zac) | 2026-10-17 | Look pass: Orders & Quotes, Greenhouse Water, Show Off tour, Quests / Party / World Map / Places / Sound; H-0054 checks answered | [`H-0057_muse-to-claude_look-pass-orders-tour-quests-map.md`](H-0057_muse-to-claude_look-pass-orders-tour-quests-map.md) |
| H-0058 | claude → muse (cc zac) | 2026-10-18 | H-0057 applied; Security app ready for a look | [`H-0058_claude-to-muse_h-0057-applied.md`](H-0058_claude-to-muse_h-0057-applied.md) |
| H-0059 | muse → claude (cc zac) | 2026-10-17 | Look pass: Security app (DEC-0033) — strip honesty, via-PC tag in full view, pictures delete label, empty-state copy; 2 checks | [`H-0059_muse-to-claude_security-look-pass.md`](H-0059_muse-to-claude_security-look-pass.md) |
