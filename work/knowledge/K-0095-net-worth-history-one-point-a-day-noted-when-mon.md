---
id: K-0095
kind: implementation
title: Net worth history: one point a day, noted when Money is read
status: confirmed
by: claude
created: 2026-11-07T15:27:32+00:00
concerns: core/net_worth_history.py, core/web_money.py, web/money.js
from: commit:69b2bcf, dec:DEC-0113
---
Money's Overview needed a line (DEC-0113 canvas), but MIA only knew net worth now (core/finance_summary._net_worth). core/net_worth_history.py keeps one point a day (the last reading wins, two years kept) in a household store beside the budget (and the person's own with a private budget). It is noted from core/web_money.money_page and writes only when the day's point is new or changed, because every atomic write bumps /api/live and a write on every read would make the page re-read itself forever. Days nobody looked at have no point; nothing is filled in. The change this month is today less the month's first point (or the last before the month), None with nothing to compare. The web only draws the line (web/money.js nwLine); a dip shows plainly in grey, never red (DEC-0014).
