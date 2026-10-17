# H-0051: The game layer, first four pieces (DEC-0028)

- From: claude → muse (cc zac, chatgpt)
- Date: 2026-10-17
- Status: built and pushed; the look is yours to polish

Zac asked what would make MIA feel like living in a video game and
approved the whole list in `docs/GAME_LAYER.md` (DEC-0028). The first
four are built:

1. **Reward Shop** (`web/shop.html`, a new app; Character's Credits tile
   opens it): rewards the person sets, bought with earned credits.
   Classes `.shop-*`.
2. **Gear condition bars** on Garage / Greenhouse / Real Estate asset
   cards, each asset's page, and the glasses' Assets list:
   `MIAShell.conditionBar(c)`, classes `.gear-condition`, `.gc-*`.
   Tones: ok / soon / bad (green / amber / red).
3. **Boss battles**: Missions → Bosses. Debts are bosses (HP bar in red,
   interest shown as the boss healing), missions can be made bosses, a
   Hall Of Fame. Classes `.boss-*`.
4. **Real character stats**: Character → Attributes, six stats 1–20 with
   a two-part bar (blue = training, green = last 30 days) and a "⌚ A
   watch adds" line. Classes `.attr-*`.

For ChatGPT (vision): ideas 5–13 in `docs/GAME_LAYER.md` wait for Zac's
next pick; the guardrails there (never punishing, health data stays on
the person's devices, no slot-machine patterns) apply to all of them.
