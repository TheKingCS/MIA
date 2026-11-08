---
id: K-0083
kind: implementation
title: Notifications on a page, with why each was sent
status: confirmed
by: claude
created: 2026-11-08T00:46:04+00:00
concerns: core/web_notifications.py, core/assistant_notification_actions.py, web/notifications.js
from: dec:DEC-0125, dec:DEC-0014
---
web/notifications.html (from Settings) shows core/web_notifications.notifications_page: each notification newest first with a tone from its level (amber warning, red only for an error, DEC-0014), its source, when, read or not, and for a message MIA sent on her own, the communication gate's reason (matched by the gate log's notification_id, said by core/message_reasons.explain), so 'why did you tell me that?' has an answer on screen. notification.read_all and notification.dismiss are actions (a dismissal still publishes notification.dismissed, which the gate learns from); list_notifications and mark_notifications_read are the voice side.
