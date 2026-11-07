# MIA's browser (DEC-0117)

MIA has a web browser of her own. She can read and move around the web by
herself, and she stops for your OK before anything that commits. You teach
her a task by doing it once while she watches. She then does it again with
you, and once two runs in a row go cleanly she calls it learned.

## What she uses

**Inside MIA** (2026-11-07): her Edge runs with no window of its own, at a
fixed 1280 x 800 page, and the Browser page shows it live (a picture about
once a second, `/api/browser/frame`). You work it from the picture: a click
lands on the same spot in the page, the box under it types, the key buttons
press Enter, Tab and the rest, the mouse wheel scrolls (`/api/browser/input`,
`Browser.person`). These are your own hands, so no gate applies, and what
you type there is never counted as words she may type later. Teaching
records them exactly as it records a window. `browser.own_window: true`
brings back a separate Edge window on the PC.

- **Her own Edge profile.** Playwright drives Microsoft Edge in a profile
  kept in the person's own folder (`data/profiles/<id>/browser/profile`).
  It has none of your own Edge sign-ins, history or saved passwords. When a
  site needs you signed in, you sign in yourself in her window; that site
  then stays signed in for her, and only in her profile.
- You can always see what she's doing and take over: in the live view on
  the Browser page (or her own window, with `browser.own_window`).
- Only web addresses (http and https). A file, `javascript:`, `data:` or
  `edge://` address is refused, never sent to a search.

## What she does alone, and what waits for you

`core/browser_safety.py` sorts every step in code, never by the model:

| Level | Examples | What happens |
|---|---|---|
| read | open, search, read, scroll, back, screenshot | she does it |
| act | follow a link, type in an ordinary field, pick from a list, a button that only shows/opens/searches | she does it |
| commit | submit, buy, pay, order, send, post, sign in/up, delete, download, upload, accept, subscribe, save; Enter in a form; any button that isn't plainly harmless | waits for you |
| never | password, PIN, one-time code, card, bank account, SSN, licence or passport field | refused: you type these yourself |

Anything unclear counts as a commit, never as a harmless step. A step that
waits becomes the action `browser.commit`, with a screenshot of the page.
You approve it on a screen (the web's actions) or by saying "yes" right
after she names the button (`core.browser.yes_to_waiting`, handled in
`core/talk_it_out.py`). The model can't approve anything. If the page
changed after she asked, or the button is gone, nothing is pressed. A step
nobody approves is let go after 30 minutes.

Text read off a page is framed as content from the web
(`browser_safety.untrusted`): information, never instructions to her. If a
page tells her to press Buy, the commit check still holds.

## Teaching her a task

1. "Open the county tax site" (her window opens on it).
2. "Learn this: pay the property tax." She watches.
3. You do the task in her window. She notes each click, typed field and
   choice by its label. Wherever you typed a password, she keeps only the
   step "sign in"; what you typed is never kept.
4. "Done." She keeps the task (`browser_routines.json` in your folder), each
   step with the page title it should lead to.
5. "Do pay the property tax." She opens the starting page and goes step by
   step. She stops for you at each sign-in and each commit, then carries
   on. If a button is missing or a page isn't the one expected, she stops
   and says where.
6. Two clean runs in a row: learned. The `browser.runs` loop watches how
   often taught tasks finish cleanly and offers to relearn ones that stop.

## Tools (domain `browser`, never offered to a child)

`browse`, `browser_read`, `browser_click`, `browser_type`, `browser_back`,
`browser_close`, `learn_browser_task`, `do_browser_task`,
`list_browser_tasks` (`core/assistant_browser_actions.py`).

## Only your words go out (DEC-0122)

A page could try to talk the model into typing something MIA knows about
you into a field or a search (a request that sends it to that site before
any commit button). So she types, chooses or searches on her own only
words that came from you: every word must be in what you said to her in
the last 30 minutes (`Browser.hear`, fed each turn by
`core/talk_it_out.pre_turn`, never a private journal turn), or be part of a
task you taught her by doing it. Anything else (words she composed,
something from her memory, a search you didn't word) waits for your OK
with the exact text shown: "type "..." into "Search"", or "Open
https://...". A plain address with no query passes; one carrying data
after a `?` follows the same rule.

## Known limits

- The rule checks words, not meaning: "Feb 3" said and "02/03" typed is a
  new word, so it asks. Better to ask than to guess.
- She can open local-network addresses (a router's page, for example). She
  can't press anything that commits there without you.
- A replay finds controls by label and role. A site that renames its
  buttons stops the run, and you show her again.
- One Playwright worker thread per person's session. The Qt app closes every
  window when it quits.
