"""
MIA Homestead — Self-Audit
v0.1

Run this before considering any development change done — it's the
enforcement mechanism behind "the system's self-understanding stays
current as the code changes." Three checks:

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


def check_scenarios() -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scenarios" / "scenarios.py")],
        capture_output=True, text=True,
    )
    last_line = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return result.returncode == 0, last_line


def main():
    print("=== MIA Homestead Self-Audit ===\n")
    all_clear = True

    print("1. Checking config/modules.yaml classes import correctly...")
    problems = check_configured_modules()
    if problems:
        all_clear = False
        for p in problems:
            print(f"   FAIL: {p}")
    else:
        print("   OK")

    print("\n2. Checking every Describable class is actually registered...")
    problems = check_all_describables_registered()
    if problems:
        all_clear = False
        for p in problems:
            print(f"   FAIL: {p}")
    else:
        print("   OK")

    print("\n3. Running scenario regression suite...")
    passed, summary = check_scenarios()
    if not passed:
        all_clear = False
        print(f"   FAIL: {summary}")
    else:
        print(f"   OK: {summary}")

    print()
    if all_clear:
        print("All checks passed. Self-understanding is consistent with the code.")
        sys.exit(0)
    else:
        print("Issues found above — fix before considering this change done.")
        sys.exit(1)


if __name__ == "__main__":
    main()
