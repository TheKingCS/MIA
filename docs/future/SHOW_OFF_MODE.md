# Show-off mode: "MIA, show off for my friends"

*Zac, 2026-10-17: "I eventually want a command for 'MIA show off for my
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

## Open question for Zac

Demo world or your own data with private things hidden?
