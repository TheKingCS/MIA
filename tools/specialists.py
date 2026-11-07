"""
tools.specialists
===================

MIA's specialists from the command line (DEC-0109; core/specialists.py).

    python -m tools.specialists                        every specialist, its notes and open questions
    python -m tools.specialists show radio             one specialist's charter, notes and questions
    python -m tools.specialists ask "how do I ..."     what her specialists know about a question
    python -m tools.specialists study radio            one study session now (Claude Code is the teacher)
    python -m tools.specialists confirm radio <note>   a person checked the note and its sources
    python -m tools.specialists withdraw radio <note> "why"
    python -m tools.specialists question radio "..."   add an open question for it to study
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    """Runs one command."""
    from core import specialists as sp

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[0] if argv else "list"
    try:
        if command == "list":
            for s in sp.SPECIALISTS:
                b = sp.book(s.id)
                live = [n for n in b["notes"] if n["status"] != "withdrawn"]
                print(f"{s.id:<13} {s.name}: {len(live)} notes "
                      f"({sum(n['status'] == 'confirmed' for n in live)} confirmed), {len(b['questions'])} questions"
                      + (f", studied {b['studied'][:10]}" if b["studied"] else ""))
            return 0
        if command == "show":
            s = sp.BY_ID[argv[1]]
            print(sp.render(s, sp.book(s.id)))
            for n in sp.book(s.id)["notes"]:
                print(f"  note {n['id']} [{n['status']}] {n['title']}")
            return 0
        if command == "ask":
            print(sp.answer(" ".join(argv[1:]), keep_question=True))  # Zac at the PC: his question to keep
            return 0
        if command == "study":
            from core.night_school import _default_ask

            result = sp.study(lambda prompt: _default_ask("claude-code", prompt), argv[1] if len(argv) > 1 else "")
            print(f"{result['specialist']}: kept {len(result['kept'])} ({'; '.join(result['kept'])}); "
                  f"refused {len(result['refused'])}")
            return 0
        if command == "confirm":
            print("Confirmed:", sp.confirm(argv[1], argv[2])["title"])
            sp.write_pages()
            return 0
        if command == "withdraw":
            print("Withdrawn:", sp.withdraw(argv[1], argv[2], " ".join(argv[3:]) or "wrong")["title"])
            sp.write_pages()
            return 0
        if command == "question":
            sp.add_question(argv[1], " ".join(argv[2:]))
            sp.write_pages()
            print("Added.")
            return 0
    except (KeyError, IndexError, ValueError) as problem:
        print(f"That didn't work: {problem}")
        return 1
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
