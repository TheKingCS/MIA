---
id: K-0351
kind: implementation
title: Catch me up leads with what needs him
status: confirmed
by: claude
created: 2026-11-23T18:04:39+00:00
concerns: core/needs_now.py, core/assistant_tools.py
from: commit:29396ed9
---
core/needs_now.py gathers three things before the life state: needs-you-now (greenhouse_link.state's open critical/warning alerts once taken over; weather_watch from the KEPT forecast only, never fetched in a turn; update_notice.waiting), what the gate holds (CommunicationGate.pending titles), and change_history.find over the last 24 hours filtered to by == 'mia'. Each source is wrapped so one failure never empties the report; describe() returns '' on a quiet day so the old report reads unchanged.
