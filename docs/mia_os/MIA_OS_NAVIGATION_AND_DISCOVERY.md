# MIA OS: navigation and discovery (Prompt 02 §9)

*Claude, 2026-11-15. This is a conceptual hierarchy; layouts belong to
Prompts 10 and 11.*

## What exists

- **Eight destinations** (`core/web_areas.py`, DEC-0153), each with subdashboards.
- **The bottom bar:** Dashboard, Apps, MIA, Search (confirmed by Zac).
- **The glasses:** orb, menu, Nexus.
- **Focus presets** put each person's likely apps first (`core/focus_presets.py`).
- **Search providers** (Ctrl+K).
- **"What can you do?"** is answered from `core/capabilities.py`.

## The model, for MIA OS

```
Main navigation (always)      Dashboard · Apps · MIA · Search      ← few, fixed
  └ Destinations (8)           Home, Garage, Finances, Health, AI Tools, Missions, Settings, Dashboard
      └ Subdashboards           Kitchen, Recreation (→ LEP, Nexus), Personal Tools (→ Smart Closet) ...
          └ Apps                one canonical owner each; elsewhere only widgets/shortcuts
Everywhere layers             Talk/voice · Search · notifications · Send to MIA (selection)
Contextual                     suggestions on the Dashboard (through the gate) · workspaces (projects)
Specialised experiences       Nexus → Living Worlds → the Convergence (not main navigation)
Background (no navigation)    scheduler, sync, discovery, backups — visible in Settings › System
```

## Rules

1. **Not everything goes in main navigation.**
   - LEP lives under Home › Recreation, with an Explore Today card on the Dashboard.
   - Smart Closet lives under Home › Personal Tools, with an "outfit for today" card.
2. **Every capability can be found three ways:**
   - by browsing (Apps);
   - by searching;
   - by asking ("can you plan a date?").

   `core/capabilities.py` stays the single, code-built list behind all three.
3. **Discovering what you don't know exists:**
   - MIA may mention an unused capability once, through the communication gate, when it fits the moment.
   - "What's new" in Settings lists capabilities added since the last look.
4. **Permissions are explained in place.** Every capability's entry says what it reads and whether it goes online (LEP discovery, weather).
5. **Device differences change how a capability is shown, not whether it exists** (DEC-0125). The glasses show LEP's top three nearby picks and Closet's outfit of the day.
