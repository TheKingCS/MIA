---
id: K-0325
kind: lesson
title: Two locks taken in both orders: the key's and the security log's
status: confirmed
by: claude
created: 2026-11-22T13:06:51+00:00
concerns: core/at_rest.py, core/security_log.py
from: task:WP-05
---
WP-05. After WP-04 sealed the security log, a thread writing it held the log's lock and then needed the key's lock (to seal the line), while a thread opening the key held the key's lock and then wrote a key problem to the log: two threads could each hold one and wait forever. at_rest._alert now only notes the problem; flush_alerts records it once this thread holds neither lock (RLock._is_owned, security_log.writing()), and SecurityLog.record flushes after letting go. A rule for both: never call out to another locked service while holding your own lock.
