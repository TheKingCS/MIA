"""
tools.audit
=============

MIA's self-audit from the command line (DEC-0108; core/self_audit.py,
core/practices.py).

    python -m tools.audit              the latest weekly report
    python -m tools.audit code         the code audit now: where it could be clearer or leaner
    python -m tools.audit connections  the interconnection audit now: each store's connections, and lone events
    python -m tools.audit run          the whole weekly audit now (keeps the report, opens up to two tasks,
                                       rewrites docs/practices/)
"""

from __future__ import annotations

import sys


def main(argv: list[str]) -> int:
    """Runs one command."""
    import logging

    logging.disable(logging.INFO)
    from core import self_audit

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[0] if argv else "report"
    if command == "code":
        found = self_audit.code_findings()
        print(f"{len(found)} places to look: " + ", ".join(f"{k} {n}" for k, n in self_audit._count(found).items()))
        for f in found[:20]:
            print(f"  {f['file']}:{f['line']} {f['name']}: {f['detail']}")
        return 0
    if command == "connections":
        rows = self_audit.store_connections()
        print(f"{self_audit.connected_share(rows):.0%} of the store connections that should exist do.")
        print("  store                 history links voice life-state web")
        for r in rows:
            print(f"  {r['store']:<22}" + " ".join(f"{'yes' if r[k] else '-':<{w}}" for k, w in (
                ("history", 7), ("links", 5), ("assistant", 5), ("life_state", 10), ("web", 3))))
        for f in self_audit.connection_findings(rows=rows):
            if f["kind"] != "store":
                print(f"  {f['detail']}")
        return 0
    if command == "run":
        report = self_audit.weekly()
        print(f"{report['code']['findings']} code findings, {report['connections']['findings']} connections to make "
              f"({report['connections']['share']:.0%} connected); practices: {report['practices']}; tasks: "
              f"{', '.join(report['tasks']) or 'none new'}")
        return 0
    if command == "report":
        last = self_audit.latest()
        if not last:
            print("No audit yet: python -m tools.audit run (Night School runs one weekly).")
            return 0
        print(f"Audit of {last['at'][:10]}: {last['code']['findings']} code findings, "
              f"{last['connections']['findings']} connections to make ({last['connections']['share']:.0%} connected).")
        for f in last["code"]["top"][:5] + last["connections"]["top"][:5]:
            print(f"  {f.get('file', '')} {f['name']}: {f['detail'][:140]}")
        return 0
    print(__doc__.strip())
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
