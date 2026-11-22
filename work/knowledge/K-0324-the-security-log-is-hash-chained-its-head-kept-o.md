---
id: K-0324
kind: implementation
title: The security log is hash-chained, its head kept on another device
status: confirmed
by: claude
created: 2026-11-22T13:06:51+00:00
concerns: core/security_log.py, server/app.py, web/signins.js
from: task:WP-05, dec:DEC-0254
---
WP-05 (REQ-SEC-034, DEC-0254). Each line holds prev (the line before's h) and h, a SHA-256 over the entry without h as sorted compact JSON (security_log.link/digest). check_chain finds a changed line (its h), one removed or put in (a prev that doesn't match); lines from before the chain come first and are counted; the first chained line's prev isn't checked (trimmed lines). A trim is a log_trimmed line. A chain without a key can be rewritten whole, so web/signins.js keeps the newest h in the viewing device's localStorage and sends it as ?seen= next time; the server answers held or missing, and a missing one is logged (log_changed) and told once per hash. Every SecurityLog on one file shares a lock (_lock_for): at_rest makes its own to note a key problem, and two instances would have chained onto the same line. The trim moved off atomic_write_text (it would put the log in the undo log).
