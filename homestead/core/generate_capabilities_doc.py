"""
MIA Homestead — Capabilities Document Generator
v0.1

Generates docs/FEATURES_AND_CAPABILITIES.md directly from the
system_capabilities table — the running features/capabilities list,
regenerated from live data every time it's run, never hand-maintained.
Each entry shows what a module claims to do AND what actually proves
it, so this document can't drift into aspirational claims the way a
hand-written features list eventually does.

Run this after any registration pass (main.py does this automatically
every startup) or manually:
    python3 core/generate_capabilities_doc.py --db mia_homestead.db
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.capability_registry import CapabilityRegistry

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "FEATURES_AND_CAPABILITIES.md"


def generate(db_path: str) -> str:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("SELECT * FROM system_capabilities ORDER BY module_id").fetchall()
    coverage = CapabilityRegistry.get_verification_coverage(conn)

    lines = [
        "# MIA Homestead — Features & Capabilities",
        "",
        f"**Auto-generated {datetime.utcnow().isoformat()}Z from `system_capabilities` — "
        f"never hand-edit this file, it will be overwritten on the next registration pass.**",
        "",
        f"**Verification coverage: {coverage['verified']}/{coverage['total']} modules have "
        f"actual proof behind their claims, not just a description.**",
    ]
    if coverage["unverified_modules"]:
        lines.append(f"Unverified: {', '.join(coverage['unverified_modules'])}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in rows:
        data_produced = json.loads(r["data_produced"] or "[]")
        actions = json.loads(r["actions_possible"] or "[]")
        evidence = json.loads(r["verification_evidence"] or "[]")

        lines.append(f"## {r['display_name']} (`{r['module_id']}`)")
        lines.append("")
        lines.append(r["purpose"])
        lines.append("")

        if actions:
            lines.append("**Can do:**")
            for a in actions:
                lines.append(f"- {a}")
            lines.append("")

        if data_produced:
            lines.append("**Tracks/produces:**")
            for d in data_produced:
                lines.append(f"- {d}")
            lines.append("")

        if r["limits_and_safety"]:
            lines.append(f"**Limits:** {r['limits_and_safety']}")
            lines.append("")

        lines.append("**Proof this actually works:**")
        if evidence:
            for e in evidence:
                lines.append(f"- {e}")
        else:
            lines.append("- UNVERIFIED — described but not yet proven against real behavior.")
        lines.append("")
        lines.append(f"*Last updated: {r['updated_at']}*")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_and_write(db_path: str) -> str:
    """The version main.py should actually call — generate() alone
    only returns a string, it doesn't touch disk. This is what closes
    that gap."""
    content = generate(db_path)
    OUTPUT_PATH.write_text(content)
    return content


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    args = parser.parse_args()
    content = generate(args.db)
    OUTPUT_PATH.write_text(content)
    print(f"Generated {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
