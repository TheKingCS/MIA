"""
tools.export_state
====================

Print (or save) a person's Life State v2 as JSON, computed from their
data (core/context_assembler.py), checked against the published schema
(docs/schema/life_state.schema.json). Engine Phase 1, 2026-10-05.

    python -m tools.export_state                 # the only (or first) person
    python -m tools.export_state --who robin@example.com --out state.json

Read-only: it changes nothing. Run it on the device that has the data;
the output holds that person's real information, so keep it out of git
(data/ and *.state.json are ignored).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def export(context, who: str = "", today: date = None) -> dict:
    """The Life State for `who` (an email, a name or a profile id; empty:
    the active person, else the only or first one). Raises LookupError."""
    from core.context_assembler import assemble_life_state_v2
    from core.personal_data import view_for

    profiles = context.profiles
    if who:
        profile = profiles.find_for_sign_in(who) or profiles.get_profile(who)
    else:
        profile = profiles.get_active_profile() or next(iter(profiles.list_profiles()), None)
    if profile is None:
        raise LookupError(f"No one called '{who}' on this MIA." if who else "No one has an account on this MIA yet.")
    return assemble_life_state_v2(view_for(context, profile.profile_id), today)


def main(argv=None) -> int:
    from core import schema_check
    from core.config_manager import ConfigManager
    from core.core_runtime import build_core_context
    from core.event_bus import EventBus

    parser = argparse.ArgumentParser(description="Print a person's Life State as JSON.")
    parser.add_argument("--who", default="", help="Email, name or profile id (default: the only or first person).")
    parser.add_argument("--out", default="", help="Save to this file instead of printing.")
    args = parser.parse_args(argv)
    context = build_core_context(ConfigManager(), EventBus())
    try:
        state = export(context, args.who)
    except LookupError as problem:
        print(problem, file=sys.stderr)
        return 1
    problems = schema_check.errors(state, schema_check.load("life_state.schema.json"))
    text = json.dumps(state, indent=2, ensure_ascii=False)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    for problem in problems:
        print(f"Schema: {problem}", file=sys.stderr)
    return 2 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
