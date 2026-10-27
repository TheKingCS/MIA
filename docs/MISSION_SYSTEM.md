# The Mission System: how MIA runs the game of your life

*Locked in by Zac and Claude, 2026-10-27 (DEC-0047). Zac: "Take note of
all your suggestions because I like them all", plus his answers to the
six questions below. This is the design every mission feature follows;
nothing here is built yet unless the Status table says so.*

MIA is a super-intelligent assistant that lives in your mind, gamifies
your life and organizes it. The mission system is how: your normal week
runs as a **loop**, anything outside it becomes an **adventure**, and she
keeps score in what you actually gain.

## 1. The layers

| Layer | What it is | Where it comes from | Example |
|---|---|---|---|
| **The Loop** | The normal week: the same grind and the same checks | Appears **automatically** from what recurs: shifts, chores, workouts, bills, the weekly check-in | Mon–Fri dungeon runs; Sunday progression check |
| **Adventures** | Anything outside the norm, built from that day's project | A project started, a calendar event that isn't routine, or saying "today I'm building a bench" | **New Mission: Woodworkers Guild, Apprentice Quest: build the bench** |
| **Questlines** | Multi-chapter goals | Bigger projects, seasons | Homestead Spring, chapters 1–3 (built, DEC-0032) |
| **Bosses** | Big goals with an HP bar | Debts, overtime runs, big builds | A loan; a 10-hour overtime run (built, DEC-0028 / DEC-0046) |
| **Side quests** | Real trouble, reframed | Game Master mode | Hard Mode: Bare Shelves (built, DEC-0046) |

## 2. The rules (Zac's answers)

1. **Who creates missions.** Loop missions appear **automatically** from
   what recurs (MIA learns the schedule from what actually happens:
   runs, calendar, routines). Adventures and the rest MIA **proposes**
   from what you're doing, and you can always ask for one.
2. **How a mission is completed.** **All of these:** evidence MIA can see
   (a run cleared, a project step done, a deposit landed, a workout
   logged), a tap on Done, or telling her.
3. **Rewards are what you actually gain in real life.** A woodworking
   quest rewards **the finished piece** (into your things or goods on
   hand) and **unlocks its recipe** (blueprint) if it wasn't already; a
   dungeon run rewards its pay; meal prep rewards the meals in the
   fridge; upkeep rewards the gear's condition bar refilled. XP, skill
   ranks and titles still track progress alongside the real reward.
4. **No limit on missions.** As many as the day actually holds. (What
   MIA *says* unprompted about them still bundles through the
   communication gate, so the phone doesn't buzz for each one; the
   missions themselves aren't capped.)
5. **The weekly check-in is Sunday morning**: a recap of last week (runs
   cleared, loot, what moved, titles earned, patterns noticed) and the
   layout of this week's planned missions (the loop, plus any
   adventures already in view).
6. **A missed loop day shows honestly**: that day earned nothing and the
   week's dungeon shows the share cleared ("4 of 5 runs, 80% cleared").
   No XP is taken away and nothing is punished (DEC-0014): it's the
   true state of the week, shown plainly.

## 3. Guilds and ranks

Each skill tree is a guild (woodworking → the Woodworkers Guild,
cooking → the Cooks' Guild, the homestead → the Homesteaders'). Ranks
follow your real skill level: **Apprentice → Journeyman → Master**. An
adventure's objectives are the project's real steps; your rank decides
the size of quest MIA offers. A **rank-up trial** is a harder project
that proves the next rank. Ranks **unlock** bigger blueprints, the way a
game gates gear by level.

## 4. MIA as the voice in your head

- **Morning quest log, evening debrief**: today's loop and any
  adventure in the morning; the loot, XP and what moved at night, like a
  session recap.
- **She notices patterns** ("Third Bare Shelves this week: want the
  record?", "Three woodworking projects: one more and your Journeyman
  trial is open"). Built on core/mission_patterns.py's
  observe → insight → recommend loop.
- **Always one glance away**: the current objective on the glasses; at
  the factory, the run tracker and the hours to boss loot.

## 5. Progression that's real

- **Titles** unlock from real streaks and feats ("Unbroken": ten
  hard-mode runs cleared; "Provider"; "Builder of the North Field"),
  shown on the character sheet.
- **A class emerges from what you actually do** (Homesteader, Maker,
  Provider): never picked, read from your life.
- **New Game+**: reaching the next dungeon (Freedom) carries your
  skills, titles and loot into the new life.

## 6. The world

- **The Codex**: recurring problems as known enemies, with what beat
  them last time ("The jammed conveyor: weakness, reset the sensor
  first"). Your own fixes, brought up when the problem comes back.
- **Rest as camp**: a real day off gives a Rested buff, never a penalty.
- **NPCs and the party**: people as your party, with real relationship
  quests; second shift are the stage preparers, never villains.
- **Seasons**: each quarter a season with its own goal and events, and a
  recap chapter in the Chronicle.

## 7. Feel

- **Cutscenes for big moments**: a rank-up, a boss falling, a season's
  end get MIA's narration and the fanfare, on the phone and the glasses.
- **Rare finds, never a slot machine**: surprises come only from real
  milestones, never random rewards meant to keep you hooked.

## 8. What exists to build on

Missions and objectives (core/mission_manager.py), recurring missions
(core/recurring_mission_manager.py), pathways and discovery, pattern
insights (core/mission_patterns.py), questlines and seasons
(core/questlines.py), bosses (core/boss_battles.py), the Dungeon and the
Game Master (core/work_dungeon.py, core/game_master.py), crafting
recipes and kitchen blueprints, buffs, character stats, the Chronicle,
sound, the glasses, the communication gate.

## 9. Status

| Piece | Status |
|---|---|
| Layers: questlines, bosses, side quests | ✅ built |
| The Loop, auto-generated from what recurs | ✅ built 2026-10-27 (`core/the_loop.py`, The Dungeon → Loop): work and chores get a rhythm by themselves, days and times learned (yours win), the week's runs planned, reminders at the time, night shifts counted for the night they started |
| Adventures from the day's project, guild quests | to build |
| Real-gain rewards (the craft, recipe unlocks) | to build |
| Completion by evidence, tap or telling her | partly (tap, telling her) |
| Sunday morning check-in | ✅ built 2026-10-27 (`core/weekly_checkin.py`, `web/checkin.html`): last week's story, the loop's score, loot, what MIA noticed; this week day by day; a rhythm of its own (Sundays 9:00, movable); Debrief Done +15 XP |
| Missed loop days shown as the share cleared | ✅ built (the week grid: cleared ✓, missed ✗ earning nothing, "3 of 4 cleared so far") |
| Guilds, ranks, rank-up trials, unlocks | to build |
| Morning quest log, evening debrief | to build |
| Pattern noticing (beyond abandonment) | to build |
| Titles, emergent class, New Game+ | to build |
| Codex, rest as camp, party quests, seasons as quarters | to build (seasonal questlines exist) |
| Cutscenes, rare finds | to build (sound exists) |
