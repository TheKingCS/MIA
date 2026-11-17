# MIA OS: desktop diagrams and wireframes (Prompt 10 §23)

*Claude (Opus), 2026-11-17. Mermaid and text wireframes; structure, not final visuals.*

## 1. The whole desktop

```mermaid
flowchart TB
  SDDM["SDDM login"] -->|MIA (default)| KW["KWin (MIA session)"]
  SDDM -->|Plasma| PL["KDE Plasma"]
  KW --> SHELL["MIA shell: Qt WebEngine window (web/)"]
  KW --> APPS["Linux apps (Flatpak)"]
  SHELL --> RT["MIA runtime: stores, actions, gate, search"]
  RT --> INT["intelligence (P07)"] & AUT["autonomy (P08)"] & SELF["self-awareness (P09)"]
  SHELL -.portals.-> PORT["xdg-desktop-portal-kde"]
  SHELL -.D-Bus.-> NOTIF["notifications, Baloo, KWin scripts"]
```
The shell is one client of KWin; Linux apps are others. Everything she does reaches the OS through portals and D-Bus.

## 2. Navigation

```mermaid
flowchart LR
  SIDE["sidebar"] --> HOME["Home"] & AREA["an area"] & SEARCH["Search"] & MIS["Missions"] & TALK["Talk"] & NOTE["Notifications"] & SET["Settings"]
  AREA --> DASH["its dashboard"] --> APP["an app"]
```

## 3. Search

```mermaid
flowchart LR
  Q["query"] --> P1["her records"] & P2["recall index"] & P3["Baloo files"] & P4["desktop entries"] & P5["capabilities"]
  P1 & P2 & P3 & P4 & P5 --> R["typed results"]
  R -->|open / find| SHOW["show"]
  R -->|ask| TALK["Talk"]
  R -->|start / do| CARD["approval card"]
```

## 4. Context sharing

```mermaid
sequenceDiagram
  participant Z as Zac
  participant S as Shell
  participant P as Portal
  participant M as MIA
  Z->>S: Share window
  S->>P: screencast request
  P->>Z: pick a window
  Z->>P: Firefox
  P->>S: one frame
  S->>M: frame + chip "Firefox"
  Z->>S: remove chip
  S->>M: context gone
```

## 5. Modes

```mermaid
stateDiagram-v2
  Workspace --> Ambient: idle / second monitor
  Ambient --> Workspace: any input
  Workspace --> Immersive: an immersive app
  Immersive --> Workspace: Esc
```

## 6. Workspace lifecycle

```mermaid
flowchart LR
  T["template or project"] --> C["create record"] --> O["open: desktop, screens, apps"] --> W["work: offered additions"] --> X["close: windows close or stay"] --> O
```

## 7. Notifications

```mermaid
flowchart LR
  HERS["her messages"] --> GATE["gate"] --> HIST["one history"]
  URG["alarms, urgent"] --> HIST
  APPN["apps, OS"] --> FD["freedesktop (Plasma)"] --> HIST
```

## 8. Settings boundaries

```mermaid
flowchart LR
  MS["MIA Settings"] --> PREF["her preferences"] & GR["grants, protected list"]
  MS -->|opens| KS["KDE System Settings"]
  MS -->|action| HELP["fixed-operation helper"] --> POLKIT["polkit dialog"]
```

## 9. Failure and fallback

```mermaid
flowchart TB
  CRASH["shell crash"] --> RESTART["systemd restarts it"]
  RTD["runtime down"] --> OFFER["shell offers Plasma"]
  KWF["KWin fails"] --> SDDM["back to login: Plasma or TTY"]
```

Further: the launcher, windows, missions, files, voice, accessibility, household and app integration are the tables
in their documents; each is a single flow through the shell, the runtime and the OS as above.

## 10. Wireframes

**Workspace mode, 4K at 150 % (2560 logical px):**
```
+--------+----------------------------------------------+---------------+
| MIA    | Home                         9:41  ☀ 31°  ● 2 |  Talk         |
| Home   | +--------------------+ +--------------------+ |  [Garage] x   |
| Garage | | Today              | | Due                | |               |
| ...    | +--------------------+ +--------------------+ |  > ...        |
|        | +--------------------+ +--------------------+ |               |
| ⌘K     | | Missions           | | MIA's activity     | |               |
+--------+----------------------------------------------+---------------+
| [Konsole] [Firefox]                                 Garage ▾  ⏹ stop  |
+-----------------------------------------------------------------------+
```

**Ambient, second monitor:**
```
+-----------------------------------------------+
|  9:41                Tuesday 17 November       |
|  ☀ 31°   next: dentist 2:30   music: ▶ ...     |
|  due: oil change · seed order                  |
|  ● MIA: Night School finished, 1 change in     |
+-----------------------------------------------+
```

**Immersive:**
```
+-----------------------------------------------+
|                Living World                    |
|                                     [Esc] back |
+-----------------------------------------------+
```

**Narrow (1280×720):**
```
+--+------------------------------------+
|⌂ | Garage                  9:41  ● 1  |
|🚗| [Vehicles] [Maintenance]           |
|$ | [Projects]                         |
|⌘ |              (Talk slides over)    |
+--+------------------------------------+
```
