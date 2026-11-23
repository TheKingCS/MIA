---
id: K-0360
kind: lesson
title: A safety dose must round up, and a food word match must be whole
status: confirmed
by: claude
created: 2026-11-23T21:12:39+00:00
concerns: core/eng_calcs.py, core/quantities.py, core/preparedness.py, core/feed_runway.py
from: commit:d7fb1eac
---
Fifth fresh review (2026-11-23): the water-bleach calculator used round() with no floor, so a cup of water got 0 drops and was said treated; now ceil and the EPA minimum of 2 drops, with the CDC double dose for water still cloudy, and kitchen volumes (qt, pt, cup, floz) added to core/quantities.py. food_days matched staples as substrings (collard greens as lard, goat as oat, green beans and oat milk as dry staples): now whole words with a not-a-staple list for wet, canned and drink forms. feed_runway ignored a bag logged without pounds (said run out the day after buying), counted same-day bags apart, and kept an old small flock rate: now same-day purchases are one, the last one without pounds is unknown, and his rate uses the last 90 days after the flock last changed, never under half the usual.
