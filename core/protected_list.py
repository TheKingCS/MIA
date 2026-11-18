"""
core.protected_list
=====================

What MIA can never change about herself, in words (DEC-0225; Zac, 2026-11-17, Q-78: "show me the list, and add grants,
the stop, browser safety and her inspection to it"). The list itself is `core.dev_lab.PROTECTED`: a lab change that
touches any of it is refused before it's tested, whoever wrote it. This module only says it plainly.

`GROUPS` sorts every protected path into a group with a plain name and why it's there; `tests/test_protected_list.py`
fails on a protected path no group names, and on a named safeguard (`SAFEGUARDS`) missing from the list, so the words
and the rule can't drift apart (R-56). Shown on Diagnostics ("What I Can Never Change") and said by the tool
`what_i_cant_change`.

Pure logic. This file is on the lab's protected list.
"""

from __future__ import annotations

# (group, why, the protected paths in it), in the order they're shown.
GROUPS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("My safety rules", "how I handle a crisis, and what children can see",
     ("core/safety_floor.py", "core/safety_escalation.py", "core/child_accounts.py")),
    ("What I may do on my own", "every change goes through one contract, with its tier and your grants, and can be "
     "undone; how far each kind of change reaches",
     ("core/actions.py", "core/undo_log.py", "core/grants.py", "core/kind_grants.py", "core/action_effects.py",
      "apps/*/manifest.json", "core/app_registry.py", "core/taught_skills.py", "core/grant_actions.py",
      "core/person_settings.py")),
    ("How you say yes", "the approval card, the words that approve by voice, and the turn they're heard in",
     ("core/spoken_approval.py", "core/quick_commands.py", "core/assistant_turn.py", "web/mia.js", "web/shell.js")),
    ("What runs by itself", "my scheduled jobs and their timing", ("core/background_jobs.py", "core/scheduler.py")),
    ("The tests that judge a change", "the suite's own settings; and a change of mine may add tests but never "
     "delete one", ("pytest.ini", "tests/conftest.py")),
    ("Your stop", "\"stop everything\" and what it holds", ("core/stop.py",)),
    ("My browser's safety", "what I may press on a site, and that secret fields are never typed",
     ("core/browser_safety.py",)),
    ("Your secrets and accounts", "passwords, vaults, keys, bank linking, email sending and sign-in",
     ("core/secrets_manager.py", "core/password_vault.py", "core/memory_vault.py", "core/plaid_manager.py",
      "core/mail_send.py", "core/home_link.py", "core/web_account.py", "core/first_account.py",
      "core/account_data.py")),
    ("How I speak up", "the gate every unprompted message goes through", ("core/communication_gate.py",)),
    ("How I'm run", "the server, how I start, my installation, settings, data and phone app",
     ("server/app.py", "main.py", "deploy/", ".github/", "config/", "data/", "requirements.txt", "android-phone/")),
    ("Your decisions", "the decisions log only you approve", ("docs/DECISIONS.md",)),
    ("The lab and its rules", "how my changes are made, checked, merged and undone, and this list",
     ("core/dev_lab.py", "tools/lab.py", "core/lab_actions.py", "core/self_merges.py", "core/self_repair.py",
      "core/protected_list.py")),
    ("What judges me", "who reviews work, my grades, my benchmarks, what my loops watch, and Claude's inspection of "
     "my models",
     ("core/work_review.py", "core/work_agents.py", "core/work_loop.py", "core/work_tasks.py", "core/work_activity.py",
      "core/dev_store.py", "core/dev_usage.py", "core/council.py", "core/council_floor.py", "core/work_runner.py",
      "core/dev_knowledge.py", "tools/work.py", "tools/dev_window.py", "work/", "core/dev_ledger.py",
      "core/mia_coder.py", "core/dev_map.py", "core/loops.py", "core/night_school.py", "core/loop_coverage.py",
      "tools/night_school.py", "core/dev_checks.py", "core/corrections.py", "core/benchmarks.py",
      "tools/weekly_bench.py", "core/capability_gaps.py", "core/model_inspection.py")),
    ("How what I make is checked", "the rules my creations, workflows and imports are published by",
     ("core/creation_spec.py", "core/creation_actions.py", "core/creations.py", "core/record_sets.py",
      "core/creation_sources.py", "core/workflows.py", "core/record_import.py", "core/good_news.py")),
)

# Safeguards that must stay on the list, whatever else changes (R-56).
SAFEGUARDS = ("core/safety_floor.py", "core/actions.py", "core/grants.py", "core/kind_grants.py", "core/stop.py",
              "core/browser_safety.py", "core/action_effects.py", "core/model_inspection.py", "core/dev_lab.py",
              "core/communication_gate.py", "core/mail_send.py", "core/self_merges.py")


def groups() -> list[dict]:
    """The groups for a screen: [{name, why, count}], only the paths still on the lab's list counted."""
    from core.dev_lab import PROTECTED

    on = set(PROTECTED)
    return [{"name": name, "why": why, "count": sum(1 for p in paths if p in on)} for name, why, paths in GROUPS]


def unnamed() -> list[str]:
    """Protected paths no group names (a test keeps this empty)."""
    from core.dev_lab import PROTECTED

    named = {p for _n, _w, paths in GROUPS for p in paths}
    return [p for p in PROTECTED if p not in named]


def said() -> str:
    """The list in words, for voice."""
    names = [g["name"].lower() for g in groups() if g["count"]]
    return ("I can never change these parts of myself, whoever writes the change: " + "; ".join(names) + ". "
            "A change that touches any of them is refused before it's even tested.")
