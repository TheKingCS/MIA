# MIA OS: graphical and session architecture (Prompt 05, deliverable 4)

*Claude (Fable), 2026-11-16. Planning only. The display protocol, the compositor, the desktop foundation, how MIA's
session and the conventional desktop coexist, and what window management MIA needs from underneath. The look is
Prompt 11's (and prompt 24's, built); the desktop experience is Prompt 10's. Decision: DEC-0191 (proposed,
provisional). Sources [S…] are in [MIA_OS_CORE_TECHNOLOGY_EVALUATION.md](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md) §9.*

## 1. What is fixed already

- At login the PC offers at least two sessions, MIA's (the default) and KDE Plasma, each usable without the other
  running (REQ-FUN-001, REQ-UX-020).
- From MIA's session, the conventional desktop, settings, a terminal and the troubleshooting tools are reachable
  without MIA answering (REQ-UX-023).
- The conventional desktop is usable within 10 seconds of choosing it, with MIA's runtime still starting or failed
  (REQ-PER-002).
- MIA's surfaces are the web front end (`web/`), served by the runtime (DEC-0013, DEC-0124).

## 2. Display protocol and desktop foundation

**Wayland only.** X11 applications run through XWayland inside either session. Reasons: the desktops MIA would
build on have dropped or are dropping their X11 sessions; Wayland's isolation between clients is what makes "an app
can't read another app's window or keystrokes" true, which the security architecture will lean on; and it is where
multi-monitor scaling, touch and HDR work is happening.

That isolation is also a constraint MIA must design within: on Wayland there is no universal way for one program to
read another's selection, watch its windows or inject input. Each of those goes through a portal with his consent,
or through accessibility interfaces. The Universal Action Layer's Linux front doors were planned with this in mind
(its plan, §6).

**KDE Plasma is the conventional desktop** (approved in the requirements). GNOME and COSMIC were compared in the
technology evaluation §4.

## 3. The compositor for MIA's session: four ways, one provisional choice

| | 1. cage and a browser | 2. KWin, MIA's shell as its client | 3. A full Plasma session with MIA's shell on top | 4. Our own compositor (wlroots) |
|---|---|---|---|---|
| What it is | a kiosk compositor showing exactly one application | KDE's compositor started for MIA's session with her shell instead of Plasma's | the ordinary Plasma session, MIA's shell full screen over it, Plasma's panels hidden | a compositor written for MIA |
| MIA-first presentation | yes | yes | yes, by convention (Plasma is underneath) | yes |
| Ordinary app windows inside MIA's session | **no** (one application) | **yes** (a real window manager) | yes | yes, if we write it |
| Lock screen | none of its own | KDE's | KDE's | ours to write |
| Portals (screenshot, file chooser, shortcuts) | a second backend to set up (wlroots') | KDE's, the same as in Plasma | KDE's | ours to arrange |
| Accessibility (Orca, keyboard) | to prove (T-13) | KDE's stack, the same as in Plasma | KDE's | ours |
| Multi-monitor, scaling, HDR, touch | basic | KWin's | KWin's | ours |
| Two sessions each usable alone (REQ-FUN-001) | yes | yes | **no**: MIA's session *is* Plasma | yes |
| Memory | least | KWin and a few KDE services | all of Plasma | small |
| Maintenance | two graphical stacks (wlroots and KDE) | one stack; a session file and a startup script of ours | one stack; fragile hiding of Plasma | a compositor, forever |
| Maturity | maintained, used for kiosks [S9] | possible and reported working; **not a supported login path** [S11] | supported | nothing exists |
| Recovery when the shell dies | cage exits with it; the session ends | KWin stays; the shell is restarted | Plasma is right there | ours |

**Provisional recommendation: option 2 on the PC, option 1 on the Pi.** One compositor technology for both of the
PC's sessions means one portal backend, one accessibility path, one lock screen and one set of multi-monitor
behaviour to test, and it lets an ordinary application appear inside MIA's session, which workspaces
(REQ-FUN-063) and Zac's later handoffs need (core architecture §7). The Pi's single small screen is exactly what
cage is for.

**Why provisional:** starting KWin with a custom client is done by people and isn't a path KDE supports as a login
session [S11]. **Proof of concept 3** runs both candidates in a virtual machine against one list:

| Test | Pass when |
|---|---|
| Session starts from the login screen, shell full screen | under 10 s to Home (REQ-PER-001's second half) |
| Shell killed | the compositor stays; the shell is back within 5 s; three kills in a row show the recovery page |
| An ordinary Flatpak application launched from MIA | its window appears, can be moved beside the shell, closes cleanly |
| Lock on idle and on request | the lock is the OS's; unlocking returns to the same state |
| Screenshot of a region through the portal, with consent | an image reaches the capture agent |
| Global hotkey for the palette | works with the shell unfocused |
| Screen reader | reads MIA's shell and an ordinary application |
| Two monitors, mixed scaling | correct on both |
| "Open the desktop" from MIA's session | Plasma usable within 10 s (REQ-PER-002), MIA's runtime untouched |

If option 2 fails the list, the fallback order is: option 1 for the MVP (as DEC-0157 proposed, accepting that
ordinary apps live in Plasma), then a small wlroots-based stacking compositor that already exists (labwc) with
MIA's shell, before anything is written. **Option 4 is rejected**: it recreates mature infrastructure.

## 4. The session model

**Separate sessions, shared user services.** MIA's session and Plasma are two entries at the login screen for the
same person. Only one runs at a time. They share everything that belongs to the *user* rather than to the *session*:

| Shared (belongs to the user manager) | Per session |
|---|---|
| the MIA Runtime and everything it supervises | the compositor |
| PipeWire, the user's D-Bus, his keyring | the shell (MIA's, or Plasma's) |
| the model server (system-wide) | the capture agent |
| his files and MIA's data | the notification service (Plasma's, or MIA's shell) |
| Flatpak applications' data | open windows |

So MIA's state never depends on which session is showing: a conversation started in MIA's session is there in MIA's
window in Plasma, because both are surfaces of the same runtime. What doesn't carry across is other applications'
open windows; that is true of every desktop, and "offered back at next login" (REQ-UX-024) is Prompt 10's.

**Why not one session with two shells that swap** (which would keep windows open across the switch): it would make
Plasma depend on MIA's session plumbing, and a broken swap would strand both. The approved requirement is that each
is usable without the other. If option 2 is chosen, both sessions use the same compositor *technology*; they are
still separate sessions.

| Event | What happens |
|---|---|
| Login | the login screen (Plasma Login Manager [S12]) starts the chosen session's entry from `wayland-sessions/`; MIA's is the default (REQ-UX-020) |
| MIA's session starts | compositor → `graphical-session.target` → the shell and the capture agent; the runtime was already started by the user manager |
| Switch to the desktop | "Open the desktop" ends MIA's session and starts Plasma for the same user without a second password where the login screen allows it **(to verify, PoC 3)**; otherwise through the login screen |
| Lock | logind's lock signal; the compositor's own locker draws it. MIA's shell never draws a lock screen itself |
| Logout | session clients stop; the runtime keeps running if lingering is on (the Pi always; the PC by choice) |
| Session restore | MIA's shell reopens where it was from the runtime's record of his place; ordinary windows are Prompt 10's |
| Several displays | the compositor's; MIA's shell asks for full screen on the primary and may place panels on others (Prompt 10) |
| Several people | each has their own login, user manager and runtime. Fast user switching works as on any Linux desktop; MIA is for Zac alone today (DEC-0119) and nothing here prevents more |

## 5. Window management and desktop integration: who provides what

| Feature | In Plasma | In MIA's session (option 2) | Needs MIA-specific work |
|---|---|---|---|
| Application windows, switching, tiling, floating, full screen | KWin | KWin | no |
| Multiple monitors, workspaces (virtual desktops) | KWin, Plasma | KWin | no; mapping a *project workspace* onto them is Prompt 10's |
| Panels | Plasma's | MIA's shell (a layer-shell surface) | the shell |
| Notifications | Plasma's service | MIA's shell implements the notification service, feeding the gate for hers and showing others' plainly | yes, small |
| System tray | Plasma's | MIA's shell hosts status items, or shows none in the MVP | later |
| Launcher | Plasma's | MIA's Apps page and search, launching through the applications adapter | the adapter |
| Widgets | Plasma's | MIA's surfaces are her widgets | no |
| MIA inside Plasma | a window, a tray item, the palette hotkey, file-manager entries | | the capture agent; service-menu files |

**The boundary:** MIA's shell is a client. It asks the compositor for a surface like any application and learns
about other windows only through sanctioned protocols. MIA never becomes the window manager in this architecture.

## 6. Recovering from a broken MIA interface without restarting

1. **The shell crashes or shows nothing:** its unit restarts it. A key combination owned by the compositor
   (independent of the shell) opens the session's recovery menu: restart MIA's shell, restart the runtime, open a
   terminal, open the desktop, log out.
2. **The runtime isn't answering:** the shell's local recovery page appears after 30 seconds with the same choices
   and the last lines of the runtime's journal (REQ-UX-022). It needs nothing from the runtime.
3. **MIA's session won't start at all:** the login screen is still there; choose Plasma. Plasma depends on nothing
   of MIA's.
4. **The login screen itself is broken:** a text console (Ctrl+Alt+F3), then the previous deployment at boot.
   Prompt 14 writes the full procedure and the USB recovery path (REQ-OPS-002).

## 7. MIA's shell: its host

The shell needs a browser engine to show `web/`. Provisional choice: the **Qt WebEngine host MIA already has**
(`gui/main_window.py`'s web mode, DEC-0124), cut down to the host alone. Compared with launching a whole browser in
kiosk mode it is one process MIA owns and updates with the image, it can be a layer-shell surface and a tray item
under KWin, and it already exists. Against: Qt WebEngine's engine trails Chromium's by months, and it must be built
for the image's pinned Python. Final in Prompt 10 (T-14).
