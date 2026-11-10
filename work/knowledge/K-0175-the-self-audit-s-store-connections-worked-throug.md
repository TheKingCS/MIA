---
id: K-0175
kind: implementation
title: The self-audit's store connections, worked through
status: confirmed
by: claude
created: 2026-11-09T09:30:28+00:00
concerns: core/self_audit.py, core/trade_session.py, core/trade_actions.py, core/life_areas.py, tests/test_life_areas.py, tests/test_trade_session.py
from: file:core/self_audit.py, file:core/trade_session.py, file:core/life_areas.py
---
2026-11-09. The interconnection audit listed seven stores with no history: cooking, connections, net_worth, lite_captures, finance, homestead and memory_vault. None of them was a real gap. Each holds machinery or a copy, and what it stands for is already kept elsewhere: the meal cooked is the kitchen's meal_logged, an accepted capture is a journal entry, imported snapshots have their source's own history, and the photo vault is a backup. So they went into core/self_audit.py's BY_DESIGN table, each with its reason, rather than getting events nobody would read. The audit also listed trade_session, which was real: trade_finished and trade_stopped were recorded by core/trade_actions.py, so the store's own file never showed it. TradeStore.save() now records a session it finishes or stops, once: it remembers the status it last read or wrote, so saving again records nothing more. The greenhouse was missing from the life state, so core/life_areas.py has a homestead area: the systems reporting and the critical alerts from the export's summary.critical_alert_count (homestead/viewer/export_home_snapshot.py writes it), named as what's next when any are open. What's left is the 'links' column: link kinds for records nobody yet links to.
