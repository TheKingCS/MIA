# MIA OS: motion (Prompt 11 §9; DEC-0238)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. Speeds and easing

| Token | Duration | For |
|---|---|---|
| `--dur-fast` | 120 ms | hover, press, toggles |
| `--dur` | 240 ms | panels, cards, navigation |
| `--dur-slow` (new) | 480 ms | mode changes, portal transitions |
| `--ease` | a soft ease-out | everything; ease-in only for leaving |

## 2. Two kinds

| Kind | Examples | Reduced motion | Effects light/none | While models busy |
|---|---|---|---|---|
| **Meaningful** | orb states, a panel opening, a value changing, a card appearing | a fade of `--dur-fast` | kept, simplified | kept |
| **Decorative** | particles, backdrop drift, liquid surfaces, scanlines | off | off | off |

**Rules:** no animation delays an action (input is accepted during it); every animation is interruptible (a new
state replaces it at once); no loop runs while hidden; nothing flashes more than three times a second.
**Budgets:** 60 fps on the desktop for transitions; the 3D room 60 fps on his PC and paused when not shown; no
continuous animation over 2 % of a CPU core at idle.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-011 | No animation shall delay or block input, and every animation shall be interruptible. | Must | MVP | All | Partial | T | DEC-0238 → 11 |
| REQ-VIS-012 | Decorative motion shall stop with reduced motion, light or no effects, while hidden, and while her models are generating. | Should | R1 | All | Partial | T | DEC-0238, DEC-0204 → 11 |
