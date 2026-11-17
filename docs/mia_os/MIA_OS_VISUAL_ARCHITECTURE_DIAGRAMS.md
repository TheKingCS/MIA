# MIA OS: visual architecture diagrams (Prompt 11 §22)

*Claude (Opus), 2026-11-17. Mermaid.*

## 1. The design system and its tokens

```mermaid
flowchart TB
  PRIM["primitive tokens (web/tokens.css)"] --> SEM["semantic tokens: accent, meaning, tiers"]
  THEME["theme data (core/themes.py, Theme Studio, mia-theme/1)"] -->|validated, clamped| SEM
  SCHEME["scheme, layout, effects (core/appearance.py)"] --> SEM
  SEM --> COMP["components: frame, card, panel, approval card, orb"]
  COMP --> PAGES["pages (web/)"]
  PAGES --> PC["desktop"] & PHONE["phone"] & GL["glasses (reduced set)"]
  SEM --> KDE["KDE colour scheme (on his yes)"]
```

## 2. Theme loading

```mermaid
sequenceDiagram
  participant S as Settings
  participant E as Engine (themes.py)
  participant P as Page (shell.js)
  S->>E: choose or import theme
  E->>E: validate keys, clamp tiers, check contrast
  E-->>S: refused (why) or accepted
  P->>E: /api/shell
  E-->>P: tokens, material, layout
  P->>P: set tokens on :root, data-theme, data-material
```

## 3. The orb's states

```mermaid
stateDiagram-v2
  Idle --> Listening: mic open
  Listening --> Processing: request
  Processing --> Thinking: model
  Thinking --> Speaking: reply
  Speaking --> Idle
  Speaking --> Interrupted: he speaks
  Thinking --> Council
  Processing --> Approval: card waiting
  Approval --> Executing: approved
  Executing --> Success
  Executing --> Error
  Idle --> Unavailable: model down
  Idle --> Muted: mic off
```

## 4. Motion and degradation

```mermaid
flowchart LR
  EV["a state change"] --> MEAN["meaningful motion"]
  DEC["decorative"] --> CHK{"reduced motion? light/none? hidden? model busy?"}
  CHK -->|yes| OFF["off"]
  CHK -->|no| ON["on, within budget"]
  MEAN --> RM{"reduced motion?"}
  RM -->|yes| FADE["fade"]
  RM -->|no| FULL["full transition"]
```

## 5. Devices

```mermaid
flowchart LR
  DS["design system"] --> D["desktop: full tiers, effects by GPU"]
  DS --> M["phone: one column, light effects"]
  DS --> G["glasses: black, rings, six lines"]
  DS --> Z["Zeta Astralis: 4:1, one card"]
  DS --> SP["spatial: the same screens in depth"]
```

## 6. Spatial portals

```mermaid
flowchart LR
  P["portal: Workshop"] --> V["the Workshop dashboard, in depth"]
  V --> SAME["the same screens and actions as the sidebar"]
```

## 7. Audio

```mermaid
flowchart LR
  E["event"] --> SND{"interface sounds on?"}
  SND -->|yes| PLAY["local sound + visual twin"]
  SND -->|no| VIS["visual only"]
  AL["alarm"] --> ALWAYS["always sounds"]
```

The cross-application system and accessibility are the tables in their documents; each follows diagram 1.
