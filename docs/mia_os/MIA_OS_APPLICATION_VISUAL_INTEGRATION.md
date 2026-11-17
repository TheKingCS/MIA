# MIA OS: apps and the visual system (Prompt 11 §18)

*Claude (Opus), 2026-11-17. Planning only.*

| App kind | Takes MIA's look | How |
|---|---|---|
| MIA apps (web) | fully | the shared frame and tokens; their atmosphere colour |
| Qt classic screens | partly, while they last | their QSS from the same palette; retired by parity |
| KDE / Qt apps | colours | a KDE colour scheme generated from the active theme's tokens (dark, accent) |
| GTK apps | colours | the matching GTK/libadwaita accent where supported |
| Flatpak apps | as their toolkit allows | portal colour-scheme preference (dark/light) and accent |
| Games, creative tools | no | they keep their own identity |

**Never required:** an app that doesn't follow MIA's look still works fully; MIA's look is offered to it, never forced.
Generated KDE schemes are written to his `~/.local/share/color-schemes/` only on his yes (a setting), and undone by
choosing another.

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-024 | MIA shall offer a KDE colour scheme matching the active theme, applied only when he chooses it, and every conventional app shall work fully without it. | Could | R1 | PC | New | D | DEC-0234 → 11 |
