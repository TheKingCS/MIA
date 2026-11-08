---
id: K-0107
kind: implementation
title: Communications screen
status: confirmed
by: claude
created: 2026-11-08T06:28:52+00:00
concerns: core/web_comms.py, web/communications.js
from: dec:DEC-0129
---
core/web_comms.comms_page gathers what was on four screens: open drafts (sending stays on /api/email/drafts, so MIA never sends and no password enters an action), the mailbox status (web_inbox._email_status), the gate's day (said, held back with reason, limit, breaks), five latest notifications, and people with an email ordered by days since last_contact. The limit and breaks became actions comms.limit / comms.resume; their voice tools already existed.
