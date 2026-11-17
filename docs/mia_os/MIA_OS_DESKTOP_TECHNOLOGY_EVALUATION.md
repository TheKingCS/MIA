# MIA OS: desktop technology evaluation and decision records (Prompt 10 §24, §26)

*Claude (Opus), 2026-11-17. Planning only. DEC-0227 to 0233 are PROPOSED. Prompt 05's evaluation (`MIA_OS_CORE_TECHNOLOGY_EVALUATION.md` §4, §9) compared the desktops; this adds the shell and its parts.*

## 1. Technologies

| Need | Options | Recommendation | Why |
|---|---|---|---|
| Desktop foundation | KDE Plasma, GNOME, COSMIC | **KDE Plasma** (approved, DEC-0189) | mature Wayland, KWin scripting, Qt WebEngine is KDE's own engine, flexible panels; GNOME's shell is harder to extend and its extensions break each release; COSMIC is young (first stable 2025) |
| MIA's session compositor | KWin with her shell; cage; full Plasma underneath; our own | **KWin** (lean of DEC-0191), PoC 3 decides | one compositor for both sessions; real windows; KDE's lock screen and portals |
| Shell host | Qt WebEngine window (exists), Electron, Tauri, a browser in kiosk mode | **Qt WebEngine** | already MIA's host; KDE's engine, AT-SPI accessibility; Electron adds a second Chromium; Tauri's Linux webview is WebKitGTK, slower on her 3D room |
| MIA apps' UI | the web frame, Qt Quick, GTK, Flutter | **the web frame** | 109 screens working; the phone uses the same pages; one theme system |
| Window control | KWin scripts and D-Bus | **KWin scripts**, run on his press | supported API; no compositor hacks |
| Search of files | Baloo, Tracker, her own crawler | **Baloo** | KDE's index, already running, D-Bus |
| Notifications | freedesktop service (Plasma's), her own | **freedesktop + her gate** | apps already speak it |
| Widgets | Plasma widgets, her cards | **her cards** in her shell; Plasma widgets in Plasma | one contract for her data |
| Voice | Prompt 07's pipeline | as decided (DEC-0211) | |
| Accessibility | AT-SPI, Orca | **AT-SPI via Qt** | the Linux standard |
| Multi-monitor, sessions | KWin, SDDM, systemd user units | **as KDE does** | |

Each: Linux compatibility native; performance one WebEngine process for the shell; accessibility through AT-SPI;
security through Wayland isolation and portals; maintenance tracks KDE releases (Fedora's).

## 2. Decision records

### DEC-0227: the shell is MIA's web front end in a full-screen window under KWin
Context: Prompt 10 §3; DEC-0191's lean. Requirements: REQ-DSK-001, 018, 027, 031, 032. Options: cage; KWin with her
shell; a Plasma session with her on top; our own compositor. Selected: KWin in MIA's session, her shell as a
full-screen client in the Qt WebEngine host, restarted by a systemd user unit; Plasma at login and from the shell.
Rejected: a compositor of our own (forever to maintain); Plasma underneath (no clean MIA session). Risks: KWin as a
single-shell session is not a supported KDE path (R-57). Reversibility: high (a session file). Reconsider if PoC 3
fails: cage for the MVP.

### DEC-0228: one navigation model
Requirements: REQ-DSK-002 to 006, 008, 021, 026. Selected: areas, each area's dashboard, apps; Talk everywhere; a
status strip; the same on every device, shown differently. Rejected: a dock of apps (57 is too many to dock).

### DEC-0229: unified search; never executes a change
Requirements: REQ-DSK-009, 010. Selected: providers (hers, the recall index, Baloo, desktop entries) with typed
results; do and start only open an approval card.

### DEC-0230: context only by explicit share; workspaces as records restored through KWin
Requirements: REQ-DSK-011, 012, 015 to 017. Selected: chips, portals, read once; project workspaces bound to virtual
desktops and restored from desktop entries. Rejected: reading the desktop because Talk is open; per-app
integrations.

### DEC-0231: modes as states of one shell
Requirements: REQ-DSK-013, 014.

### DEC-0232: one notification pipeline
Requirements: REQ-DSK-019, 020. Selected: her gate for hers; the freedesktop service for apps and the OS; one history
with source and why.

### DEC-0233: apps stay in the framework that suits them
Requirements: REQ-DSK-007, 030. Selected: MIA's on the web frame; Linux apps native via Flatpak; no forced framework.
