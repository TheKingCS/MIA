---
id: K-0266
kind: implementation
title: DEC-0196, one browser: everyday mode, her own tab, private sites
status: confirmed
by: claude
created: 2026-11-16T10:16:41+00:00
concerns: core/browser.py, core/assistant_browser_actions.py, core/web_account.py, core/person_settings.py, core/grants.py, apps/browser/manifest.json, docs/BROWSER.md, tests/test_browser.py
from: dec:DEC-0196, dec:DEC-0117, dec:DEC-0122
---
What: core/browser.py. Per-person settings browser.everyday and browser.sensitive_sites (PERSONAL_SETTINGS; Settings › Browser rows). Everyday mode: _Worker launches the persistent context headed, with ignore_default_args=EVERYDAY_DROPS (exact strings taken from Playwright 1.64's chromiumSwitches: --enable-automation, --disable-sync, --disable-extensions, --disable-component-extensions-with-background-pages, --disable-component-update, --disable-background-networking, --disable-client-side-phishing-detection, --disable-popup-blocking, --disable-default-apps, --password-store=basic, --use-mock-keychain) and downloads allowed; she opens her own tab (context.new_page()) instead of pages[0], and _page reopens one of hers, never his. EdgeDriver.take_over picks the tab with document.hasFocus() (Browser.take_over; tool take_over_tab, tagged outside text in apps/browser and grants.FRAMED_TOOLS since it returns the page). Private sites: Browser.withheld() replaces a sensitive site's text in read() and glance() with a sentence unless asked_now(): the person said a reading word plus the site's name or "this page" within ASKED_SECONDS (120), from the existing `heard` list. Tools private_sites and use_everyday_browser.

Why this way: Chromium refuses automation of the default profile, so the only safe 'same browser' is MIA's profile becoming his (Q-45, DEC-0196). Playwright's defaults are for tests and would silently weaken a person's browser; dropping only those switches keeps the pipe connection Playwright needs (ignore_default_args=True would risk losing it). --disable-features=... has a computed value and isn't dropped.

Not verified yet (needs the PC): that sync and sign-in work under automation, the automation infobar, that InPrivate windows aren't in the persistent context's pages, and document.hasFocus() picking the right tab. Recall indexing doesn't exist yet: 'never kept for search' must be enforced when it's built (is_sensitive is the check to use).
