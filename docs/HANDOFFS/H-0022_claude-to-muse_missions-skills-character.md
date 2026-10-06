# H-0022: Missions, Skills and Character are working (closes H-0013)
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-06
- Related: H-0013, H-0021, DEC-0017, DEC-0018, Q-0014

## H-0013, item by item

1. **Mission detail.** `/api/missions` (`MIA.missions()`) has every mission object: objectives with progress, difficulty, XP, credits and the skills it teaches. It also has MIA-assigned, group quests with "your part", the pathway step, a linked asset and the recipes it unlocks.
2. **Per-skill totals and levels.** `/api/skills` has each skill's level, XP into the level, XP needed, capability, XP this week and what a locked one needs. Each category also carries its trend (growing, quieter, or not started).
3. **Character level and XP.** Every page carries `me`: level, XP, credits, prestige tier and color. `/api/character` adds lifetime stats, the collection, the rarity tally and emblems.
4. **Rarity.** Applied only where the engine has it: challenge chains, hidden achievements and the collection. These use your `.rarity .r-*` classes and `.rarity-tag`. Missions carry their difficulty and never an invented rarity, as you asked.

## What landed (yours to review and polish)

- **Missions (`missions.html`, `missions.js`).**
  - Tabs: Active (ready to complete first), Daily (streaks), Completed and Set aside.
  - Each card shows icon, name, area, objectives done, progress bar, rewards, an MIA badge and a difficulty chip. A one-tap +1 counts the next objective, and Complete appears when the mission is ready.
  - The mission sheet has objectives (+1, add, remove), rewards, Complete, Give up for now (with a reason), Pick back up, Teaches a skill, Edit and Delete.
  - "Ask MIA for one" keeps your invent-a-mission idea, through Talk.
- **Skills (`skills.html`, `skills.js`).**
  - Category tabs, your interests first (★), with ↑ or ↓ for the trend.
  - Skill cards, with locked ones dashed and saying what they need. The next-honest-step skill glows.
  - The skill sheet lists its pathways with a Start button.
  - Side column: next honest step, prestige and recent achievements. Rewards are below.
- **Character (`character.html`, `character.js`).** Name, level and prestige, lifetime XP, credits and missions done. It also shows a portrait placeholder (art comes later, Zac's call), lifetime stats, top skills, latest missions, the collection with the rarity tally, and prestige emblems.
- **A shared level card:** `MIAShell.levelCard(node, me)`, which wears the prestige color once earned.
- **Styles:** the "Missions, Skills, Character" section at the end of `concept.css`. Character is purple. Its photo is `img/character.jpg`, now on the image list for ChatGPT.

## Two engine fixes you'll feel

- Completing a mission from the phone now gives the XP to the person on the phone, not whoever is signed in on the PC. This applies to every action.
- Undo of a mission, skill or pathway change now shows immediately.

## Acceptance criteria

- After any polish, these still work end to end, each with confirm and undo:
  - complete, +1, add an objective, give up and pick back up, add a mission;
  - start a pathway;
  - prestige (it appears only at level 100).
- No rarity on missions.
