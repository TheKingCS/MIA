"""
core.onboarding
==================

The one-time, first-run welcome message injected into a brand-new
user's very first conversation — docs/VISION.md's "interactive
first-time onboarding... MIA teaches herself through real conversation
and real tasks, not docs/slides." See gui/home_dashboard.py's
`__init__` for how this gets injected: right after it creates the
new session's active conversation, gated on a `system.onboarding_shown`
config flag so it fires exactly once, ever, not on every login.

**Deliberately template-based, not an LLM call** — same "start boring,
not clever" reasoning core/startup_briefing.py's own docstring already
established for its own once-per-launch greeting, even more warranted
here: this fires at the single highest-stakes moment possible (the
very first thing a brand-new user ever sees MIA say), so a scripted-
but-warm message beats boot-time LLM latency or a cold/unwarmed Ollama
backend here even more than it does for the daily greeting.

Reuses core.assistant_chat.suggested_prompts_for_module(None) — the
same generic, cross-domain sampler gui/character_panel.py's sidebar
already shows on the Home screen — for "things to try," rather than
inventing a second, driftable list of example prompts.

Pure functions only, no Qt/manager coupling — testable without a real
app (see tests/test_onboarding.py), same shape as core/startup_briefing.py.
"""

from __future__ import annotations

from core.assistant_chat import suggested_prompts_for_module


def build_first_run_welcome_message(user_name: str) -> str:
    """Pure logic — testable without Qt or a real clock."""
    intro = (
        f"Hi {user_name}, I'm MIA — good to meet you. I'm your own personal assistant, and I live right "
        f"here in this app with you, not off in the cloud somewhere."
    )
    prompts = suggested_prompts_for_module(None)
    if prompts:
        examples = "\n".join(f'- "{prompt}"' for prompt in prompts)
        intro += f"\n\nHere are a few things you could try asking me right now:\n{examples}"
    intro += (
        "\n\nOr just start using the app — I'll pick things up as we go. And anytime you want a real "
        'walkthrough of a feature, just ask me something like "teach me how X works."'
    )
    return intro
