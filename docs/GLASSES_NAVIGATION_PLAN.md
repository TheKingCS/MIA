# Glasses navigation and flow: draft plan

*Claude, 2026-11-02. Status: DRAFT for Zac. Nothing here is decided. It starts
from what's built, then lists what each app needs and what Zac has to choose.*

## How it works today

```
Her orb
  └─ move ─ Home: Priority now, app tiles (eight to a page), the selected app's line
              ├─ an app ─ number tiles and its menu
              │             └─ a list ─ a line
              │                          ├─ an action: approve with a second gesture
              │                          └─ deeper (a recipe shelf, a vehicle, a playlist)
              ├─ All Apps: the same screen, every app
              └─ Conversation
```

Move walks, select goes in, back goes up one. Voice works anywhere: "open
Kitchen", "go home", or anything else for Talk.

## Rules to keep (proposed)

1. **Four levels at most:** Home, app, list, item. Anything deeper is a phone job.
2. **Back always goes up one**, and never loses your place in a list.
3. **Every screen says what move, select and back do.**
4. **Reopening an app returns to where you were** for a few minutes. Not built.
5. **Something running stays reachable:** music or a live workout shows on Home.
   Not built.
6. **Voice for anything typed:** a number, a name or a search is spoken, never
   picked letter by letter. Which of these she can already do needs testing.
7. **Long lists get shelves first**, as recipes now do, so nobody swipes through
   sixty things.

## App by app

Reach: what the real glasses can open now, through the relay's `HOME_APPS`.

| App | Reach | Can do on the glasses now | What's missing |
|---|---|---|---|
| Missions | Yes | Pick one, tick steps, see what's ready | Claiming a finished mission is off the relay |
| Calendar | Yes | Past due, today, soon | Open one event; add by voice |
| Kitchen | Yes | Recipe shelves, ingredients, steps, Ate it, Got it | "I Made This" is off the relay; add to the list by voice; photos don't cross |
| Workout | Yes | Today's training, steps | Active Training is off the relay; logging weight by voice |
| Garage, Greenhouse | Yes | Assets, one asset, Done | Meter readings |
| Music | Yes | Songs, playlists, artists, Now Playing | Shuffle, search by voice, its card on Home |
| Skills, Character | No | Readouts only | Are they wanted? |
| People, Household, Notes, Inbox | No | A few panels or questions | Personal: each is Zac's call |
| Rentals, Budget, Freedom | No | Nothing, by rule (H-0041, DEC-0062) | Stay on the phone unless he says otherwise |
| Workshop, Expeditions, Maps, Navigation, Classroom, Memories, Lab, Field Kit, Power, Observations, Diagnostics | No | Questions for MIA, which the relay doesn't carry | Each needs its own decision: panels, or off the glasses |

## Questions for Zac (three open)

1. **Which apps belong on the glasses at all?** A short list that works well beats
   twenty-five thin ones. Proposed first: Missions, Calendar, Kitchen, Workout,
   Garage, Music, then People.
2. **Pinned order on Home:** by your stars, or the order you use them?
3. Answered 2026-11-02 (DEC-0065): yes, with claiming missions.
4. **Should People and Notes cross the relay?** They're personal, so it's a wider read.
5. Answered 2026-11-02: song files Zac copies to the phone. MIA reads its Music
   and Download folders, once Android allows it.

## Build order (proposed)

1. Rule 5, what's running on Home, because music needs it.
2. Rule 4, returning to your place.
3. App by app in the order of question 1, each with a board on the canvas first.
4. Rule 6, testing every spoken shortcut and listing what's missing.
