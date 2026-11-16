---
id: K-0246
kind: implementation
title: M4, first part: every capability's tier in its manifest, and a grant check that only watches
status: confirmed
by: claude
created: 2026-11-16T03:21:56+00:00
concerns: core/grants.py, core/app_registry.py, tools/app_manifests.py, core/actions.py, core/taught_skills.py, tests/test_grants.py
from: dec:DEC-0156, dec:DEC-0178, dec:DEC-0173
---
What: core/grants.py holds the five tiers (observe, suggest, act_within_grant, act_with_approval, never), the pure decide(tier, initiator, granted) and observe(), a report-only hook called from actions.run_as_tool. Each manifest's capabilities gained tiers ({tool or action kind: tier}) and outside ([tools whose answers carry outside text]); permissions gained stores.write:<store> for each store the app owns. app_registry._tier_problems refuses a capability without a tier, a kind that always asks (taught_skills.always_asks) tiered below the person's yes, an owned store without its permission, and any difference between the tagged outside tools and tool_loop.OUTSIDE_TOOLS | grants.FRAMED_TOOLS.
Why this way: DEC-0156 is proposed, not approved, so nothing may be refused yet; declaring and watching changes no behaviour and makes the later switch small. Tiers live in the manifest (one record per app, DEC-0175) rather than a second table; always_asks stays the one classification of consequential kinds, with a test keeping the tiers in agreement. Tiers were generated once from rules (default_tool_tier, default_action_tier) and are hand-kept after: write --force keeps a decided tier and gives only a new capability the rule's.
What to know: the tool rule goes by the name, so a read named like a change (world_finds, look_up_online, browser_read) and a draft named like a send (draft_email) were corrected by hand (TOOL_TIER). The initiator at run_as_tool is MIA only inside a skill step the person hasn't said yes to (taught_skills.in_unapproved_step); there the skill counts as the grant, so the hook reports exactly what the skill's own guard already stops. Network and device permissions are not declared yet.
