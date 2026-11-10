---
id: K-0178
kind: implementation
title: The self-audit's interconnection list, finished
status: confirmed
by: claude
created: 2026-11-09T10:11:07+00:00
concerns: core/business_use_actions.py, core/saga_actions.py, core/progress_history.py, core/self_audit.py, core/web_equipment.py, core/chronicle.py, web/asset.js, web/chronicle.js, core/web_more.py
from: file:core/business_use_actions.py, file:core/saga_actions.py, file:core/progress_history.py, file:core/self_audit.py
---
2026-11-09, the fourth pass (16 open, now 0). Business use was voice-only. core/business_use_actions.py now adds asset.business_use_log (Log Use) and asset.business_use_remove, plus page_section(), which the asset page shows in its Costs tab: the worksheet's figures, this year's jobs, the first note on anything uncertain, and 'records and arithmetic, not tax advice'. Business use is also an adults-only life area. The moments kept for the Chronicles had no screen. core/saga_actions.py adds saga.mark and kept_moments(), and the Chronicle page has a Kept tab; only 'series' approves a moment, and a child has none, as by voice. The new action family needed a loop, so the Chronicles loop covers action:saga. profile.prestiged and profile.reward_unlocked had no listener. core/progress_history.py hears both and records into the profile's own data_dir, so a reward earned from the phone is theirs, with the reward named from its tier. The other five unheard events are announcements with no consumer yet, or already recorded directly, so they are in self_audit.EVENTS_BY_DESIGN with exact reasons. Note the device events are announcements, not screen refreshes: nothing subscribes to them. Health, the ID wallet and memories are in BY_DESIGN for links, because links.json is one per household and a link names its record. The workshop page's store lookups were a generator, which the audit's text match couldn't see; they are spelled out now.
