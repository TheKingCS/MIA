"""
tests.test_no_secrets_in_logs
===============================

No secret reaches a log (docs/SECURITY.md step 6). Two checks:

- **By reading the code**: no logging call anywhere in MIA passes a value named like a secret (a password, passphrase,
  token, secret, API key or recovery code) into the message, whether as an argument or inside an f-string. A name
  used only to choose words ("(encrypted)" if passphrase else "") is fine: that's the test of a conditional, not a
  value logged.
- **By running it** (tests/test_server_app.py, where the data is a temp folder): signing in, a wrong password,
  setting up two-step sign-in, a new recovery code and changing the password, every log line recorded with `Keep`;
  none of the secrets used appears in any of them.
"""

import ast
import logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDERS = ("core", "server", "modules", "gui", "tools")
LOG_METHODS = {"debug", "info", "warning", "warn", "error", "exception", "critical", "log"}
SECRET_NAMES = {"password", "passphrase", "passwd", "token", "access_token", "refresh_token", "secret",
                "client_secret", "api_key", "recovery_code", "master_password", "app_password", "new_password"}


def _secret_values(node: ast.AST) -> list[str]:
    """The secret-named values a logging argument would print: names and attributes, skipping the test of a
    conditional (it only picks which words are logged)."""
    found = []
    if isinstance(node, ast.IfExp):
        return _secret_values(node.body) + _secret_values(node.orelse)
    if isinstance(node, ast.Name) and node.id.lower() in SECRET_NAMES:
        found.append(node.id)
    elif isinstance(node, ast.Attribute) and node.attr.lower() in SECRET_NAMES:
        found.append(node.attr)
    elif isinstance(node, ast.Call):  # a call's result: only its arguments could carry the secret through
        for arg in list(node.args) + [k.value for k in node.keywords]:
            found += _secret_values(arg)
    else:
        for child in ast.iter_child_nodes(node):
            found += _secret_values(child)
    return found


def _is_log_call(node: ast.Call) -> bool:
    """A call like log.info(...), logger.warning(...), self.log.error(...)."""
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr in LOG_METHODS):
        return False
    owner = func.value
    name = owner.id if isinstance(owner, ast.Name) else owner.attr if isinstance(owner, ast.Attribute) else ""
    return name in ("log", "logger", "_log", "LOG", "logging")


def test_no_logging_call_passes_a_secret_into_its_message():
    """Every .py under MIA's own folders, read as code."""
    bad = []
    for folder in FOLDERS:
        for path in (ROOT / folder).rglob("*.py"):
            if "__pycache__" in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and _is_log_call(node):
                    for arg in list(node.args) + [k.value for k in node.keywords]:
                        for name in _secret_values(arg):
                            bad.append(f"{path.relative_to(ROOT)}:{node.lineno} logs {name}")
    assert not bad, "secrets passed to logging: " + "; ".join(bad)


def test_the_check_itself_catches_a_secret_and_lets_a_flag_through():
    """The reading check on two made-up lines: a password logged is caught; a yes/no about it isn't."""
    leak = ast.parse("log.info('signed in with %s', password)").body[0].value
    flag = ast.parse("log.info('made%s', ' (encrypted)' if passphrase else '')").body[0].value
    fstring = ast.parse("log.warning(f'token was {token}')").body[0].value
    assert _secret_values(leak.args[1]) == ["password"]
    assert _secret_values(flag.args[1]) == []
    assert _secret_values(fstring.args[0]) == ["token"]


class Keep(logging.Handler):
    """Keeps every log line's text."""

    def __init__(self):
        """Nothing yet."""
        super().__init__(logging.DEBUG)
        self.lines = []

    def emit(self, record):
        """Keeps the formatted message and any exception text."""
        self.lines.append(record.getMessage() + (self.format(record) if record.exc_info else ""))
