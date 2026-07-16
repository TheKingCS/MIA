# Bundled fonts

The "ForMIA" design handoff (`docs/ROADMAP.md`'s 2026-07-15 entries)
specifies **Inter** for UI text and **JetBrains Mono** for numeric/mono
accents in the `dark_field` theme. Neither is a default system font on
a fresh Windows/Linux/Pi install, so they're bundled here and loaded at
startup via `QFontDatabase.addApplicationFont()`
(`core/application.py`) rather than assumed present — the same
"don't assume, verify" discipline this project applies to everything
else.

- **Inter** (Regular/Medium/SemiBold/Bold/ExtraBold, static weights) —
  SIL Open Font License 1.1. https://github.com/rsms/inter
- **JetBrains Mono** (Regular/Medium/Bold) — Apache License 2.0.
  https://github.com/JetBrains/JetBrainsMono

Both fonts are free to bundle/redistribute under their respective
licenses. Files fetched from Google Fonts' static TTF distribution
(fonts.gstatic.com), not the variable-font versions, since Qt's
`QFontDatabase` works with plain static weight files without needing
variable-axis handling.
