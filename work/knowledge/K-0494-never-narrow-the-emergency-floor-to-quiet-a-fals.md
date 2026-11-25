---
id: K-0494
kind: lesson
title: Never narrow the emergency floor to quiet a false alarm
status: confirmed
by: claude
created: 2026-11-25T15:21:43+00:00
concerns: core/first_aid_floor.py
from: commit:7999ffa6
---
Twice in one day (the eighth and ninth reviews, 2026-11-25) narrowing core/first_aid_floor.py words to stop false alarms (mom passed out the cookies; the movie had gushing blood) silenced real emergencies: grandma fell off the horse and is not breathing, dad has collapsed, my stepdad collapsed, he cut his finger off a minute ago help. The floor is a floor: a false alarm costs one careful message with the number, a miss can cost a life. It was restored to the wide version, and tests/test_first_aid_floor_never_misses.py lists every real phrasing found; it only grows. Any change to the floor must pass it, and should only ever widen.
