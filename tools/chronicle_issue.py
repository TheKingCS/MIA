"""
tools.chronicle_issue
=======================

The Chronicles' weekly issue (core/chronicle_issue.py, build plan step 17).

    python -m tools.chronicle_issue               every issue and its status
    python -m tools.chronicle_issue draft         the next issue from the approved archive events, checked, with panels
    python -m tools.chronicle_issue show I-0001   the script, panel by panel, and any continuity problems
    python -m tools.chronicle_issue approve I-0001    (Zac) the issue joins the series
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

IMAGEGEN = Path.home() / "DevTools" / "imagegen"


def draw(issue: dict) -> str:
    """The issue's panels, by the local image model in its own environment (T-0036)."""
    from core.chronicle_issue import PANELS, panel_prompts

    python = IMAGEGEN / ".venv" / "Scripts" / "python.exe"
    # SDXL-Turbo when it's set up (T-0036: cleaner panels, 0.7 s each at 512 px), else SD-Turbo's drafts
    model = next((IMAGEGEN / m for m in ("sdxl-turbo-onnx", "sd-turbo-onnx") if (IMAGEGEN / m).exists()),
                 IMAGEGEN / "sd-turbo-onnx")
    if not python.exists() or not model.exists():
        return "no panels: the local image model isn't set up here"
    out = PANELS / issue["id"]
    out.mkdir(parents=True, exist_ok=True)
    prompts = out / "prompts.json"
    prompts.write_text(json.dumps(panel_prompts(issue)), encoding="utf-8")
    script = Path(__file__).resolve().parent / "chronicle_panels.py"
    done = subprocess.run([str(python), str(script), str(prompts), str(out), str(model)], capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=1800)
    return f"panels in {out}" if done.returncode == 0 else f"panels failed: {(done.stderr or done.stdout)[-300:]}"


def main(argv: list[str]) -> int:
    from core import chronicle_issue as ci

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    command = argv[0] if argv else "list"
    if command == "draft":
        issue = ci.draft()
        if issue is None:
            print("Nothing new to tell: approve some archive events first (the dev window's Chronicles panel).")
            return 1
        print(f"{issue['id']} \"{issue['title']}\": {issue['status']}" + (
            "; problems: " + "; ".join(issue["problems"]) if issue["problems"] else ""))
        print(draw(issue))
        return 0
    if command == "show" and len(argv) > 1:
        issue = next((i for i in ci.issues() if i["id"] == argv[1].upper()), None)
        if issue is None:
            print(f"No issue {argv[1]}.")
            return 1
        print(f"#{issue['number']:03d} {issue['title']} ({issue['status']})")
        for n, p in enumerate(issue["panels"], 1):
            print(f"\nPanel {n} [{p['event']}{'' if p['real'] else ', fictional'}]\n  {p['caption']}")
            for line in p["lines"]:
                print(f"  {line['who']}: {line['line']}")
        for problem in issue.get("problems", []):
            print(f"! {problem}")
        return 0
    if command == "approve" and len(argv) > 1:
        try:
            issue = ci.approve(argv[1])
        except ValueError as problem:
            print(problem)
            return 1
        print(f"{issue['id']} is approved and in docs/chronicles/issues.md.")
        return 0
    for issue in ci.issues():
        print(f"{issue['id']}  #{issue['number']:03d}  {issue['status']:9} {issue['title']}")
    if not ci.issues():
        print("No issues yet: python -m tools.chronicle_issue draft")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
