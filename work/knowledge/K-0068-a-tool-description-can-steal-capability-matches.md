---
id: K-0068
kind: lesson
title: A tool description can steal capability matches
status: confirmed
by: claude
created: 2026-11-07T17:06:58+00:00
concerns: core/capabilities.py, core/assistant_records_actions.py, core/web_surfaces.py
from: dec:DEC-0125, commit:5003931
---
Adding the files domain (find_my_files, DEC-0125) made "file my taxes" answer Files instead of Compliance: core/capabilities.can_i scores an app by its name, what, ask and every tool description, and words are stemmed (file, files, filed all become fil). Files already tied Compliance on name and what; one more "files" in the tool text and the example ask tipped it. Fixed by keeping the stem out of the tool description and the ask. When giving an app new tools, run tests/test_capabilities.py and check the ask examples there still land where they should.
