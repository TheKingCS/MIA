# The game layer: missions, achievements and rewards tied together

*Zac, 2026-11-24: "everything needs to be intelligently intertwined with the mission system so that the user can see
the rewards and progress through all these different areas... the missions and achievements engines should be tied
together... cards that pop up congratulating me... Like a game." Built on what exists (docs/GAME_LAYER.md,
docs/MISSION_SYSTEM.md, core/rewards_manager.py); nothing here is a second rewards system.*

## The rule

Every number is read from a real record, never kept twice (the rewards manager's own rule): pounds from the grow
lab's harvests, eggs from the flock book, jars from the canning shelf's history, structures from Complete projects,
songs from the guitar path, recipes from the kitchen. What's earned is celebrated (DEC-0014: never punished), and
every unlock is in his history with its date.

## Step 1 (built 2026-11-24): achievements from his homestead, the log and the card

- `core/life_milestones.py`: produce grown (lb, oz and kg in pounds), eggs collected, jars canned, and structures
  built (greenhouse, aquaponics, coop, barn, shed, garage, workshop, cold room, power, water, well pump, raised beds,
  orchard, fence: a Complete project naming one; "repair the shed" builds nothing).
- `core/rewards_manager.py`: three new chains (Grower to 5,000 lb, Egg Basket to 500 dozen, Canner to 1,000 jars),
  the structures as one-time milestones; harvests, eggs and jars say `activity.logged`, so a tier crossed unlocks
  the moment it's logged.
- `core/achievement_cards.py`: the log (every unlock, dated), the cards not yet seen (three at most at once), the
  page (`web/achievements.html`, linked from Skills) and the voice twin (`my_achievements`).
- The card (`web/shell.js`): every page shows each new unlock as a card in its rarity's colour with its sound, and
  a finished mission or a level reached from an action gets one too. Closing it marks that card seen by its id
  (/api/achievements/seen), outside undo, so it never blocks undoing what earned it.

## Step 2: typed mission rewards and missions completed by evidence

- A mission's reward gains kinds beyond XP, credits, skill XP and recipe unlocks (`Mission.recipe_unlocks` is the
  pattern): **item** (a crafted good, core/craft), **structure** (the project it builds), **song** (a song unlocked
  on the guitar path), **knowledge** (a course or lesson mastered, core/library_course.py), **recipe**, and **skill**
  (a new skill such as canning or preserving, added to `data/skill_definitions.json`). Each is shown on the mission
  card before it's earned and on the completion card after, and recorded in the history.
- A fourth objective metric, `records`: progress read from a life_milestones stat since the mission started ("put
  up 20 jars this summer", "harvest 100 lb from the greenhouse"), so the mission finishes itself from what he logs,
  the evidence MISSION_SYSTEM.md section 9 asks for.
- Achievements that a mission chain leads to are named on its missions ("this one is 3 of 5 toward Rule the Roost").

## Step 3 (built 2026-11-24): music, smart and online

- Music has a YouTube tab (`core/youtube_music.py`, `web/music.js`): search YouTube with a YouTube Data API key of
  his own (entered once on that tab, sealed at rest, never in a proposal), or paste a link (no key needed). Songs play
  in YouTube's own embedded player (the privacy-enhanced youtube-nocookie.com host, the only outside frame the
  page's security policy allows), and are saved as links (`youtube.save`): a library track with a video id and no
  file, so playlists mix his files and YouTube songs. Nothing is downloaded.
- By voice: `find_on_youtube`, `save_from_youtube` (onto a playlist he names) and `play_on_youtube` (saved and left
  as MIA's pick at the top of Music, one press to play: a voice turn has no screen for a video).
- Offline: his own files, Creative Commons or public-domain audio and purchases with files. Ripping YouTube to MP3
  breaks YouTube's terms and usually copyright, so MIA won't; YouTube Music Premium is the legitimate offline route.
- Still to do: a YouTube song keeps playing only while the Music page is open (the shared player plays files);
  started by voice it waits for a press.
- His songbook (core/repertoire.py, built 2026-11-24): songs he can play, on Music's Can Play tab or "I learned
  Wagon Wheel on guitar"; the Songbook achievements (1 to 75 songs) and mission objectives count them.
