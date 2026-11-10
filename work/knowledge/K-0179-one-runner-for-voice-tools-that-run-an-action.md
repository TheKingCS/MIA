---
id: K-0179
kind: implementation
title: One runner for voice tools that run an action
status: confirmed
by: claude
created: 2026-11-09T10:16:59+00:00
concerns: core/actions.py, core/assistant_health_actions.py, core/assistant_asset_part_actions.py, core/assistant_proposal_actions.py, core/assistant_goods_actions.py
from: file:core/actions.py
---
2026-11-09, from the self-audit's same_body findings. Nine assistant_*_actions modules each had their own _run, and they came in three versions. Three (asset parts, health, proposals) called execute without describe, so a voice tool skipped the checks the screen makes before an approval. Two (goods, cooking) also caught a store's ValueError, and the rest let it raise. core.actions.run_as_tool now does it once: describe, then execute, and any ValueError (ActionError is one) comes back as words. Each module's _run keeps its docstring and hands off to it. The suite passed unchanged. Left as they are on purpose: the 3-to-8-line helpers duplicated across a few stores (_in_range, _save_usage_log, _load_file), which the repo's 'a sibling, not a shared abstraction' convention keeps apart (see core/finance_manager.py), and the garage, greenhouse and property Qt modules, which can't share code because modules never import each other.
