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

import core.budget_manager as budget_manager_module
import core.plaid_manager as plaid_manager_module
from core.app_context import AppContext
from core.budget_manager import BudgetManager
from core.config_manager import ConfigManager
from core.event_bus import EventBus
from core.plaid_manager import (
    PlaidItem,
    PlaidManager,
    PlaidVault,
    compute_net_balance_total,
    extract_completed_public_token,
    map_plaid_category,
)
from core.secrets_manager import SecretsError


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setattr(plaid_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(plaid_manager_module, "_VAULT_FILE", data_dir / "plaid_vault.enc")
    return data_dir


@pytest.fixture
def isolated_paths_with_budget(tmp_path, monkeypatch):
    """Same isolation as isolated_paths, plus a real, isolated
    BudgetManager sharing the AppContext — for tests that exercise
    _import_transaction()'s real budget.add_income()/add_expense()
    calls, not just the Plaid vault/client side."""
    data_dir = tmp_path / "data"
    monkeypatch.setattr(plaid_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(plaid_manager_module, "_VAULT_FILE", data_dir / "plaid_vault.enc")
    monkeypatch.setattr(budget_manager_module, "_DATA_DIR", data_dir)
    monkeypatch.setattr(budget_manager_module, "_BILLS_FILE", data_dir / "bills.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_FILE", data_dir / "income.json")
    monkeypatch.setattr(budget_manager_module, "_EXPENSES_FILE", data_dir / "budget_expenses.json")
    monkeypatch.setattr(budget_manager_module, "_INCOME_SOURCES_FILE", data_dir / "income_sources.json")
    monkeypatch.setattr(budget_manager_module, "_BUDGET_TARGETS_FILE", data_dir / "budget_targets.json")
    return data_dir


def _make_manager() -> PlaidManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    return PlaidManager(context)


def _make_manager_with_budget() -> PlaidManager:
    context = AppContext(config=ConfigManager(), events=EventBus())
    context.budget = BudgetManager(context)
    return PlaidManager(context)


def _fake_transaction(transaction_id="txn-1", amount=45.0, name="Coffee Shop", merchant_name=None,
                       date="2026-09-01", primary="FOOD_AND_DRINK", detailed="FOOD_AND_DRINK_COFFEE"):
    return SimpleNamespace(
        transaction_id=transaction_id, amount=amount, name=name, merchant_name=merchant_name,
        date=date, personal_finance_category=SimpleNamespace(primary=primary, detailed=detailed),
    )


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
    assert item.transactions_enabled is True
    assert item.investments_enabled is True
    assert len(manager.connected_items()) == 1

    manager.save_current_vault("hunter2")

    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert len(reloaded.connected_items()) == 1
    assert reloaded.connected_items()[0].institution_name == "Chase"
    assert reloaded.connected_items()[0].access_token == "access-sandbox-abc"
    assert reloaded.connected_items()[0].transactions_enabled is True
    assert reloaded.connected_items()[0].investments_enabled is True


# ------------------------------------------------------------------
# map_plaid_category — pure logic, no SDK objects, one case per row of
# the mapping table in core/plaid_manager.py's own docstring
# ------------------------------------------------------------------

def test_map_plaid_category_income_dividend_is_investment():
    assert map_plaid_category("INCOME", "INCOME_DIVIDENDS", is_income=True) == "Investment"


def test_map_plaid_category_income_interest_is_investment():
    assert map_plaid_category("INCOME", "INCOME_INTEREST_EARNED", is_income=True) == "Investment"


def test_map_plaid_category_income_otherwise_is_salary():
    assert map_plaid_category("INCOME", "INCOME_WAGES", is_income=True) == "Salary"


def test_map_plaid_category_loan_disbursements_is_other():
    assert map_plaid_category("LOAN_DISBURSEMENTS", "", is_income=True) == "Other"


def test_map_plaid_category_transfer_in_is_skipped():
    assert map_plaid_category("TRANSFER_IN", "", is_income=True) is None


def test_map_plaid_category_unrecognized_income_primary_is_other():
    assert map_plaid_category("SOME_FUTURE_CATEGORY", "", is_income=True) == "Other"


def test_map_plaid_category_rent_and_utilities_rent_is_mortgage_rent():
    assert map_plaid_category("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_RENT", is_income=False) == "Mortgage/Rent"


def test_map_plaid_category_rent_and_utilities_otherwise_is_utilities():
    assert map_plaid_category("RENT_AND_UTILITIES", "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY", is_income=False) == "Utilities"


def test_map_plaid_category_food_and_drink_is_groceries():
    assert map_plaid_category("FOOD_AND_DRINK", "FOOD_AND_DRINK_GROCERIES", is_income=False) == "Groceries"


def test_map_plaid_category_transportation_is_transportation():
    assert map_plaid_category("TRANSPORTATION", "", is_income=False) == "Transportation"


def test_map_plaid_category_home_improvement_is_maintenance():
    assert map_plaid_category("HOME_IMPROVEMENT", "", is_income=False) == "Maintenance"


def test_map_plaid_category_general_services_insurance_is_insurance():
    assert map_plaid_category("GENERAL_SERVICES", "GENERAL_SERVICES_INSURANCE", is_income=False) == "Insurance"


def test_map_plaid_category_general_services_otherwise_is_other():
    assert map_plaid_category("GENERAL_SERVICES", "GENERAL_SERVICES_ACCOUNTING", is_income=False) == "Other"


def test_map_plaid_category_government_tax_is_taxes():
    assert map_plaid_category("GOVERNMENT_AND_NON_PROFIT", "GOVERNMENT_AND_NON_PROFIT_TAX", is_income=False) == "Taxes"


def test_map_plaid_category_government_otherwise_is_other():
    assert map_plaid_category("GOVERNMENT_AND_NON_PROFIT", "GOVERNMENT_AND_NON_PROFIT_DONATIONS", is_income=False) == "Other"


def test_map_plaid_category_loan_payments_mortgage_is_mortgage_rent():
    assert map_plaid_category("LOAN_PAYMENTS", "LOAN_PAYMENTS_MORTGAGE_PAYMENT", is_income=False) == "Mortgage/Rent"


def test_map_plaid_category_loan_payments_otherwise_is_other():
    assert map_plaid_category("LOAN_PAYMENTS", "LOAN_PAYMENTS_CAR_PAYMENT", is_income=False) == "Other"


def test_map_plaid_category_transfer_out_is_skipped():
    assert map_plaid_category("TRANSFER_OUT", "", is_income=False) is None


def test_map_plaid_category_unrecognized_expense_primary_is_other():
    # A value Plaid might add in the future that this function doesn't
    # recognize yet — real ENTERTAINMENT/MEDICAL/etc. now have their own
    # explicit mapping, see the tests below.
    assert map_plaid_category("SOME_FUTURE_EXPENSE_CATEGORY", "", is_income=False) == "Other"


def test_map_plaid_category_medical_is_medical():
    assert map_plaid_category("MEDICAL", "", is_income=False) == "Medical"


def test_map_plaid_category_personal_care_is_personal_care():
    assert map_plaid_category("PERSONAL_CARE", "", is_income=False) == "Personal Care"


def test_map_plaid_category_general_merchandise_is_shopping():
    assert map_plaid_category("GENERAL_MERCHANDISE", "", is_income=False) == "Shopping"


def test_map_plaid_category_bank_fees_is_bank_fees():
    assert map_plaid_category("BANK_FEES", "", is_income=False) == "Bank Fees"


def test_map_plaid_category_entertainment_is_entertainment():
    assert map_plaid_category("ENTERTAINMENT", "", is_income=False) == "Entertainment"


def test_map_plaid_category_travel_is_travel():
    assert map_plaid_category("TRAVEL", "", is_income=False) == "Travel"


# ------------------------------------------------------------------
# create_hosted_link_session / create_update_mode_session — request
# shape, no real network call
# ------------------------------------------------------------------

def test_create_hosted_link_session_requests_both_products(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")

    captured = {}
    fake_response = SimpleNamespace(link_token="link-token-1", hosted_link_url="https://hosted.plaid.com/abc")

    def _fake_link_token_create(req):
        captured["request"] = req
        return fake_response

    manager._client = SimpleNamespace(link_token_create=_fake_link_token_create)

    link_token, hosted_link_url = manager.create_hosted_link_session()
    assert link_token == "link-token-1"
    assert hosted_link_url == "https://hosted.plaid.com/abc"
    assert [str(p) for p in captured["request"].products] == ["balance", "transactions", "investments"]


def test_create_update_mode_session_passes_access_token_and_additional_products(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
    ))

    captured = {}
    fake_response = SimpleNamespace(link_token="link-token-2", hosted_link_url="https://hosted.plaid.com/def")

    def _fake_link_token_create(req):
        captured["request"] = req
        return fake_response

    manager._client = SimpleNamespace(link_token_create=_fake_link_token_create)

    link_token, hosted_link_url = manager.create_update_mode_session("item-1")
    assert link_token == "link-token-2"
    assert captured["request"].access_token == "access-abc"
    assert [str(p) for p in captured["request"].additional_consented_products] == ["transactions"]


def test_create_update_mode_session_raises_for_unknown_item(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    with pytest.raises(ValueError):
        manager.create_update_mode_session("no-such-item")


def test_finish_transactions_upgrade_flips_flag_in_memory_only(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
        transactions_enabled=False,
    ))
    manager.save_current_vault("hunter2")  # establish the item exists on disk before the in-memory-only flip below
    manager._client = SimpleNamespace(item_public_token_exchange=lambda req: SimpleNamespace())

    manager.finish_transactions_upgrade("item-1", "public-token-upgrade")
    assert manager.connected_items()[0].transactions_enabled is True

    # Not yet persisted — a fresh reload without saving still shows False.
    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert reloaded.connected_items()[0].transactions_enabled is False

    manager.save_current_vault("hunter2")
    reloaded_after_save = _make_manager()
    reloaded_after_save.unlock("hunter2")
    assert reloaded_after_save.connected_items()[0].transactions_enabled is True


def test_plaid_item_from_dict_backward_compatible_with_old_shape_defaults_investments_false():
    old_shape = {
        "item_id": "item-1", "access_token": "access-abc", "institution_name": "Chase",
        "connected_at": "2026-09-01T00:00:00",
    }
    item = PlaidItem.from_dict(old_shape)
    assert item.investments_enabled is False


def test_create_investments_upgrade_session_passes_access_token_and_additional_products(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
    ))

    captured = {}
    fake_response = SimpleNamespace(link_token="link-token-3", hosted_link_url="https://hosted.plaid.com/ghi")

    def _fake_link_token_create(req):
        captured["request"] = req
        return fake_response

    manager._client = SimpleNamespace(link_token_create=_fake_link_token_create)

    link_token, hosted_link_url = manager.create_investments_upgrade_session("item-1")
    assert link_token == "link-token-3"
    assert captured["request"].access_token == "access-abc"
    assert [str(p) for p in captured["request"].additional_consented_products] == ["investments"]


def test_create_investments_upgrade_session_raises_for_unknown_item(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    with pytest.raises(ValueError):
        manager.create_investments_upgrade_session("no-such-item")


def test_finish_investments_upgrade_flips_flag_in_memory_only(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
        investments_enabled=False,
    ))
    manager.save_current_vault("hunter2")
    manager._client = SimpleNamespace(item_public_token_exchange=lambda req: SimpleNamespace())

    manager.finish_investments_upgrade("item-1", "public-token-upgrade")
    assert manager.connected_items()[0].investments_enabled is True

    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert reloaded.connected_items()[0].investments_enabled is False

    manager.save_current_vault("hunter2")
    reloaded_after_save = _make_manager()
    reloaded_after_save.unlock("hunter2")
    assert reloaded_after_save.connected_items()[0].investments_enabled is True


# ------------------------------------------------------------------
# Real (non-mocked) SDK construction — same discipline that caught the
# CountryCode/cursor bugs earlier this session: build the actual plaid-
# python model classes, don't assume the shape from memory.
# ------------------------------------------------------------------

def test_investments_holdings_get_request_constructs_from_real_sdk():
    from plaid.model.investment_holdings_get_request_options import InvestmentHoldingsGetRequestOptions
    from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest

    request = InvestmentsHoldingsGetRequest(access_token="access-abc")
    assert request.access_token == "access-abc"

    request_with_options = InvestmentsHoldingsGetRequest(
        access_token="access-abc", options=InvestmentHoldingsGetRequestOptions()
    )
    assert request_with_options.access_token == "access-abc"


# ------------------------------------------------------------------
# _holdings_snapshot_for_item — resolves security names, sums the
# total, and treats a fallback/empty response as "nothing to show yet"
# ------------------------------------------------------------------

def _fake_holding(account_id="acct-1", security_id="sec-1", quantity=10.0, institution_price=150.0,
                   institution_value=1500.0, iso_currency_code="USD"):
    return SimpleNamespace(
        account_id=account_id, security_id=security_id, quantity=quantity,
        institution_price=institution_price, institution_value=institution_value,
        iso_currency_code=iso_currency_code,
    )


def _fake_security(security_id="sec-1", name="Apple Inc.", ticker_symbol="AAPL"):
    return SimpleNamespace(security_id=security_id, name=name, ticker_symbol=ticker_symbol)


def test_holdings_snapshot_for_item_resolves_names_and_sums_total(isolated_paths):
    manager = _make_manager()
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Fidelity",
                      connected_at="2026-09-01T00:00:00", investments_enabled=True)

    response = SimpleNamespace(
        is_investments_fallback_item=False,
        holdings=[_fake_holding(institution_value=1500.0), _fake_holding(account_id="acct-1", security_id="sec-2", institution_value=250.0)],
        securities=[_fake_security(), _fake_security(security_id="sec-2", name="Vanguard Total Bond", ticker_symbol="BND")],
    )
    manager._client = SimpleNamespace(investments_holdings_get=lambda req: response)

    snapshot = manager._holdings_snapshot_for_item(item)
    assert snapshot is not None
    assert snapshot["source"] == "plaid_investments_item-1"
    assert snapshot["holdings_total_value"] == 1750.0
    assert "summary" not in snapshot  # regression guard: never double-counts against sync()'s balance total
    names = {h["ticker_symbol"] for h in snapshot["holdings"]}
    assert names == {"AAPL", "BND"}


def test_holdings_snapshot_for_item_none_on_fallback_item(isolated_paths):
    manager = _make_manager()
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Fidelity",
                      connected_at="2026-09-01T00:00:00", investments_enabled=True)
    response = SimpleNamespace(is_investments_fallback_item=True, holdings=[], securities=[])
    manager._client = SimpleNamespace(investments_holdings_get=lambda req: response)
    assert manager._holdings_snapshot_for_item(item) is None


def test_holdings_snapshot_for_item_none_on_empty_holdings(isolated_paths):
    manager = _make_manager()
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Fidelity",
                      connected_at="2026-09-01T00:00:00", investments_enabled=True)
    response = SimpleNamespace(is_investments_fallback_item=False, holdings=[], securities=[])
    manager._client = SimpleNamespace(investments_holdings_get=lambda req: response)
    assert manager._holdings_snapshot_for_item(item) is None


# ------------------------------------------------------------------
# compute_net_balance_total — pure logic
# ------------------------------------------------------------------

def test_compute_net_balance_total_nets_credit_and_loan_as_liabilities():
    accounts = [
        {"type": "depository", "balances": {"current": 1000.0}},
        {"type": "credit", "balances": {"current": 200.0}},
        {"type": "investment", "balances": {"current": 5000.0}},
    ]
    assert compute_net_balance_total(accounts) == 5800.0


def test_compute_net_balance_total_none_when_all_balances_missing():
    accounts = [{"type": "depository", "balances": {}}, {"type": "credit", "balances": None}]
    assert compute_net_balance_total(accounts) is None


def test_compute_net_balance_total_real_zero_is_not_none():
    accounts = [{"type": "depository", "balances": {"current": 0.0}}]
    assert compute_net_balance_total(accounts) == 0.0


# ------------------------------------------------------------------
# sync() — investments integration
# ------------------------------------------------------------------

def test_sync_writes_summary_total_value_on_balance_snapshot(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
    ))
    fake_account = SimpleNamespace(
        account_id="acct-1", name="Checking", official_name=None, type="depository", subtype="checking",
        mask="1234", balances=SimpleNamespace(to_dict=lambda: {"current": 1234.56}),
    )
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[fake_account])
    manager._client = SimpleNamespace(accounts_get=lambda req: fake_accounts_response)
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync()
    assert result.snapshots[0]["summary"]["total_value"] == 1234.56


def test_sync_fetches_holdings_only_for_investments_enabled_items(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Fidelity", connected_at="2026-09-01T00:00:00",
        investments_enabled=True,
    ))
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Fidelity"), accounts=[])
    holdings_response = SimpleNamespace(
        is_investments_fallback_item=False,
        holdings=[_fake_holding(institution_value=1500.0)],
        securities=[_fake_security()],
    )
    manager._client = SimpleNamespace(
        accounts_get=lambda req: fake_accounts_response,
        investments_holdings_get=lambda req: holdings_response,
    )
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync()
    assert result.investment_accounts_synced == 1
    assert len(result.snapshots) == 2
    holdings_snapshot = next(s for s in result.snapshots if s["source"] == "plaid_investments_item-1")
    assert holdings_snapshot["holdings_total_value"] == 1500.0


def test_sync_skips_holdings_write_for_non_investments_item(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
        investments_enabled=False,
    ))
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    manager._client = SimpleNamespace(accounts_get=lambda req: fake_accounts_response)
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync()
    assert result.investment_accounts_synced == 0
    assert len(result.snapshots) == 1


# ------------------------------------------------------------------
# _sync_transactions_for_item — cursor-based pagination
# ------------------------------------------------------------------

def test_sync_transactions_for_item_pages_across_has_more(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", transactions_enabled=True)

    page_1 = SimpleNamespace(
        added=[_fake_transaction(transaction_id="txn-1", amount=10.0)],
        modified=[], removed=[], next_cursor="cursor-page-2", has_more=True,
    )
    page_2 = SimpleNamespace(
        added=[_fake_transaction(transaction_id="txn-2", amount=20.0)],
        modified=[], removed=[], next_cursor="cursor-final", has_more=False,
    )
    responses = [page_1, page_2]
    manager._client = SimpleNamespace(transactions_sync=lambda req: responses.pop(0))

    added, updated = manager._sync_transactions_for_item(item)
    assert added == 2
    assert updated == 0
    assert item.transactions_cursor == "cursor-final"
    assert len(manager.context.budget.all_expenses()) == 2


# ------------------------------------------------------------------
# _import_transaction / sync() — sign convention, dedup, removed
# handling, passphrase-gated persistence, context.budget is None guard
# ------------------------------------------------------------------

def test_import_transaction_positive_amount_is_an_expense(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    txn = _fake_transaction(transaction_id="txn-1", amount=45.0, primary="FOOD_AND_DRINK", detailed="")
    outcome = manager._import_transaction(txn)
    assert outcome == "added"
    expenses = manager.context.budget.all_expenses()
    assert len(expenses) == 1
    assert expenses[0].amount == 45.0
    assert expenses[0].category == "Groceries"
    assert expenses[0].plaid_transaction_id == "txn-1"
    assert manager.context.budget.all_income() == []


def test_import_transaction_negative_amount_is_income_abs_valued(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    txn = _fake_transaction(transaction_id="txn-2", amount=-1200.0, primary="INCOME", detailed="INCOME_WAGES")
    outcome = manager._import_transaction(txn)
    assert outcome == "added"
    income = manager.context.budget.all_income()
    assert len(income) == 1
    assert income[0].amount == 1200.0
    assert income[0].category == "Salary"
    assert income[0].plaid_transaction_id == "txn-2"
    assert manager.context.budget.all_expenses() == []


def test_import_transaction_zero_amount_is_skipped(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    txn = _fake_transaction(transaction_id="txn-3", amount=0.0)
    outcome = manager._import_transaction(txn)
    assert outcome == "skipped"
    assert manager.context.budget.all_expenses() == []
    assert manager.context.budget.all_income() == []


def test_import_transaction_transfer_is_skipped(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    txn = _fake_transaction(transaction_id="txn-4", amount=100.0, primary="TRANSFER_OUT", detailed="")
    outcome = manager._import_transaction(txn)
    assert outcome == "skipped"
    assert manager.context.budget.all_expenses() == []


def test_import_transaction_dedup_updates_existing_entry_on_repeat(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    first = _fake_transaction(transaction_id="txn-5", amount=45.0, primary="FOOD_AND_DRINK", detailed="")
    assert manager._import_transaction(first) == "added"

    modified = _fake_transaction(transaction_id="txn-5", amount=52.0, primary="FOOD_AND_DRINK", detailed="")
    outcome = manager._import_transaction(modified)
    assert outcome == "updated"

    expenses = manager.context.budget.all_expenses()
    assert len(expenses) == 1
    assert expenses[0].amount == 52.0


def test_sync_removed_transaction_is_logged_not_deleted(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", transactions_enabled=True)
    manager._vault.items.append(item)

    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    added_txn = _fake_transaction(transaction_id="txn-6", amount=45.0)
    sync_response = SimpleNamespace(
        added=[added_txn], modified=[], removed=[SimpleNamespace(transaction_id="txn-6")],
        next_cursor="cursor-1", has_more=False,
    )
    manager._client = SimpleNamespace(
        accounts_get=lambda req: fake_accounts_response,
        transactions_sync=lambda req: sync_response,
    )
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths_with_budget / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync(passphrase="hunter2")
    assert result.transactions_added == 1
    expenses = manager.context.budget.all_expenses()
    assert len(expenses) == 1
    assert expenses[0].plaid_transaction_id == "txn-6"


def test_sync_without_passphrase_does_not_persist_cursor(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase",
        connected_at="2026-09-01T00:00:00", transactions_enabled=True,
    ))
    manager.save_current_vault("hunter2")  # establish the item exists on disk (with an empty cursor) first
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    sync_response = SimpleNamespace(added=[], modified=[], removed=[], next_cursor="cursor-1", has_more=False)
    manager._client = SimpleNamespace(
        accounts_get=lambda req: fake_accounts_response,
        transactions_sync=lambda req: sync_response,
    )
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths_with_budget / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    manager.sync(passphrase=None)
    assert manager._vault.items[0].transactions_cursor == "cursor-1"  # in-memory

    reloaded = _make_manager_with_budget()
    reloaded.unlock("hunter2")
    assert reloaded.connected_items()[0].transactions_cursor == ""  # not persisted


def test_sync_with_passphrase_persists_cursor(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase",
        connected_at="2026-09-01T00:00:00", transactions_enabled=True,
    ))
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    sync_response = SimpleNamespace(added=[], modified=[], removed=[], next_cursor="cursor-1", has_more=False)
    manager._client = SimpleNamespace(
        accounts_get=lambda req: fake_accounts_response,
        transactions_sync=lambda req: sync_response,
    )
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths_with_budget / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    manager.sync(passphrase="hunter2")

    reloaded = _make_manager_with_budget()
    reloaded.unlock("hunter2")
    assert reloaded.connected_items()[0].transactions_cursor == "cursor-1"


def test_sync_skips_transaction_import_when_budget_is_none(isolated_paths):
    manager = _make_manager()  # no context.budget
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase",
        connected_at="2026-09-01T00:00:00", transactions_enabled=True,
    ))
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    manager._client = SimpleNamespace(accounts_get=lambda req: fake_accounts_response)
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync(passphrase="hunter2")  # must not raise
    assert result.transactions_added == 0
    assert len(result.snapshots) == 1


def test_sync_balance_only_item_unaffected(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase",
        connected_at="2026-09-01T00:00:00", transactions_enabled=False,
    ))
    fake_accounts_response = SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[])
    manager._client = SimpleNamespace(accounts_get=lambda req: fake_accounts_response)
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_paths_with_budget / "finance_import", scan_for_new_snapshots=lambda: None,
    )

    result = manager.sync()  # no passphrase needed at all
    assert result.transactions_added == 0
    assert len(result.snapshots) == 1
    assert manager.context.budget.all_expenses() == []


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
