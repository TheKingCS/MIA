# H-0050: Journal, Workshop, Expeditions, Music and Files on the web; Home replaces the Dashboard

- From: claude → muse (cc zac)
- Date: 2026-10-16
- Status: built and pushed; the look is yours to polish
- Note: numbered H-0050 because H-0049 was used twice (one each way) the same day.

## What changed

**Five apps that only opened a chat now have working screens** (Zac: "they
are empty right now and just bring up a chat with MIA"):

| App | Page | What it does |
|---|---|---|
| Journal (was Notes on the web) | `web/journal.html` | Entries newest first, search, tag filter, Write Entry, open to read, Edit, Delete. Talk It Out opens the chat to journal with MIA; those private entries stay encrypted and are only counted here. |
| Workshop | `web/workshop.html` | Tabs Jobs, Materials, Products, Parts, Money. + / − stock, a job's Used Material and Made Product, Sell (logs the sale, takes it out of stock), sales/costs/profit. |
| Expeditions | `web/expeditions.html` | Happening Now / Coming Up / Past cards; one opens to its trips with Start/Finish, the packing list (tap to pack) and Add. |
| Music | `web/music.html` | Songs (search), Playlists, Artists. Songs play in the browser, streamed from MIA. Scan Library. |
| Files | `web/files.html` | The person's own MIA files folder: Upload, New Folder, Open (pictures, PDFs, songs, text show in place), Rename, Delete. Never the computer's whole disk: the server can be reached from the phone. |

Data: `core/web_more.py` (one assembler each), actions: `core/more_actions.py`,
files: `core/my_files.py`. The phone's engine now also builds the Workshop
and Music stores (`core/core_runtime.py`). Examples for the preview:
`docs/schema/{journal,workshop,expeditions,music,files}.example.json`.

**Home replaces the Dashboard** (DEC-0027): Home is greeting, Today's Focus,
Upcoming and the level card; no quick buttons, no date; MIA's badge opens
the chat. The bottom bar is Home and Apps.

## For you (look only)

- New classes, all on tokens, at the end of `web/concept.css`:
  `.journal-*`, `.trip-*`, `.gear-*`, `.music-*`, `.file-*`.
- Hero art: these pages use the shared hero; `mod-notes`, `mod-workshop`,
  `mod-expeditions`, `mod-music`, `mod-files` are on `<body>` if you want
  per-app imagery.
- Checked at 412 px: no page scrolls sideways.
