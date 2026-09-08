"""
tests.test_plaid_manager
===========================

Unit tests for core.plaid_manager — the vault encrypt/decrypt round
trip (real core.secrets_manager calls, no network) and
poll_for_public_token()'s/extract_completed_public_token()'s stopping
logic against fake, duck-typed response objects (SimpleNamespace, not
real plaid.model classes — those require every field passed explicitly
even as None, which would make these tests verbose and brittle for no
real benefit; the code under test only reads a handful of attributes
by name, so a duck-typed fake is the right level of fidelity).

No test here makes a real network call or needs real Plaid credentials
— see core/plaid_manager.py's own module docstring for what's still
unverified against Plaid's real API as of this file's writing.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Optional

import pytest

import core.plaid_manager as plaid_manager_module
from core.app_context import AppContext
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.plaid_manager import PlaidItem, PlaidManager, PlaidVault, extract_completed_public_token
from core.secrets_manager import SecretsError


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(plaid_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(plaid_manager_module, "_VAULT_FILE", data_dir / "plaid_vault.enc")
    return data_dir


def _make_manager() -> PlaidManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return PlaidManager(context)


# ------------------------------------------------------------------
# Vault setup / unlock — real secrets_manager encryption, no network
# ------------------------------------------------------------------

def test_is_configured_false_before_setup(isolated_paths):
    manager = _make_manager()
    assert manager.is_configured() is False


def test_setup_creates_a_vault_and_unlocks_it(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid123", secret="sec456", environment="sandbox", passphrase="hunter2")

    assert manager.is_configured() is True
    assert manager.is_unlocked() is True
    assert manager.connected_items() == []


def test_unlock_with_correct_passphrase_restores_the_vault(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid123", secret="sec456", environment="sandbox", passphrase="hunter2")

    reloaded = _make_manager()
    assert reloaded.is_unlocked() is False
    reloaded.unlock("hunter2")
    assert reloaded.is_unlocked() is True
    assert reloaded.connected_items() == []


def test_unlock_with_wrong_passphrase_raises_secrets_error(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid123", secret="sec456", environment="sandbox", passphrase="hunter2")

    reloaded = _make_manager()
    with pytest.raises(SecretsError):
        reloaded.unlock("wrong-passphrase")


def test_unlock_before_any_setup_raises_secrets_error(isolated_paths):
    manager = _make_manager()
    with pytest.raises(SecretsError):
        manager.unlock("anything")


def test_setup_rejects_unknown_environment_defaults_to_sandbox(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="not-a-real-environment", passphrase="hunter2")
    assert manager._vault.environment == "sandbox"


def test_require_unlocked_raises_before_setup_or_unlock(isolated_paths):
    manager = _make_manager()
    with pytest.raises(RuntimeError):
        manager.connected_items()


# ------------------------------------------------------------------
# finish_connection / save_current_vault — real encryption round trip
# with a connected item persisted
# ------------------------------------------------------------------

def test_finish_connection_appends_item_and_save_persists_it(isolated_paths, monkeypatch):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")

    fake_exchange_response = SimpleNamespace(access_token="access-sandbox-abc", item_id="item-123")
    fake_item = SimpleNamespace(institution_name="Chase")
    fake_accounts_response = SimpleNamespace(item=fake_item, accounts=[])
    fake_client = SimpleNamespace(
        item_public_token_exchange=lambda req: fake_exchange_response,
        accounts_get=lambda req: fake_accounts_response,
    )
    manager._client = fake_client

    item = manager.finish_connection("public-token-xyz")
    assert item.access_token == "access-sandbox-abc"
    assert item.institution_name == "Chase"
    assert len(manager.connected_items()) == 1

    manager.save_current_vault("hunter2")

    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert len(reloaded.connected_items()) == 1
    assert reloaded.connected_items()[0].institution_name == "Chase"
    assert reloaded.connected_items()[0].access_token == "access-sandbox-abc"


# ------------------------------------------------------------------
# extract_completed_public_token — pure logic, duck-typed fakes
# ------------------------------------------------------------------

def _get_response(sessions):
    return SimpleNamespace(link_sessions=sessions)


def _session(item_add_results=None, results=None):
    if results is None:
        results = SimpleNamespace(item_add_results=item_add_results or [])
    return SimpleNamespace(results=results)


def _item_add_result(public_token: Optional[str]):
    return SimpleNamespace(public_token=public_token)


def test_extract_completed_public_token_none_when_no_sessions():
    assert extract_completed_public_token(_get_response([])) is None


def test_extract_completed_public_token_none_when_session_has_no_results():
    response = _get_response([_session(results=None)])
    assert extract_completed_public_token(response) is None


def test_extract_completed_public_token_none_when_no_item_add_results_yet():
    response = _get_response([_session(item_add_results=[])])
    assert extract_completed_public_token(response) is None


def test_extract_completed_public_token_finds_the_real_token():
    response = _get_response([_session(item_add_results=[_item_add_result("public-token-xyz")])])
    assert extract_completed_public_token(response) == "public-token-xyz"


def test_extract_completed_public_token_skips_a_result_with_no_token_yet():
    response = _get_response([_session(item_add_results=[_item_add_result(None), _item_add_result("real-token")])])
    assert extract_completed_public_token(response) == "real-token"


# ------------------------------------------------------------------
# poll_for_public_token — stopping logic against a fake client + fake
# clock, no real 180-second wait
# ------------------------------------------------------------------

def test_poll_for_public_token_returns_immediately_on_first_success(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")

    response = _get_response([_session(item_add_results=[_item_add_result("token-1")])])
    manager._client = SimpleNamespace(link_token_get=lambda req: response)

    result = manager.poll_for_public_token(
        "link-token", timeout_seconds=10, poll_interval_seconds=1,
        sleep_fn=lambda seconds: None, now_fn=_counting_clock(),
    )
    assert result == "token-1"


def test_poll_for_public_token_succeeds_after_a_few_empty_polls(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")

    empty_response = _get_response([_session(item_add_results=[])])
    success_response = _get_response([_session(item_add_results=[_item_add_result("token-2")])])
    responses = [empty_response, empty_response, success_response]
    manager._client = SimpleNamespace(link_token_get=lambda req: responses.pop(0))

    result = manager.poll_for_public_token(
        "link-token", timeout_seconds=100, poll_interval_seconds=1,
        sleep_fn=lambda seconds: None, now_fn=_counting_clock(),
    )
    assert result == "token-2"


def test_poll_for_public_token_returns_none_on_timeout(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")

    empty_response = _get_response([_session(item_add_results=[])])
    manager._client = SimpleNamespace(link_token_get=lambda req: empty_response)

    # A clock that jumps straight past the deadline on the second call —
    # simulates a real timeout without actually waiting for one.
    clock = iter([0.0, 0.0, 1000.0])
    result = manager.poll_for_public_token(
        "link-token", timeout_seconds=10, poll_interval_seconds=1,
        sleep_fn=lambda seconds: None, now_fn=lambda: next(clock),
    )
    assert result is None


def _counting_clock():
    """A fake now_fn that advances by 1 on every call — enough ticks
    for these tests' short poll sequences without ever reaching a
    generously-sized timeout."""
    state = {"t": 0.0}

    def _now():
        state["t"] += 1.0
        return state["t"]

    return _now
