"""
tools.good_news
=================

Good News Radio on this PC (DEC-0096, core/good_news.py).

    python -m tools.good_news make        today's episode: the feeds, the stories, every personality's voice
    python -m tools.good_news show        today's stories, how each is known, and its links
    python -m tools.good_news script late night    one personality's script
"""

from __future__ import annotations

import logging
import sys


def main(argv: list[str]) -> int:
    from core import good_news

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[0] if argv else "show"
    if command == "make":
        logging.disable(logging.INFO)
        from tools.intelligence_check import build_context

        context = build_context()
        record = good_news.make(flagged=good_news.flagged_sources(context))
        print(f"{len(record['stories'])} stories from {record['items']} items"
              + (f"; didn't answer: {', '.join(record['failed'])}" if record["failed"] else ""), flush=True)
        for key in good_news.PERSONALITIES:
            title = good_news.on_air(context, record, key)
            print(f"{key}: {title or 'no voice (Kokoro not installed)'}", flush=True)
        return 0
    record = good_news.episode()
    if record is None:
        print("No episode today yet: python -m tools.good_news make")
        return 1
    if command == "script":
        print(record["scripts"][" ".join(argv[1:]) or "morning"])
        return 0
    for s in record["stories"]:
        print(f"[{s['topic']}, {s['known']}] {s['title']}")
        if s["caveats"]:
            print(f"    caveats: {'; '.join(s['caveats'])}")
        for link in s["links"]:
            print(f"    {link}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
