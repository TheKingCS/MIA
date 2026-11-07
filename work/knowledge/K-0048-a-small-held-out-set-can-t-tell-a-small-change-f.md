---
id: K-0048
kind: lesson
title: A small held-out set can't tell a small change from noise
status: confirmed
by: claude
created: 2026-11-07T05:35:25+00:00
concerns: core/model_forge.py, tools/model_forge.py
from: dec:DEC-0106, file:core/model_forge.py
---
What happened: giving the router the person's record names raised it on the choosing half (86% to 87% first pick, 97% to 99% top five) and left it level on the scoring half (81% to 80%, 97% to 95%). With 95 requests, one request is about a point.
What was done: the change was kept, because it was chosen on the choosing half, and undoing it because of the scoring half would make that half choose too. The card reports the scoring half's number as it is.
Lesson: when a change moves a score by a request or two, it hasn't been shown to help or hurt. The cure is more held-out data, which is what the shadow runs on new requests are for.
