---
id: K-0228
kind: implementation
title: UAL U2: MIA in Android's selection menu, a card over the other app
status: confirmed
by: claude
created: 2026-11-15T11:21:15+00:00
concerns: android-phone/app/src/main/java/com/mia/phone/SelectionActivity.kt, web/selection.js, core/ual.py
from: dec:DEC-0165
---
What: android-phone SelectionActivity.kt answers PROCESS_TEXT (the text-selection menu, label "MIA") and SEND text/plain ("Do with MIA"). It starts the phone's engine (Engine.ensure, once per process), then shows web/selection.html in a dialog-themed activity (excludeFromRecents, its own empty taskAffinity) over the calling app, so Close returns there. The page asks /api/ual/offer and /api/ual/run like the PC's Ctrl+K palette: a read action's result shows in the card with Copy; an act action shows its proposal sentence and waits for Yes, then offers Undo.

How the selection travels: through a JavaScript bridge (MIASelection.capture()), never the URL, so it isn't in history, logs or the remembered last page. The address carries only the sign-in token after the # (the same as MainActivity). The card's WebView loads nothing but 127.0.0.1. "Open in MIA" is limited to MIA's own page names (OWN_PAGE) and handed to MainActivity as an extra.

Why sensitivity grew: the phone names the source as android:<package> and the app's label as the title. core/ual.Capture.sensitive now also matches words in those (bank, pay, wallet, health, pharmacy, password, authenticator, vault, journal...): a selection from such an app never gets an online or cloud action. The word list only narrows what may leave the device; online stays off until the person turns it on, so a missed app is still safe by default. Package ids alone often don't say (com.chase.sig.android), which is why the app's label is checked for phone captures; a web page's title is not (a browser page titled "Pay your bill" isn't made sensitive by that).

Not done: the selected text in the other app is never replaced (no setResult with EXTRA_PROCESS_TEXT) until a convert action exists and the person picks "replace". Kotlin isn't compiled in the cloud container; the phone CI build is the check.
