"""
tests.test_web_scripts
========================

The web pages' own scripts (2026-11-07): every script a page loads is there, and the shared modules pages depend on
still define what they promise. A security change once replaced the Grow Lab module (grow.js) with a one-line
redirect, which sent every asset page to the Greenhouse; this catches that kind of overwrite.
"""

import re
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"

# A shared script and the global it must define for the pages that load it.
MODULES = {"grow.js": "window.MIAGrow", "shell.js": "window.MIAShell", "mia.js": "MIA", "icons.js": "MIAIcons",
           "player.js": "window.MIAPlayer"}


def test_every_script_a_page_loads_is_there():
    missing = []
    for page in WEB.glob("*.html"):
        for src in re.findall(r'<script[^>]*src="([^"]+)"', page.read_text(encoding="utf-8")):
            if "://" not in src and not (WEB / src.split("?")[0]).is_file():
                missing.append(f"{page.name}: {src}")
    assert missing == []


def test_the_shared_modules_still_define_what_pages_use():
    for name, symbol in MODULES.items():
        assert symbol in (WEB / name).read_text(encoding="utf-8"), f"{name} no longer defines {symbol}"


def test_a_redirect_page_never_borrows_a_module_file():
    for page in WEB.glob("*.html"):
        for src in re.findall(r'<script[^>]*src="([^"]+)"', page.read_text(encoding="utf-8")):
            path = WEB / src.split("?")[0]
            if path.is_file() and "location.replace(" in path.read_text(encoding="utf-8") and src.split("?")[0] in MODULES:
                raise AssertionError(f"{page.name} loads {src}, a shared module, as a redirect")
