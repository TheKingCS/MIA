"""
tools.model_forge
===================

MIA's model forge from the command line (DEC-0106; core/model_forge.py).

    python -m tools.model_forge router     train the tool router and print its card
    python -m tools.model_forge list       every model she has made, with its scores
    python -m tools.model_forge needs      the issues (loops slipping) a model of hers could help with

The router learns from the desktop tools' own words and is tested on the
routing corpus (tests/assistant_routing_corpus.py), which it never sees in
training. The keyword router's share on the same requests goes on the card
for reference.
"""

from __future__ import annotations

import sys


def _router() -> int:
    """Trains the router, prints its scores and its first misses."""
    import logging

    logging.disable(logging.INFO)  # building the registry logs every tool it registers
    from core import model_forge
    from tests.assistant_registry import build_desktop_registry, demo_context, offered_tools
    from tests.assistant_routing_corpus import CORPUS, INFO

    registry = build_desktop_registry()
    context = demo_context()  # the sample household's records, so "the peppers" names a Maintenance one
    held_out = [model_forge.Example(said, tool, tuple(sorted(registry.named_domains(said, context))))
                for said, tool in CORPUS if tool != INFO]
    _choose, report = model_forge.split(held_out)
    offered = sum(e.label in offered_tools(registry, e.text, context) for e in report)
    print("Training (a few settings, about half a minute)...")
    card = model_forge.forge_router(registry._actions.values(), held_out,
                                    baseline=round(offered / len(report), 3) if report else None)
    t, s, k = card["trained_on"], card["scores"], card["settings"]
    print(f"Trained on {t['examples']} examples of {t['tools']} tools ({t['features']} features); "
          f"{k['epochs']} epochs chosen on {k['chosen_on']} requests.")
    print(f"Tested on {card['tested_on']['examples']} real requests it never saw: "
          f"first pick right {s['top1']:.0%}, right tool in its top 5 {s['top5']:.0%}.")
    print(f"The keyword router offers the right tool for {card['keyword_router']['offers_the_tool']:.0%} "
          "(tuned on these same requests).")
    for m in card["misses"][:8]:
        print(f"  missed: {m['said']!r} wanted {m['wanted']}, picked {', '.join(m['picked'])}")
    return 0


def _list() -> int:
    """Prints each model's card in a line."""
    from core.model_forge import cards

    found = cards()
    if not found:
        print("No models yet: python -m tools.model_forge router")
    for c in found:
        print(f"{c['name']}: {c['kind']}; made {c['made'][:10]}; scores {c['scores']}; "
              f"{'in use' if c.get('in_use') else 'not in use'}")
    return 0


def _needs() -> int:
    """Prints each slipping loop a model could help with, the kinds that could, and what's already assigned."""
    import logging

    logging.disable(logging.INFO)
    from core import loops
    from core.model_forge import opportunities

    found = opportunities(loops.summary(None, "device"))
    if not found:
        print("No slipping loop that a model of hers could help with right now.")
    for o in found:
        kinds = ", ".join(k["kind"] + ("" if k["built"] else " (not built yet)") for k in o["kinds"])
        print(f"{o['loop']} ({o['state']}: {o['why']}): {kinds}"
              + (f"; assigned: {', '.join(o['assigned'])}" if o["assigned"] else ""))
    return 0


def main(argv: list[str]) -> int:
    """Runs one command."""
    commands = {"router": _router, "list": _list, "needs": _needs}
    if not argv or argv[0] not in commands:
        print(__doc__.strip())
        return 2
    return commands[argv[0]]()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
