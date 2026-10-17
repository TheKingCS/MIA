# Show-off mode: "MIA, show off for my friends"

*Built 2026-10-17 (DEC-0031): say "show off for my friends", or Home's gear
menu → Show Off. `core/show_off.py`, `web/showoff.html`. Zac, 2026-10-17: "I eventually want a command for 'MIA show off for my
friends' and it walk through like a tutorial/demo mode to show off her
abilities." Parked; Claude's notes for when it's built.*

## The idea

Saying (or typing) "show off for my friends" starts a guided tour. MIA
narrates, out loud where there's a voice, and each step opens the real
screen and does something live: a level-up celebration, a boss battle's
HP bar, a buff, this week's Chronicle chapter, the Reward Shop, a
crafting recipe's shopping list, "What I Used" under an answer, MIA
Remembers, and the glasses view. It ends with "ask me anything" and a
couple of suggested questions. Next / Back / Stop at every step.

## The one rule: friends never see private things

A demo in front of other people must never show money, the journal,
memories, health or people's details. Two ways:

1. **Demo world (Claude's recommendation):** the tour runs on the "Robin"
   demo data (the same placeholder world as the public preview), so
   everything can be shown and nothing real is at risk. Changes made in
   the tour are thrown away.
2. **Your own MIA with a privacy filter:** real data, with money, the
   journal, memories, health and people hidden for the tour.

## Built on what exists

- The trigger: `core/quick_commands.py` (plain-word commands, no model).
- The script: a list of steps in core (screen, what MIA says, the live
  action), like `core/onboarding.py`'s template-based welcome, never an
  LLM call (no waiting in front of an audience).
- The demo world: `docs/schema/*.example.json` (what the Pages preview
  reads), or a seeded throwaway engine like the screenshot tools.
- Voice: the phone's voice output; the glasses view for the finale.

## Decided (DEC-0031)

Zac, 2026-10-17: "We will build it for my real profile." Option 2: real
data, with money, the journal, memories, health and people's details
hidden for the whole tour.

## As built

Cards (empty ones skipped): hello, level and top skills, the six stats,
buffs (never Debt Slayer, Good Company, Well Fed or Clear Mind), missions
and a mission boss (never a debt), gear condition, crafting (recipes,
builds, a finished build's photo; never a price), the Reward Shop's
credits, this week's Chronicle without money / journal / people / food
lines, the glasses, and the finale. Back / Next / Stop, arrow keys,
optional voice (the browser's own speech). No Talk on the tour page.
`tests/test_show_off.py` seeds a debt, a journal entry, a memory, a
person, a weight and a meal and checks none of them reach the tour.
