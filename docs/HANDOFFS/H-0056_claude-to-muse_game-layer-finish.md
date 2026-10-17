# H-0056 · claude → muse (cc zac) · 2026-10-17

## The rest of the game layer is built (DEC-0032): a look pass when you can

Zac picked the remaining game-layer ideas and they're working, in the
Stark tokens, on the shared frame. Function first, so the look is yours
to push (nothing here is final):

1. **Missions → Quests** (`web/missions.js` `questsView`, CSS
   `.season-banner`, `.quest-card`, `.quest-path`, `.quest-step`,
   `.quest-node`): a season banner, each questline as a vertical path of
   chapters (done ✓ green, current gold with MIA's line in italics,
   locked dimmed), dashed "offer" cards for starters.
2. **Party** (`web/party.html`, `.raid-card`, `.party-crew`): raid cards
   with a progress bar, a chip per person (theirs/total), the job list
   with who has each; the leaderboard (🥇🥈🥉 only with 3+ people and a
   win).
3. **World Map** (`web/worldmap.html`, `.world-canvas`, `.world-rank`):
   a canvas, fog = `--rgb-panel-2`, cleared tiles glow `--rgb-accent`
   with an outline only on the edge of explored land, gold "?" pins for
   unreached waypoints, emoji pins (📷 📍 🚩). There's no basemap yet.
   The pins are the weakest part; line icons would help.
4. **My Places** (`web/places.html`) and the **arrival prompt**
   (`.place-arrival`, a plain confirm dialog today).
5. **Sound** (`web/sound.js`): tones are synthesized (chime, quest,
   fanfare, tick). If you have a sound identity in mind, the note lists
   are at the top of `TUNES`.

All of them were checked at phone width (412 px, no sideways scroll). The
public preview has demo data for all of them (`?demo`).
