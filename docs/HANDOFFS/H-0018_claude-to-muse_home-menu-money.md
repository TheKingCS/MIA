# H-0018: Home is MIA again, a ⋯ menu, and Money is complete
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-06
- Related: DEC-0017 (amended), H-0017

## Context

Zac, in chat with Claude, 2026-10-06 (recorded as a DEC-0017 amendment):
- "I really liked the homepage being centered on just mia's face and the ability to chat with her."
- The dashboard should be "some kind of a separate dashboard page".
- The navigation should be "a button with like three dots that expands and shows the choices".

## What changed in your files

- **Your presence page is the Home again (`web/index.html`).**
  - I removed the seven module links under Briefing, because the menu replaces them, and added a "Dashboard" link.
  - It loads the frame with `<script src="shell.js" data-frame="web_home" data-talk="own">`. That gives it the ⋯ menu and no floating Talk, since it has its own.
  - Nothing else changed.
- **The dashboard moved to `dashboard.html`**, with its data from `MIA.dashboard()`.
- **The ⋯ menu (in `shell.js` and `shell.css`)**: one round button, top left. It opens every app as a grid of tiles, with level and XP and a link to the apps still on the PC.
  - It shows on phones on every page, and on Home at any size.
  - Desktop module pages keep your sidebar.
  - The phone's sideways rail is gone. Zac found the wrapped version clunky.
- **Money is complete: `money.html` and `money.js`.**
  - It covers everything the PC's Budget screen does, apart from connecting and syncing a bank, which needs the vault passphrase.
  - Every change goes through a confirm with the engine's own sentence, and can be undone.
  - The forms come from the engine's field lists, through `MIAShell.form(title, fields, values)`, which any screen can use.
  - `finances.html` now just redirects to it.
- **Your static sidebar links** now say "Money → money.html". The frame replaces them at runtime anyway.

## What's needed from you
- The look of the ⋯ button and menu, the Money screen, and the form dialog, against the concept.
- On the phone, Money's eight tabs wrap onto three lines. A scrolling tab bar or a picker might be better; your call.

## Acceptance criteria
- Home stays MIA's face and chat; every page reaches every app through ⋯ on a phone.
- Money keeps working end to end (add, edit, pay, delete, undo) after any restyle.
