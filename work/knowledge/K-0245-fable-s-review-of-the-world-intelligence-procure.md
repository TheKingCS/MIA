---
id: K-0245
kind: lesson
title: Fable's review of the World Intelligence, Procurement, Living System and registry work: what was wro
status: confirmed
by: claude
created: 2026-11-16T03:15:11+00:00
concerns: core/communication_gate.py, core/world_intel.py, core/good_news.py, core/tool_loop.py, core/product_specs.py, core/price_book.py, core/app_ecosystem.py, web/shell.js, core/requirements.py, core/price_actions.py, core/world_intel_actions.py
from: dec:DEC-0174, dec:DEC-0173
---
Reviewed queue items 1-13 (DEC-0174). Defects found and fixed, each with a test:
1. Outside text: a find's link came from a feed or search result and was used as a page link unchecked; the finds tool wasn't listed as outside text (its answer is said to the person, not read back by the model in the same turn, because its name makes it run as a change: so nothing was steered, and nothing guarded it). Now core/good_news.web_link keeps only http(s), web/shell.js el() refuses javascript:, vbscript: and data: as a link (data: stays allowed as a picture source), and world_finds is in tool_loop.OUTSIDE_TOOLS.
2. Learned pace: note_engagement by notification id marked one log entry though a digest carries several; not_for_me was recorded as opened (engaged). Now every entry of the notification is marked, and passed_at lowers the pace without counting toward a pause.
3. product_specs.models took any letters-and-digits token as a model number, so 120VAC made a pump and a fan identical and price_book.product_key merged their histories. Measurement, size and count tokens are excluded.
4. app_ecosystem.health called Registry.problems(), which builds parity.desktop_registry() (a whole MIAApplication's tools, importing Qt) on every Apps page load and check_my_apps: slow, 300 log lines, and impossible on the phone. The running check reports load problems and failing jobs only.
5. MIA's own watches required every word of a record's name, common words included.
6. requirements._apply and price trip figures accepted zero or negative numbers.
Pattern worth keeping: text or links from a feed, a search or a page are outside text wherever they end up (a page attribute, a tool result, a store), not only where they are first read.
