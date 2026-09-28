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
    granted_products,
    liability_debt_fields,
    map_plaid_category,
    plaid_error_code,
    standard_card_apr,
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
    monkeypatch.setattr(budget_manager_module, "_BUSINESS_ENTITIES_FILE", data_dir / "business_entities.json")
    monkeypatch.setattr(budget_manager_module, "_DEBTS_FILE", data_dir / "debts.json")
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
    fake_item = SimpleNamespace(institution_name="Chase", products=["transactions", "investments", "liabilities"])
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
    assert item.liabilities_enabled is True
    assert len(manager.connected_items()) == 1

    manager.save_current_vault("hunter2")

    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert len(reloaded.connected_items()) == 1
    assert reloaded.connected_items()[0].institution_name == "Chase"
    assert reloaded.connected_items()[0].access_token == "access-sandbox-abc"
    assert reloaded.connected_items()[0].transactions_enabled is True
    assert reloaded.connected_items()[0].investments_enabled is True
    assert reloaded.connected_items()[0].liabilities_enabled is True


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

def test_create_hosted_link_session_requires_only_transactions(isolated_paths):
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
    # "balance" is rejected by /link/token/create, and requiring
    # investments/liabilities would hide institutions lacking them
    # (most card issuers) — both are required-if-supported instead.
    assert [str(p) for p in captured["request"].products] == ["transactions"]
    assert [str(p) for p in captured["request"].required_if_supported_products] == ["investments", "liabilities"]


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


# ------------------------------------------------------------------
# Liabilities (2026-09-27) — credit cards/student loans -> Debt records
# ------------------------------------------------------------------

def _apr(apr_type, pct):
    return SimpleNamespace(apr_type=apr_type, apr_percentage=pct)


def _card(account_id="card-1", aprs=None, minimum_payment_amount=35.0, last_statement_balance=None):
    return SimpleNamespace(
        account_id=account_id,
        aprs=aprs if aprs is not None else [_apr("purchase_apr", 24.99)],
        minimum_payment_amount=minimum_payment_amount,
        last_statement_balance=last_statement_balance,
    )


def _student(account_id="loan-1", loan_name="Sallie Mae Loan", rate=5.5, minimum_payment_amount=180.0):
    return SimpleNamespace(
        account_id=account_id, loan_name=loan_name, interest_rate_percentage=rate,
        minimum_payment_amount=minimum_payment_amount, last_statement_balance=None,
    )


def _liability_account(account_id="card-1", name="Freedom", mask="1234", current=1500.0):
    return SimpleNamespace(account_id=account_id, name=name, mask=mask, balances=SimpleNamespace(current=current))


def test_granted_products_reads_item_products_as_strings():
    assert granted_products(SimpleNamespace(products=["transactions", "liabilities"])) == {"transactions", "liabilities"}


def test_granted_products_missing_means_nothing_granted():
    assert granted_products(SimpleNamespace()) == set()
    assert granted_products(None) == set()


def test_standard_card_apr_prefers_purchase_apr():
    aprs = [_apr("cash_apr", 29.99), _apr("purchase_apr", 21.99)]
    assert standard_card_apr(aprs) == 21.99


def test_standard_card_apr_never_uses_special_promo_rate():
    aprs = [_apr("special", 0.0), _apr("balance_transfer_apr", 19.99)]
    assert standard_card_apr(aprs) == 19.99


def test_standard_card_apr_none_when_nothing_usable():
    assert standard_card_apr([_apr("special", 0.0)]) is None
    assert standard_card_apr([]) is None
    assert standard_card_apr(None) is None


def test_liability_debt_fields_credit_card():
    fields = liability_debt_fields("credit", _card(), _liability_account(), "Chase")
    assert fields == {
        "name": "Chase Freedom \u2022\u20221234",
        "debt_type": "Credit Card",
        "balance": 1500.0,
        "interest_rate": 24.99,
        "minimum_payment": 35.0,
    }


def test_liability_debt_fields_student_loan_uses_loan_name():
    fields = liability_debt_fields("student", _student(), _liability_account(account_id="loan-1", mask=None, current=15000.0), "Nelnet")
    assert fields["name"] == "Sallie Mae Loan"
    assert fields["debt_type"] == "Student Loan"
    assert fields["interest_rate"] == 5.5


def test_liability_debt_fields_falls_back_to_statement_balance():
    account = _liability_account(current=None)
    fields = liability_debt_fields("credit", _card(last_statement_balance=820.0), account, "Chase")
    assert fields["balance"] == 820.0


def test_liability_debt_fields_none_without_any_balance():
    assert liability_debt_fields("credit", _card(), _liability_account(current=None), "Chase") is None


def test_liability_debt_fields_unknown_kind_is_none():
    assert liability_debt_fields("mortgage", _card(), _liability_account(), "Chase") is None


def test_plaid_item_from_dict_backward_compatible_defaults_liabilities_false():
    item = PlaidItem.from_dict({"item_id": "i", "access_token": "a", "institution_name": "X", "connected_at": ""})
    assert item.liabilities_enabled is False


def test_finish_connection_only_enables_products_the_institution_granted(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    fake_accounts_response = SimpleNamespace(
        item=SimpleNamespace(institution_name="Discover", products=["transactions", "liabilities"]), accounts=[],
    )
    manager._client = SimpleNamespace(
        item_public_token_exchange=lambda req: SimpleNamespace(access_token="access-1", item_id="item-1"),
        accounts_get=lambda req: fake_accounts_response,
    )
    item = manager.finish_connection("public-token")
    assert item.transactions_enabled is True
    assert item.investments_enabled is False
    assert item.liabilities_enabled is True


def test_create_liabilities_upgrade_session_passes_access_token_and_additional_products(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
    ))
    captured = {}

    def _fake_link_token_create(req):
        captured["request"] = req
        return SimpleNamespace(link_token="lt", hosted_link_url="https://hosted.plaid.com/x")

    manager._client = SimpleNamespace(link_token_create=_fake_link_token_create)
    manager.create_liabilities_upgrade_session("item-1")
    assert captured["request"].access_token == "access-abc"
    assert [str(p) for p in captured["request"].additional_consented_products] == ["liabilities"]


def test_create_liabilities_upgrade_session_raises_for_unknown_item(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    with pytest.raises(ValueError):
        manager.create_liabilities_upgrade_session("nope")


def test_finish_liabilities_upgrade_flips_flag(isolated_paths):
    manager = _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
    ))
    manager._client = SimpleNamespace(item_public_token_exchange=lambda req: SimpleNamespace())
    manager.finish_liabilities_upgrade("item-1", "public-token")
    assert manager.connected_items()[0].liabilities_enabled is True


def _liabilities_response(credit=None, student=None, accounts=None):
    return SimpleNamespace(
        accounts=accounts if accounts is not None else [_liability_account()],
        liabilities=SimpleNamespace(credit=credit or [], student=student or [], mortgage=[{"ignored": True}]),
    )


def test_sync_liabilities_creates_then_updates_debt_without_duplicating(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", liabilities_enabled=True)
    responses = [
        _liabilities_response(credit=[_card()]),
        _liabilities_response(
            credit=[_card(aprs=[_apr("purchase_apr", 26.99)], minimum_payment_amount=40.0)],
            accounts=[_liability_account(current=1200.0)],
        ),
    ]
    manager._client = SimpleNamespace(liabilities_get=lambda req: responses.pop(0))

    assert manager._sync_liabilities_for_item(item) == (1, 0)
    budget = manager.context.budget
    debt = budget.all_debts()[0]
    assert debt.plaid_account_id == "card-1"
    assert debt.balance == 1500.0

    # User-owned edits must survive the next sync.
    budget.update_debt(debt.debt_id, name="My Chase Card", promo_apr=0.0, promo_expires_date="2026-12-01", notes="keep")

    assert manager._sync_liabilities_for_item(item) == (0, 1)
    assert len(budget.all_debts()) == 1
    synced = budget.get_debt(debt.debt_id)
    assert synced.balance == 1200.0
    assert synced.interest_rate == 26.99
    assert synced.minimum_payment == 40.0
    assert synced.name == "My Chase Card"
    assert synced.promo_apr == 0.0
    assert synced.promo_expires_date == "2026-12-01"
    assert synced.notes == "keep"


def test_sync_liabilities_does_not_overwrite_rate_plaid_did_not_report(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", liabilities_enabled=True)
    responses = [
        _liabilities_response(credit=[_card()]),
        _liabilities_response(credit=[_card(aprs=[], minimum_payment_amount=None)]),
    ]
    manager._client = SimpleNamespace(liabilities_get=lambda req: responses.pop(0))
    manager._sync_liabilities_for_item(item)
    manager._sync_liabilities_for_item(item)
    debt = manager.context.budget.all_debts()[0]
    assert debt.interest_rate == 24.99
    assert debt.minimum_payment == 35.0


def test_sync_liabilities_skips_accounts_missing_from_response(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", liabilities_enabled=True)
    manager._client = SimpleNamespace(
        liabilities_get=lambda req: _liabilities_response(credit=[_card(account_id="ghost")]),
    )
    assert manager._sync_liabilities_for_item(item) == (0, 0)


def test_sync_imports_student_loans_too(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Nelnet",
                      connected_at="2026-09-01T00:00:00", liabilities_enabled=True)
    manager._client = SimpleNamespace(liabilities_get=lambda req: _liabilities_response(
        student=[_student()], accounts=[_liability_account(account_id="loan-1", current=15000.0)],
    ))
    manager._sync_liabilities_for_item(item)
    debt = manager.context.budget.all_debts()[0]
    assert debt.debt_type == "Student Loan"
    assert debt.balance == 15000.0


def _sync_ready_manager(isolated_dir, liabilities_enabled, liabilities_get):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    manager._vault.items.append(PlaidItem(
        item_id="item-1", access_token="access-abc", institution_name="Chase", connected_at="2026-09-01T00:00:00",
        liabilities_enabled=liabilities_enabled,
    ))
    manager._client = SimpleNamespace(
        accounts_get=lambda req: SimpleNamespace(item=SimpleNamespace(institution_name="Chase"), accounts=[]),
        liabilities_get=liabilities_get,
    )
    manager.context.finance = SimpleNamespace(
        import_folder_path=isolated_dir / "finance_import", scan_for_new_snapshots=lambda: None,
    )
    return manager


def test_sync_reports_debt_counts(isolated_paths_with_budget):
    manager = _sync_ready_manager(
        isolated_paths_with_budget, True, lambda req: _liabilities_response(credit=[_card()]),
    )
    result = manager.sync()
    assert result.debts_added == 1
    assert result.debts_updated == 0


def test_sync_skips_liabilities_when_not_enabled(isolated_paths_with_budget):
    def _must_not_be_called(req):
        raise AssertionError("liabilities_get called for a non-liabilities item")

    manager = _sync_ready_manager(isolated_paths_with_budget, False, _must_not_be_called)
    result = manager.sync()
    assert result.debts_added == 0
    assert manager.context.budget.all_debts() == []


def test_sync_continues_when_liabilities_call_fails(isolated_paths_with_budget):
    import plaid

    def _fail(req):
        raise plaid.ApiException(status=400, reason="NO_LIABILITY_ACCOUNTS")

    manager = _sync_ready_manager(isolated_paths_with_budget, True, _fail)
    result = manager.sync()
    assert len(result.snapshots) == 1
    assert result.debts_added == 0


# ------------------------------------------------------------------
# Disconnect / reset (2026-09-27) — must free Plaid Item slots, never
# leave a removed-remotely item saved locally, and never delete the
# vault while any real connection is still live.
# ------------------------------------------------------------------

import json as _json

import plaid as _plaid


def _api_error(error_code):
    exc = _plaid.ApiException(status=400, reason="Bad Request")
    exc.body = _json.dumps({"error_code": error_code, "error_type": "ITEM_ERROR"})
    return exc


class _FakeFinance:
    def __init__(self, sources):
        self.sources = set(sources)

    def remove_snapshots(self, sources):
        removed = [s for s in sources if s in self.sources]
        self.sources -= set(removed)
        return len(removed)

    def all_latest_snapshots(self):
        return [SimpleNamespace(source=s) for s in sorted(self.sources)]


def _manager_with_items(item_ids, with_budget=False):
    manager = _make_manager_with_budget() if with_budget else _make_manager()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    for item_id in item_ids:
        manager._vault.items.append(PlaidItem(
            item_id=item_id, access_token=f"access-{item_id}", institution_name=f"Bank {item_id}",
            connected_at="2026-09-27T00:00:00",
        ))
    manager.save_current_vault("hunter2")
    return manager


def test_plaid_error_code_reads_json_body():
    assert plaid_error_code(_api_error("ITEM_NOT_FOUND")) == "ITEM_NOT_FOUND"


def test_plaid_error_code_none_for_missing_or_non_json_body():
    assert plaid_error_code(_plaid.ApiException(status=500, reason="x")) is None
    exc = _plaid.ApiException(status=500, reason="x")
    exc.body = "<html>oops</html>"
    assert plaid_error_code(exc) is None


def test_verify_passphrase(isolated_paths):
    manager = _manager_with_items([])
    assert manager.verify_passphrase("hunter2") is True
    assert manager.verify_passphrase("wrong") is False


def test_environment_reported_only_while_unlocked(isolated_paths):
    manager = _manager_with_items([])
    assert manager.environment == "sandbox"
    assert _make_manager().environment is None


def test_disconnect_item_removes_remotely_then_locally_and_persists(isolated_paths_with_budget):
    manager = _manager_with_items(["a", "b"], with_budget=True)
    removed_tokens = []
    manager._client = SimpleNamespace(item_remove=lambda req: removed_tokens.append(req.access_token))
    manager.context.finance = _FakeFinance(["plaid_a", "plaid_investments_a", "plaid_b"])
    budget = manager.context.budget
    budget.add_debt(name="Card A", balance=100.0, interest_rate=20.0, plaid_account_id="acct-a", plaid_item_id="a")
    budget.add_debt(name="Card B", balance=100.0, interest_rate=20.0, plaid_account_id="acct-b", plaid_item_id="b")

    manager.disconnect_item("a", "hunter2")

    assert removed_tokens == ["access-a"]
    assert [i.item_id for i in manager.connected_items()] == ["b"]
    assert manager.context.finance.sources == {"plaid_b"}
    card_a = next(d for d in budget.all_debts() if d.name == "Card A")
    card_b = next(d for d in budget.all_debts() if d.name == "Card B")
    assert card_a.plaid_account_id == "" and card_a.plaid_item_id == ""
    assert card_b.plaid_account_id == "acct-b"

    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert [i.item_id for i in reloaded.connected_items()] == ["b"]


def test_disconnect_item_wrong_passphrase_touches_nothing(isolated_paths):
    manager = _manager_with_items(["a"])

    def _must_not_remove(req):
        raise AssertionError("item_remove called before passphrase was verified")

    manager._client = SimpleNamespace(item_remove=_must_not_remove)
    with pytest.raises(SecretsError):
        manager.disconnect_item("a", "wrong")
    assert len(manager.connected_items()) == 1


def test_disconnect_item_already_gone_on_plaid_still_forgets_locally(isolated_paths):
    manager = _manager_with_items(["a"])

    def _gone(req):
        raise _api_error("ITEM_NOT_FOUND")

    manager._client = SimpleNamespace(item_remove=_gone)
    manager.disconnect_item("a", "hunter2")
    assert manager.connected_items() == []


def test_disconnect_item_real_plaid_failure_keeps_item_for_retry(isolated_paths):
    manager = _manager_with_items(["a"])

    def _fail(req):
        raise _api_error("INTERNAL_SERVER_ERROR")

    manager._client = SimpleNamespace(item_remove=_fail)
    with pytest.raises(_plaid.ApiException):
        manager.disconnect_item("a", "hunter2")
    assert len(manager.connected_items()) == 1
    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert len(reloaded.connected_items()) == 1


def test_reset_removes_every_item_deletes_vault_and_locks(isolated_paths_with_budget):
    manager = _manager_with_items(["a", "b"], with_budget=True)
    removed_tokens = []
    manager._client = SimpleNamespace(item_remove=lambda req: removed_tokens.append(req.access_token))
    manager.context.finance = _FakeFinance(["plaid_a", "plaid_b", "plaid_investments_old", "real_estate_portfolio"])

    result = manager.reset("hunter2", purge_imported_data=False)

    assert result.completed
    assert sorted(removed_tokens) == ["access-a", "access-b"]
    assert not manager.is_configured()
    assert not manager.is_unlocked()
    assert manager.context.finance.sources == {"real_estate_portfolio"}


def test_reset_purges_imported_data_including_synced_debts(isolated_paths_with_budget):
    manager = _manager_with_items(["a"], with_budget=True)
    manager._client = SimpleNamespace(item_remove=lambda req: None)
    manager.context.finance = _FakeFinance([])
    budget = manager.context.budget
    budget.add_expense(amount=10.0, plaid_transaction_id="t1")
    budget.add_expense(amount=20.0)  # manual — must survive
    budget.add_income(amount=5.0, plaid_transaction_id="t2")
    budget.add_debt(name="Synced", balance=1.0, interest_rate=1.0, plaid_account_id="acct-a", plaid_item_id="a")
    budget.add_debt(name="Manual", balance=1.0, interest_rate=1.0)

    result = manager.reset("hunter2", purge_imported_data=True)

    assert (result.income_purged, result.expenses_purged, result.debts_purged) == (1, 1, 1)
    assert [e.amount for e in budget.all_expenses()] == [20.0]
    assert budget.all_income() == []
    assert [d.name for d in budget.all_debts()] == ["Manual"]


def test_reset_without_purge_keeps_imported_data(isolated_paths_with_budget):
    manager = _manager_with_items(["a"], with_budget=True)
    manager._client = SimpleNamespace(item_remove=lambda req: None)
    manager.context.finance = _FakeFinance([])
    manager.context.budget.add_expense(amount=10.0, plaid_transaction_id="t1")
    manager.reset("hunter2", purge_imported_data=False)
    assert len(manager.context.budget.all_expenses()) == 1


def test_reset_stops_and_keeps_vault_if_any_removal_fails(isolated_paths_with_budget):
    manager = _manager_with_items(["a", "b"], with_budget=True)

    def _remove(req):
        if req.access_token == "access-b":
            raise _api_error("INTERNAL_SERVER_ERROR")

    manager._client = SimpleNamespace(item_remove=_remove)
    manager.context.finance = _FakeFinance([])
    manager.context.budget.add_expense(amount=10.0, plaid_transaction_id="t1")

    result = manager.reset("hunter2", purge_imported_data=True)

    assert not result.completed
    assert result.removed == ["Bank a"]
    assert result.failed == ["Bank b: INTERNAL_SERVER_ERROR"]
    assert manager.is_configured() and manager.is_unlocked()
    assert [i.item_id for i in manager.connected_items()] == ["b"]
    assert len(manager.context.budget.all_expenses()) == 1  # no purge on a stopped reset
    reloaded = _make_manager()
    reloaded.unlock("hunter2")
    assert [i.item_id for i in reloaded.connected_items()] == ["b"]


def test_reset_wrong_passphrase_touches_nothing(isolated_paths):
    manager = _manager_with_items(["a"])

    def _must_not_remove(req):
        raise AssertionError("item_remove called before passphrase was verified")

    manager._client = SimpleNamespace(item_remove=_must_not_remove)
    with pytest.raises(SecretsError):
        manager.reset("wrong", purge_imported_data=True)
    assert manager.is_configured()


def test_sync_liabilities_records_item_id_on_new_debt(isolated_paths_with_budget):
    manager = _make_manager_with_budget()
    manager.setup(client_id="cid", secret="sec", environment="sandbox", passphrase="hunter2")
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Chase",
                      connected_at="2026-09-01T00:00:00", liabilities_enabled=True)
    manager._client = SimpleNamespace(liabilities_get=lambda req: _liabilities_response(credit=[_card()]))
    manager._sync_liabilities_for_item(item)
    assert manager.context.budget.all_debts()[0].plaid_item_id == "item-1"


# ------------------------------------------------------------------
# Other loans from /accounts/get (2026-09-28): auto, personal, lines of credit
# ------------------------------------------------------------------

def _loan(account_id, subtype, current, kind="loan", name="Auto Loan", mask="4821"):
    return {"account_id": account_id, "name": name, "official_name": None, "type": kind, "subtype": subtype,
            "mask": mask, "balances": {"current": current}}


def test_loan_account_debt_fields_maps_only_the_loans_liabilities_miss():
    from core.plaid_manager import loan_account_debt_fields

    assert loan_account_debt_fields(_loan("a", "auto", 18250.0), "Ally") == {
        "name": "Ally Auto Loan ••4821", "debt_type": "Auto Loan", "balance": 18250.0}
    assert loan_account_debt_fields(_loan("b", "line of credit", 900.0, kind="credit", name="LOC"), "Chase")["debt_type"] == "Personal Loan"
    assert loan_account_debt_fields(_loan("c", "credit card", 900.0, kind="credit"), "Chase") is None  # liabilities' job
    assert loan_account_debt_fields(_loan("d", "mortgage", 150000.0), "Chase") is None  # Real Estate's
    assert loan_account_debt_fields(_loan("e", "student", 9000.0), "Nelnet")["debt_type"] == "Student Loan"
    assert loan_account_debt_fields(_loan("e", "student", 9000.0), "Nelnet", liabilities_enabled=True) is None
    assert loan_account_debt_fields(_loan("f", "auto", None), "Ally") is None
    assert loan_account_debt_fields({"type": "depository", "subtype": "checking", "balances": {"current": 5}}, "Ally") is None


def test_sync_loan_accounts_creates_then_updates_only_the_balance(isolated_paths_with_budget):
    from core.plaid_manager import LOAN_RATE_NOTE

    manager = _make_manager_with_budget()
    item = PlaidItem(item_id="item-1", access_token="access-abc", institution_name="Ally", connected_at="2026-09-01T00:00:00")
    assert manager._sync_loan_accounts(item, [_loan("acct-auto", "auto", 18250.0)]) == (1, 0)
    [debt] = manager.context.budget.all_debts()
    assert (debt.debt_type, debt.balance, debt.interest_rate, debt.notes) == ("Auto Loan", 18250.0, 0.0, LOAN_RATE_NOTE)
    manager.context.budget.update_debt(debt.debt_id, interest_rate=6.9, minimum_payment=455.0)  # the owner fills them in
    assert manager._sync_loan_accounts(item, [_loan("acct-auto", "auto", 17800.0)]) == (0, 1)
    [debt] = manager.context.budget.all_debts()
    assert (debt.balance, debt.interest_rate, debt.minimum_payment) == (17800.0, 6.9, 455.0)
