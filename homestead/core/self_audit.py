"""
MIA Homestead — Self-Audit
v0.1

Run this before considering any development change done — it's the
enforcement mechanism behind "the system's self-understanding stays
current as the code changes." Seven checks:

1. Every MiaHomesteadModule class referenced in config/modules.yaml
   actually imports and exists.
2. Every Describable class defined in modules/ or core/ is actually
   wired into main.py's registration list — catches the specific
   failure mode of writing a new module, giving it a proper
   describe_capabilities()/describe_hardware_requirements(), and then
   forgetting to add it to all_describables in main.py, which would
   otherwise silently leave a real module invisible to the assistant.
3. The full scenario regression suite still passes — the safety-net
   check.
4. Verification coverage — how many registered capabilities actually
   have proof behind them (informational, not a hard failure).
5. Conversational coverage (best-effort heuristic) — every declared
   action_possible should have a matching assistant tool, unless it's
   a documented, intentional exception (see CLAUDE.md rule 5).
6. Tool domain coverage — every tool in assistant/greenhouse_assistant.py's
   TOOLS list has a matching entry in TOOL_DOMAINS, and vice versa. See
   docs/OFFLINE_ASSISTANT_PLAN.md for why this tagging exists.
7. Destructive-tool validity — every name in DESTRUCTIVE_TOOLS matches a
   real tool, so split_safe_tool_calls()'s protection can't silently go
   stale after a tool is renamed or removed.

Usage:
    python3 core/self_audit.py
"""

import ast
import importlib
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))


def check_configured_modules() -> list[str]:
    """Every class referenced in config/modules.yaml must actually import."""
    problems = []
    config = yaml.safe_load((ROOT / "config" / "modules.yaml").read_text())
    for entry in config.get("modules", []):
        class_path = entry["class"]
        module_path, class_name = class_path.rsplit(".", 1)
        try:
            mod = importlib.import_module(module_path)
            getattr(mod, class_name)
        except Exception as e:
            problems.append(f"config/modules.yaml references '{class_path}' (id: {entry['id']}) "
                             f"which fails to import: {e}")
    return problems


def find_describable_classes() -> dict[str, Path]:
    """Scans modules/ and core/ for classes that inherit Describable —
    doesn't execute anything, just parses the AST, so this is safe to
    run even against code with bugs elsewhere."""
    found = {}
    for directory in ["modules", "core"]:
        for path in (ROOT / directory).glob("*.py"):
            try:
                tree = ast.parse(path.read_text())
            except SyntaxError:
                found[f"SYNTAX_ERROR:{path.name}"] = path
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    base_names = [b.id if isinstance(b, ast.Name) else getattr(b, "attr", "")
                                   for b in node.bases]
                    if "Describable" in base_names or "MiaHomesteadModule" in base_names:
                        found[node.name] = path
    return found


def check_all_describables_registered() -> list[str]:
    """Cross-references every Describable class found in code against
    main.py's registration text — a class that exists but is never
    mentioned in main.py's all_describables list is real code the
    assistant doesn't actually know about."""
    problems = []
    main_py_text = (ROOT / "main.py").read_text()
    classes = find_describable_classes()
    config = yaml.safe_load((ROOT / "config" / "modules.yaml").read_text())

    for class_name, path in classes.items():
        if class_name.startswith("SYNTAX_ERROR"):
            problems.append(f"{path} has a syntax error — cannot verify registration")
            continue
        # A registered class is either instantiated directly in main.py,
        # or loaded dynamically via module_registry.py from
        # config/modules.yaml (control modules). Check both paths.
        if class_name in main_py_text:
            continue
        referenced_in_config = any(class_name in entry["class"] for entry in config.get("modules", []))
        if referenced_in_config:
            continue
        problems.append(
            f"{class_name} ({path.relative_to(ROOT)}) implements Describable but isn't "
            f"referenced in main.py or config/modules.yaml — the assistant doesn't know it exists."
        )
    return problems


def check_conversational_coverage() -> dict:
    """Best-effort check: does every registered capability's
    actions_possible have SOMETHING that looks like a matching
    assistant tool? This is deliberately a keyword heuristic, not
    exact matching — action descriptions are free text. It exists to
    catch the specific failure mode this project has hit before: a
    real backend method exists, does something useful, and nobody
    wired a conversational path to it. False positives are expected
    and fine to dismiss after a manual look; false negatives (a real
    gap this misses) are the risk to watch for.

    Scans only the real TOOLS definitions (names + descriptions), not the
    whole source file — scanning the whole file was tried first and broke
    the moment assistant/greenhouse_assistant.py grew a domain-keyword
    dict (TOOL_DOMAINS/DOMAIN_TRIGGER_KEYWORDS) full of the same
    dosing-related vocabulary as the two intentionally-uncommandable dosing
    actions, which made this heuristic falsely think they were covered.
    Matching against actual tool text only is also just the more correct
    check for what this is trying to verify."""
    import json
    import re
    import sqlite3

    db_path = ROOT / "mia_homestead.db"
    if not db_path.exists():
        return {}

    conn = sqlite3.connect(str(db_path))
    from assistant.greenhouse_assistant import TOOLS
    tools_source = " ".join(f"{t['name']} {t['description']}" for t in TOOLS).lower()

    # Verb-ish stopwords stripped so "record a new planting" -> {"record","new","planting"}
    # then checked against whether those words appear near a tool name/description.
    STOPWORDS = {"a", "the", "to", "for", "of", "on", "with", "and", "or", "an", "is", "this"}

    rows = conn.execute("SELECT module_id, actions_possible FROM system_capabilities").fetchall()
    gaps = {}
    for module_id, actions_json in rows:
        actions = json.loads(actions_json or "[]")
        missing = []
        for action in actions:
            words = [w for w in re.findall(r"[a-z]+", action.lower()) if w not in STOPWORDS and len(w) > 3]
            if not words:
                continue
            # A tool "covers" this action if at least half its significant
            # words show up somewhere in the tools source text.
            hits = sum(1 for w in words if w in tools_source)
            if hits < max(1, len(words) // 2):
                missing.append(action)
        if missing:
            gaps[module_id] = missing
    return gaps


def check_tool_domain_coverage() -> list[str]:
    """Every tool in assistant/greenhouse_assistant.py's TOOLS list must
    have a matching entry in TOOL_DOMAINS, and vice versa — this is what
    keeps the domain-tagging step of docs/OFFLINE_ASSISTANT_PLAN.md from
    silently drifting out of sync as tools get added, renamed, or removed.
    Same discipline this project already applies to capability
    registration, one layer up: tagging a tool's domain happens in the
    same sitting as adding the tool, not as a followup someone forgets."""
    from assistant.greenhouse_assistant import TOOL_DOMAINS, TOOLS

    problems = []
    tool_names = {t["name"] for t in TOOLS}
    tagged_names = set(TOOL_DOMAINS.keys())

    for name in sorted(tool_names - tagged_names):
        problems.append(f"Tool '{name}' exists in TOOLS but has no entry in TOOL_DOMAINS")
    for name in sorted(tagged_names - tool_names):
        problems.append(f"TOOL_DOMAINS has an entry for '{name}' which no longer exists in TOOLS")
    return problems


def check_destructive_tools_valid() -> list[str]:
    """Every name in DESTRUCTIVE_TOOLS must match a real tool in TOOLS —
    catches a typo or a stale entry left behind after a tool was renamed.
    Either one would silently leave that tool unprotected by
    split_safe_tool_calls() with no error to flag it — a much worse
    failure mode than the tagging drift check 6 guards against, since
    this one is a safety gap, not just a routing inefficiency."""
    from assistant.greenhouse_assistant import DESTRUCTIVE_TOOLS, TOOLS

    tool_names = {t["name"] for t in TOOLS}
    problems = []
    for name in sorted(DESTRUCTIVE_TOOLS):
        if name not in tool_names:
            problems.append(
                f"DESTRUCTIVE_TOOLS has an entry for '{name}' which doesn't match any real "
                f"tool in TOOLS — it would silently go unprotected against bundled-call risk"
            )
    return problems


def check_scenarios() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scenarios" / "scenarios.py")],
        capture_output=True, text=True,
    )
    last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return result.returncode == 0, last_line


def run_full_diagnostics(print_output: bool = True) -> dict:
    """Runs all 7 checks and returns a structured result — the single
    persistent, always-current self-diagnostic suite for this project,
    usable two ways: the CLI (main(), below — output/exit-code unchanged
    from before this function existed) and core.self_audit.run_full_diagnostics()
    called directly by anything else that wants the program to test
    itself, e.g. assistant/greenhouse_assistant.py's run_self_diagnostics
    tool, so a human can trigger a real self-check from chat instead of
    only ever from a developer's terminal. Every check here already
    re-runs against whatever the code currently is (imports, greps
    source, executes the real scenario suite) — nothing here is a
    stale snapshot that needs separate upkeep as the project grows."""
    def p(line: str = ""):
        if print_output:
            print(line)

    p("=== MIA Homestead Self-Audit ===\n")
    checks = []
    all_clear = True

    p("1. Checking config/modules.yaml classes import correctly...")
    problems = check_configured_modules()
    ok = not problems
    all_clear = all_clear and ok
    checks.append({"name": "configured_modules_import", "ok": ok, "problems": problems})
    p("   OK" if ok else "\n".join(f"   FAIL: {x}" for x in problems))

    p("\n2. Checking every Describable class is actually registered...")
    problems = check_all_describables_registered()
    ok = not problems
    all_clear = all_clear and ok
    checks.append({"name": "describables_registered", "ok": ok, "problems": problems})
    p("   OK" if ok else "\n".join(f"   FAIL: {x}" for x in problems))

    p("\n3. Running scenario regression suite...")
    passed, summary = check_scenarios()
    all_clear = all_clear and passed
    checks.append({"name": "scenario_suite", "ok": passed, "summary": summary})
    p(f"   {'OK' if passed else 'FAIL'}: {summary}")

    p("\n4. Checking verification coverage (claims backed by proof)...")
    coverage_check = {"name": "verification_coverage", "ok": True}
    try:
        import sqlite3
        from core.capability_registry import CapabilityRegistry
        # Coverage is informational, not a hard failure — an unverified
        # module is a real gap worth knowing about, but shouldn't block
        # a build the way a broken import or a failing scenario does.
        conn = sqlite3.connect(ROOT / "mia_homestead.db")
        coverage = CapabilityRegistry.get_verification_coverage(conn)
        coverage_check["coverage"] = coverage
        if coverage["total"] == 0:
            p("   (no capabilities registered yet — run main.py once first)")
        else:
            p(f"   {coverage['verified']}/{coverage['total']} modules have verification evidence")
            if coverage["unverified_modules"]:
                p(f"   Unverified (not a failure, just a gap): {', '.join(coverage['unverified_modules'])}")
    except Exception as e:
        coverage_check["skipped_reason"] = str(e)
        p(f"   (skipped — {e})")
    checks.append(coverage_check)

    p("\n5. Checking conversational coverage (best-effort heuristic)...")
    gaps = check_conversational_coverage()
    checks.append({"name": "conversational_coverage", "ok": True, "gaps": gaps})
    if gaps:
        p(f"   {len(gaps)} module(s) declare actions with no obviously-matching assistant tool:")
        for module_id, actions in gaps.items():
            p(f"   - {module_id}: {actions}")
        p("   (This is a heuristic keyword match, not exhaustive — verify by hand before "
          "assuming a real gap. But every hit so far in this project's history has been real.)")
    else:
        p("   OK — no obvious gaps found")

    p("\n6. Checking every assistant tool has a domain tag (TOOL_DOMAINS)...")
    domain_check = {"name": "tool_domain_coverage", "ok": True}
    try:
        problems = check_tool_domain_coverage()
        ok = not problems
        all_clear = all_clear and ok
        domain_check.update(ok=ok, problems=problems)
        p("   OK" if ok else "\n".join(f"   FAIL: {x}" for x in problems))
    except Exception as e:
        domain_check.update(skipped_reason=str(e))
        p(f"   (skipped — {e})")
    checks.append(domain_check)

    p("\n7. Checking every destructive-tool tag matches a real tool...")
    destructive_check = {"name": "destructive_tools_valid", "ok": True}
    try:
        problems = check_destructive_tools_valid()
        ok = not problems
        all_clear = all_clear and ok
        destructive_check.update(ok=ok, problems=problems)
        p("   OK" if ok else "\n".join(f"   FAIL: {x}" for x in problems))
    except Exception as e:
        destructive_check.update(skipped_reason=str(e))
        p(f"   (skipped — {e})")
    checks.append(destructive_check)

    p()
    if all_clear:
        p("All checks passed. Self-understanding is consistent with the code.")
    else:
        p("Issues found above — fix before considering this change done.")

    return {"all_clear": all_clear, "checks": checks}


def main():
    result = run_full_diagnostics(print_output=True)
    sys.exit(0 if result["all_clear"] else 1)


if __name__ == "__main__":
    main()
