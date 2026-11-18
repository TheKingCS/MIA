"""
tests.test_ci_workflows
=========================

FW-02, CI as the gate (DEC-0264; `docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md` §4): every action a workflow
uses is pinned to a commit, not a tag that could be moved; every workflow says what its token may do; the Linux suite
runs on every push; the image's own Python runs the whole suite inside the booted image; and nothing in the code or
its settings names a person's Windows user folder (the repository is public, DEV-011).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = sorted((ROOT / ".github" / "workflows").glob("*.yml"))


def test_every_action_a_workflow_uses_is_pinned_to_a_full_commit():
    loose = []
    for wf in WORKFLOWS:
        for n, line in enumerate(wf.read_text(encoding="utf-8").splitlines(), 1):
            found = re.search(r"uses:\s*([^\s#]+)", line)
            if found and not found.group(1).startswith("./") and not re.search(r"@[0-9a-f]{40}$", found.group(1)):
                loose.append(f"{wf.name}:{n} {found.group(1)}")
    assert loose == [], loose


def test_every_workflow_says_what_its_token_may_do():
    assert WORKFLOWS and [wf.name for wf in WORKFLOWS if "\npermissions:" not in wf.read_text(encoding="utf-8")] == []


def test_the_linux_suite_runs_on_every_push_and_the_whole_suite_runs_inside_the_image():
    poc = (ROOT / ".github" / "workflows" / "mia-os-poc.yml").read_text(encoding="utf-8")
    trigger = poc.split("\non:\n", 1)[1].split("\npermissions:", 1)[0]
    assert "push:" in trigger and "paths:" not in trigger and "suite-linux:" in poc
    vm = (ROOT / ".github" / "workflows" / "mia-os-vm.yml").read_text(encoding="utf-8")
    assert "/usr/lib/mia/venv/bin/python -m pytest" in vm and "runuser -l mia" in vm


def _tracked() -> list[str]:
    """The repository's tracked files (git ls-files), or none where git isn't there."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return out.stdout.splitlines() if out.returncode == 0 else []


# Docs, records and Zac's own prompts are history and stay as written; code and settings must never name a user folder.
_NOT_CODE = ("docs/", "work/", "audit/")
_USER_FOLDER = re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+(?!<|Public\b|Default\b|runneradmin\b|x[\\/]|you\b|name\b)[A-Za-z0-9._-]+")


def test_no_code_or_setting_names_a_persons_windows_user_folder():
    files = [f for f in _tracked() if not f.startswith(_NOT_CODE)
             and f.endswith((".py", ".js", ".html", ".css", ".json", ".yml", ".yaml", ".toml", ".ini", ".sh", ".ps1",
                             ".bat", ".service", ".kt", ".gradle", ".kts", ".xml", ".cfg", ".txt"))
             and not f.endswith(".lock")]
    hits = []
    for name in files:
        try:
            text = (ROOT / name).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for found in _USER_FOLDER.finditer(text):
            hits.append(f"{name}: {found.group(0)}")
    assert hits == [], hits
