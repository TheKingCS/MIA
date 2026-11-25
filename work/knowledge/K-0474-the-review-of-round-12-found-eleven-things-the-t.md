---
id: K-0474
kind: lesson
title: The review of round 12 found eleven things the tests passed
status: confirmed
by: claude
created: 2026-11-25T03:06:24+00:00
concerns: core/fishing_times.py, core/sun_moon.py, core/hen_laying.py, core/tax_setaside.py, core/harvest_log.py, core/outdoor_work.py, core/weather_watch.py
from: file:core/fishing_times.py, file:core/hen_laying.py, file:core/tax_setaside.py
---
A fresh reviewer read the nights commits (03a50439..e6018c2e) and ran code: the moon said a new moon today the day after one (two days in a row could qualify; now is_the_day, one day only, shared by phase_word and next_moons); the sun-and-moon reply had two phase readings that disagreed; the garden and greenhouse lettuce were two rows; a flock that came 10 weeks ago was said to be 10 weeks old; Tampa got short days in June (short days now judged by the places own year); 1040-ES dates never moved off weekends or MLK and Emancipation Day; Windows gives a fixed UTC offset for now, so a week across a clock change was an hour off (now each days noon offset); will the pipes freeze went unanswered on a mild night; do I need to water the tomatoes and pea plants missed; a stale forecast was read as today; and astral sun() fails whole far north in summer (sunrise and sunset now asked separately). The node harvest ref now carries its time so a rebuilt node database does not hide new harvests. Lesson: date, zone and astronomy code needs a reviewer who runs edge dates.
