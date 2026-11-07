---
id: K-0078
kind: implementation
title: Cook mode on the glasses: Cooking Now
status: confirmed
by: claude
created: 2026-11-07T18:18:24+00:00
concerns: core/glasses.py, web/glasses.js
from: dec:DEC-0113, dec:DEC-0125
---
The Kitchen card's first menu item on the glasses is Cooking Now (core/glasses._kitchen_cooking). With a recipe cooking it leads with cooking_hero (recipe, Step N of M, the step itself large, each timer's m:ss left or Done) and rows: Next Step (I Made This on the last step, which keeps the usual second press because it logs the meal and uses the pantry), the timer the step offers, Stop for each running timer, Back. Next, Back and the timers are one press (QUICK) like the live workout. Stopping without logging is left to voice and the screen, since it throws the session away. Added cooking.next/back/timer/timer_cancel/made to GLASSES_KINDS.
