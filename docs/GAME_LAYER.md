# The Game Layer: making life feel like a game

*Written by Claude, 2026-10-17, from Zac's question: "What else might it
need to be as much like living in a video game as it could be?" Zac:
"I love all of your ideas, so let's take note of them and work on them
in your recommended order." Decision: DEC-0028.*

MIA already covers the whole of a life as the game world: home, gear,
money, food, body, trips, people. What it needs to feel like *Ready
Player One* is less about new apps and more about the feel:

1. **The world notices you.** Games track you automatically; progress in
   MIA mostly comes from tapping Done. The watch (health), location
   (geofenced quests) and the glasses close that gap.
2. **Your stats are real.** XP exists; the character sheet should reflect
   the actual person.
3. **Things feel like objects in a world**, not rows in a list.

## The ideas (all approved to note; built in the order below)

| # | Idea | What it is | Built on |
|---|---|---|---|
| 1 | **Reward Shop** | Spend credits on real rewards the person sets ("new bike pedals = 3,000", "guilt-free gaming night = 500"). | Credits (profile) |
| 2 | **Gear condition bars** | Garage / Real Estate assets as equipment with a condition bar that drains as upkeep comes due and refills when it's done. | Maintenance |
| 3 | **Boss battles** | Big goals with an HP bar: paying off a debt, training for a race, finishing a build. | Money (debts), missions, builds |
| 4 | **Real character stats** | Vitality (sleep, resting HR, HRV), Stamina (steps, cardio, VO2 max), Strength (lifts, skill bests), Wisdom (journal, Classroom), Charisma (time with people), Craft (kitchen, workshop). Ready for the watch. | Fitness, journal, people, kitchen, workshop |
| 5 | **Buffs, never debuffs** | "Well Rested +10% XP", "Hydrated", "On a Roll". Positive only (DEC-0014). | Stats, streaks |
| 6 | **World map, fog of war** | Hikes, rides and expeditions reveal the map; achievements for new places; photos pinned where taken. | Expeditions, waypoints, maps |
| 7 | **Questlines and seasons** | Linked chapters ("Homestead Spring: Ch. 1 Prep the beds → Ch. 2 Plant → Ch. 3 First harvest"), seasonal events, MIA as quest-giver and narrator. | Missions, pathways |
| 8 | **The Chronicle** | A weekly and yearly story recap MIA writes ("Week 42: you conquered the garage…"). | Life events |
| 9 | **Crafting** | Recipes as blueprints, pantry as materials, "missing materials"; Workshop jobs turning materials into products. | Kitchen, Workshop |
| 10 | **Party and guild** | Co-op household quests (a spring-cleaning raid), opt-in friendly leaderboards. | Households |
| 11 | **Sound** | Level-up fanfare, a quest-complete chime on the glasses, MIA's voice lines. | Glasses, phone |
| 12 | **Watch health HUD** | Energy bar from sleep and recovery, heart-rate zones as intensity feeding XP, self-logging workouts, a live run HUD on the glasses (HR, pace, distance, objective). | Smart watch (later) |
| 13 | **Location quests** | Arrive at the gym: the session starts; walk into the store: the grocery list is on the glasses. | Phone location |

## Guardrails

- **Never punishing** (DEC-0014): no HP lost for a slow week, no guilt.
  Buffs only; stats never fall to shame anyone.
- **Health data stays on your own devices.**
- **Not a slot machine**: no streak-loss threats, no manufactured urgency.
  The goal is a life that feels like an adventure.

## Build order (DEC-0028)

1. Reward Shop → 2. Gear condition bars → 3. Boss battles → 4. Real
character stats. Then the rest as Zac picks them.

## Status

| # | Idea | Status (2026-10-17) |
|---|---|---|
| 1 | Reward Shop | ✅ built: `web/shop.html`, `core/reward_shop.py`, `shop_reward.*`, `shop.buy` |
| 2 | Gear condition bars | ✅ built: `core/web_equipment.condition`, cards, asset pages, glasses |
| 3 | Boss battles | ✅ built: Missions → Bosses, `core/boss_battles.py`, `boss.add/remove` |
| 4 | Real character stats | ✅ built: Character → Attributes, `core/character_stats.py` |
| 5–13 | Buffs, world map, questlines, Chronicle, crafting, party, sound, watch HUD, location quests | waiting for Zac to pick the next one |
