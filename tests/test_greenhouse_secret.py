"""
tests.test_greenhouse_secret
==============================

The greenhouse node's email password, from the vault to the node (core/greenhouse_provision.py, DEC-0150: "secrets
from the vault and never typed by a model"): found in the person's own unlocked vault, never unlocked by MIA, sent
only on "yes, send it", over standard input (never in the command or a reply), and set in the node's config by a
script that keeps the line's comment and leaves the file to its owner.
"""

import io
import sys
from types import SimpleNamespace

import pytest

from core import greenhouse_link as gl
from core import greenhouse_provision as gp
from core import life_events
from core.life_events import LifeEventLog

SECRET = "abcd efgh ijkl mnop"


class Vault:
    """A stand-in password vault: locked or not, with one login."""

    def __init__(self, unlocked=True, title="Greenhouse email", url="https://smtp.example.com"):
        """One login, its password the test secret."""
        self.unlocked = unlocked
        self.login = SimpleNamespace(entry_id="e1", title=title, url=url, password=SECRET)

    def is_unlocked(self):
        """Whether it's open."""
        return self.unlocked

    def logins(self):
        """Its logins (none when locked)."""
        return [self.login] if self.unlocked else []

    def get(self, entry_id):
        """A login by id."""
        return self.login


@pytest.fixture
def world(tmp_path, monkeypatch):
    """A context with the link, a history and a vault, and the node's key and bundle in a temp folder."""
    context = SimpleNamespace(passwords=Vault())
    context.greenhouse_link = gl.GreenhouseLink(context, data_dir=tmp_path)
    context.life_events = LifeEventLog(context, tmp_path)
    monkeypatch.setattr(gp, "KEY", tmp_path / ".keys" / "node")
    monkeypatch.setattr(gp, "BUNDLE", tmp_path / "bundle")
    gp.KEY.parent.mkdir(parents=True)
    gp.KEY.write_text("key")
    return context


def test_the_password_goes_on_standard_input_only_on_yes_and_never_into_a_reply(world):
    """The plan names the login by title and waits; "yes, send it" sends the secret as input, not in the command;
    no reply carries it, and the history records the step without it."""
    sent = []
    plan = gp.reply(world, "send the greenhouse its email password to mia-greenhouse")
    assert "Greenhouse email" in plan and "yes, send it" in plan and SECRET not in plan
    assert sent == []
    said = gp.reply(world, "yes, send it", run_input=lambda cmd, data, timeout: sent.append((cmd, data)) or (0, "set"))
    assert said.startswith("The node on mia-greenhouse") and SECRET not in said
    (cmd, data), = sent
    assert data == SECRET and all(SECRET not in part for part in cmd)
    events = life_events.events_for(world, types=("node_secret_sent",))
    assert len(events) == 1 and SECRET not in events[0].summary


def test_a_locked_vault_or_a_missing_login_is_said_and_nothing_is_sent(world):
    """MIA never unlocks the vault; with no matching login she says how to save one."""
    world.passwords = Vault(unlocked=False)
    assert "locked" in gp.reply(world, "send the greenhouse its email password")
    world.passwords = Vault(title="Bank", url="https://bank.example.com")
    assert "don't see" in gp.reply(world, "send the greenhouse its email password")
    assert world.greenhouse_link.pending == {}


def test_a_failed_send_hides_the_secret_in_what_it_printed(world):
    """Whatever the remote command printed comes back with the secret hidden."""
    gp.reply(world, "send the greenhouse its email password")
    said = gp.reply(world, "yes, send it", run_input=lambda cmd, data, timeout: (1, f"error near {data}"))
    assert "didn't reach" in said and SECRET not in said


def _run_script(monkeypatch, folder):
    """Runs the node's script in this process, in `folder`, with the secret on its standard input (no real
    process); returns what it printed."""
    out = io.StringIO()
    monkeypatch.chdir(folder)
    monkeypatch.setattr(sys, "stdin", io.StringIO(SECRET))
    monkeypatch.setattr(sys, "stdout", out)
    exec(gp._SET_SECRET, {})
    monkeypatch.setattr(sys, "stdout", sys.__stdout__)
    return out.getvalue()


def test_the_node_script_sets_the_line_keeps_its_comment_and_locks_the_file(tmp_path, monkeypatch):
    """Run as the node would, the script replaces smtp_password's value (quoted), keeps the comment, adds the line
    when it's missing, and prints nothing of the secret."""
    (tmp_path / "config").mkdir()
    conf = tmp_path / "config" / "notifications.yaml"
    conf.write_text('smtp_host: "smtp.example.com"\nsmtp_password: ""         # an APP password\nfrom_address: ""\n')
    assert _run_script(monkeypatch, tmp_path).strip() == "set"
    lines = conf.read_text().splitlines()
    assert lines[1] == f'smtp_password: "{SECRET}"  # an APP password' and lines[2] == 'from_address: ""'
    conf.write_text("smtp_host: x\n")
    _run_script(monkeypatch, tmp_path)
    assert conf.read_text().splitlines()[-1] == f'smtp_password: "{SECRET}"'
