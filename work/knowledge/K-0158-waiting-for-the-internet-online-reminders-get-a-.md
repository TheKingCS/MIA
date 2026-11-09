---
id: K-0158
kind: implementation
title: Waiting for the Internet: online reminders get a screen on Notifications
status: confirmed
by: claude
created: 2026-11-09T08:09:15+00:00
concerns: core/online_watch.py, core/web_notifications.py, web/notifications.js
from: dec:DEC-0125
---
The reminders kept by the remind_when_online tool (core/online_watch.OnlineReminders) had no screen. The Notifications page (core/web_notifications.notifications_page) now carries `online` (waiting_for_internet: each reminder with its place and when, and whether MIA is online, offline or not known), shown under the notifications with Add a Reminder and Remove. The changes are actions in core/web_notifications.py: online.remind {what} and online.forget {index} (the store gained listed() and remove()). By index because the reminders have no id; the describe step re-reads the list, so a stale index is refused rather than removing the wrong one.
