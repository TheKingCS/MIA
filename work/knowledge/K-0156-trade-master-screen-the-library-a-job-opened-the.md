---
id: K-0156
kind: implementation
title: Trade Master screen: the library, a job opened, the walkthrough, and the glasses' job panel
status: confirmed
by: claude
created: 2026-11-09T08:03:43+00:00
concerns: core/web_trades.py, web/trades.js, web/trades.html, core/glasses_cards.py, core/glasses.py
from: dec:DEC-0149
---
web/trades.html (core/web_trades.py, GET /api/trades?item=) shows every job and diagnosis by trade, one opened whole (scope, permit, hazards, wear, tools, materials, phases with hold points, stop rules, sources) with Start It and Make It a Mission, and the walkthrough when one is going: the step large, why, watch for, the hold (amber until checked), the phase strip, and Checked / Next Step / Back / Stop, or Yes / No for a diagnosis. Every press is a trade.* action, so the holds are enforced in core/trade_session.py exactly as by voice; the page never decides whether you may go on. On the glasses the Workshop card gained 'The Job' (core/glasses_cards._trade_job): Next is only offered once an open hold is checked, Stop is always there, and why goes last so the five lines never drop Stop. The card truncates a long step at about 44 characters, so the step is split over two lines; the rest is a word away by voice.
