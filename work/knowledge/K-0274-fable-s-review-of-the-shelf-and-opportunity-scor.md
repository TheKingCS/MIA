---
id: K-0274
kind: lesson
title: Fable's review of the shelf and opportunity scoring: three fixes
status: confirmed
by: claude
created: 2026-11-16T18:44:21+00:00
concerns: core/shelf.py, core/opportunity.py, web/shell.js, core/ual.py
from: dec:DEC-0174, task:UI-4, task:P3
---
1. A derived capture must carry its sources' sensitivity. core/shelf.combined() gave several entries the source 'mia:shelf', so Capture.sensitive (worked out from source_app and title) was lost and ual.may_offer could offer an online action for text that came from a bank app. combined() now takes the first sensitive entry's source_app and title. Any future function that makes a Capture from other captures must do the same.

2. Reading a price out of free text needs more than a currency sign. opportunity.price_in took the first amount, so 'was $80, now $45' was 80 and '$5 off, $45' was 5, and the second would be judged the lowest seen and recommended 'buy when ready'. With more than one distinct amount it now returns None (the dimension says several amounts were there) and the recommendation falls to investigate. A wrong 'buy' is worse than a missing one.

3. A document-level drop handler takes drops from text boxes unless it leaves them alone: dragover's preventDefault stops the browser inserting dragged words into an input. web/shell.js now ignores drags whose target is an input, textarea, select or contenteditable.

Not changed, noted: the drop overlay still shows over a page's own drop zone (that zone still gets its drop); compatibility is word matching, so 'met' means the spec's words appear, not that the part fits.
