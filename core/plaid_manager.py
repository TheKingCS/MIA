"""
core.plaid_manager
=====================

Bank/brokerage connectivity via Plaid — the one credible third-party
path found after real research (2026-09-08): Robinhood has no public
stocks API (crypto-only officially; everything else is unofficial and
ToS-violating), Chime's own API is a B2B "Partner API," not self-
service for an individual. Plaid connects both — most brokerages
including Robinhood, and Chime as a bank — in one integration.

This is a real, explicit tension with docs/VISION.md's offline-first/
no-third-party-in-the-loop principle — accepted by the user knowingly,
not glossed over.

**Plaid Link has no native desktop SDK** (built for web/mobile only),
and this repo has a confirmed real blocker for embedding web content
(`PySide6.QtWebEngineWidgets` fails to import here — missing
`libnspr4.so`, no sudo — the same issue that ruled out a Leaflet.js map
earlier in this project). Plaid's **Hosted Link** mode sidesteps this
entirely: `create_hosted_link_session()` returns a plain URL, opened in
the user's own system browser (`webbrowser.open()`, stdlib, no new
widget/dependency) instead of embedded. After the user finishes in
their browser, MIA has no public server to receive a webhook (offline-
first, by design) — so `poll_for_public_token()` polls Plaid's own
`/link/token/get` instead, which is Plaid's own documented approach for
integrations that don't use webhooks.

**Credentials**: one encrypted vault (`core.secrets_manager.encrypt_bytes`/
`decrypt_bytes` — Fernet + PBKDF2, already used for encrypted Backup/
Restore, already a dependency via `cryptography`) holds the app's own
`client_id`/`secret`/environment AND every connected bank's real
`access_token`. Chosen over the OS `keyring` package: `keyring` would
be a new dependency confirmed unverifiable in this dev sandbox (no
keyring daemon running here) with real risk of being unavailable on
some real Linux desktops too. The vault is unlocked with a passphrase
once per session (decrypted into memory, held only for this run, never
re-persisted in plaintext — same discipline core.backup_manager's own
encrypted-backup passphrase flow already follows) rather than reading
it fresh from disk on every call.

**Offline caching, per the user's explicit requirement**: sync() never
hands live data straight to a widget. It writes a real
core.finance_manager.FinancialSnapshot-shaped JSON file into
context.finance.import_folder_path — the exact same watched folder
Kraken/real-estate ingestion already uses — and calls
context.finance.scan_for_new_snapshots() for immediate pickup.
core/finance_manager.py's existing latest_snapshot() then only ever
serves the last successfully imported snapshot, never a live re-fetch —
so losing internet just means sync() can't produce a new one; the last
real data stays visible. Zero new ingestion/caching code needed.

**Real, honest limitation**: none of this can be verified against
Plaid's real API (not even Sandbox, which is safe/fake-data-only) with
out the user creating their own free Plaid developer account and
sharing a client_id/Sandbox secret — there is no way around that, and
it hasn't happened as of this file's writing. Every method here that
doesn't need live credentials (the vault crypto round-trip, the polling
stopping logic, the snapshot-shape building) is unit-tested; the real
network calls are not, and are flagged as such rather than assumed
correct.

**Investments/holdings (added 2026-09-09)**: real research confirmed
Fidelity IS supported via Plaid, but on Plaid's free/Pay-as-you-go
tier, actually seeing Fidelity holdings requires the user to file a
support ticket with Plaid requesting Investments product access for
their account first — Plaid's API itself doesn't error on a
non-qualifying item, it just returns `is_investments_fallback_item=True`
with no holdings. `_holdings_snapshot_for_item()` below treats that
response (and a genuinely empty `holdings` list) as "nothing to show
yet" and writes no snapshot at all, rather than surfacing it as a bug.

**Liabilities (added 2026-09-27)**: credit cards and student loans
from /liabilities/get become real `core.budget_manager.Debt` records,
deduped by `Debt.plaid_account_id`, so they show up in the Debts tab's
payoff ranking like a manually-entered debt. Plaid owns balance, the
standard APR, and the minimum payment (re-synced every time — the
bank is the source of truth for those); the user owns everything else
(name after creation, debt type, entity, notes, and the promo APR +
expiration — Plaid's "special" APR type carries no expiration date, so
it can't populate a promo that `effective_apr()` would honor anyway).
Mortgages are deliberately skipped (see Debt's own docstring — they
belong to core.real_estate_manager.Property).

**Other loans (added 2026-09-28)**: auto loans, personal loans and lines
of credit aren't in /liabilities/get, but every sync's /accounts/get
already returns them (type `loan`, or `credit` with subtype `line of
credit`) with a balance. `loan_account_debt_fields()` turns those into
Debts too (no extra Plaid product or consent needed). Plaid reports no
rate or minimum for them, so a new one starts at 0% with a note asking
the owner to fill them in; syncs only ever update the balance.

**Connect request fix (2026-09-27)**: `create_hosted_link_session()`
originally listed `balance` in `products`, which Plaid's
/link/token/create rejects outright (Balance is initialized
automatically by any other product), and listed `investments` there
too, which hides every institution that doesn't support investments —
most card issuers. Now only `transactions` is required; `investments`
and `liabilities` go in `required_if_supported_products`, and
`finish_connection()` reads which ones the institution actually
granted from the Item's own `products` list rather than assuming.

**Disconnect/reset (2026-09-27)**: `disconnect_item()` calls Plaid's
/item/remove before forgetting an item locally. Just deleting the
local record would leave the Item live on Plaid's side, where it keeps
counting against the Trial plan's 10-Item Production cap.
`reset()` does the same for every item and only deletes the vault
once none of them failed to remove. An item Plaid reports as already
gone is dropped locally without error. The passphrase is verified
*before* anything is removed remotely, so a typo can't leave a
removed-remotely-but-still-saved-locally item behind.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Optional

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.link_token_create_hosted_link import LinkTokenCreateHostedLink
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions

from core.app_context import AppContext
from core.atomic_write import atomic_write_text
from core.logger import get_logger
from core.secrets_manager import SecretsError, decrypt_bytes, encrypt_bytes

if TYPE_CHECKING:
    from plaid.model.link_token_get_response import LinkTokenGetResponse

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_VAULT_FILE = _DATA_DIR / "plaid_vault.enc"

ENVIRONMENTS = ["sandbox", "production"]


@dataclass
class PlaidItem:
    item_id: str
    access_token: str
    institution_name: str
    connected_at: str  # ISO datetime
    transactions_enabled: bool = False  # Transactions product consent granted
    transactions_cursor: str = ""  # last next_cursor from /transactions/sync — "" means never synced yet
    investments_enabled: bool = False  # Investments product consent granted
    liabilities_enabled: bool = False  # Liabilities product consent granted

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id, "access_token": self.access_token,
            "institution_name": self.institution_name, "connected_at": self.connected_at,
            "transactions_enabled": self.transactions_enabled, "transactions_cursor": self.transactions_cursor,
            "investments_enabled": self.investments_enabled,
            "liabilities_enabled": self.liabilities_enabled,
        }

    @staticmethod
    def from_dict(data: dict) -> "PlaidItem":
        return PlaidItem(
            item_id=data.get("item_id", ""),
            access_token=data.get("access_token", ""),
            institution_name=data.get("institution_name", ""),
            connected_at=data.get("connected_at", ""),
            transactions_enabled=data.get("transactions_enabled", False),
            transactions_cursor=data.get("transactions_cursor", ""),
            investments_enabled=data.get("investments_enabled", False),
            liabilities_enabled=data.get("liabilities_enabled", False),
        )


@dataclass
class PlaidVault:
    client_id: str = ""
    secret: str = ""
    environment: str = "sandbox"  # one of ENVIRONMENTS
    items: list[PlaidItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "client_id": self.client_id, "secret": self.secret, "environment": self.environment,
            "items": [i.to_dict() for i in self.items],
        }

    @staticmethod
    def from_dict(data: dict) -> "PlaidVault":
        return PlaidVault(
            client_id=data.get("client_id", ""),
            secret=data.get("secret", ""),
            environment=data.get("environment", "sandbox"),
            items=[PlaidItem.from_dict(d) for d in data.get("items", [])],
        )


def extract_completed_public_token(get_response: "LinkTokenGetResponse") -> Optional[str]:
    """Pure logic — testable without a real Plaid client (see
    tests/test_plaid_manager.py). Digs through a real
    LinkTokenGetResponse-shaped object for the first completed session's
    public_token, if any exist yet."""
    for session in get_response.link_sessions or []:
        results = session.results
        if results is None:
            continue
        for item_result in results.item_add_results or []:
            if item_result.public_token:
                return item_result.public_token
    return None


@dataclass
class PlaidSyncResult:
    snapshots: list[dict]
    transactions_added: int = 0
    transactions_updated: int = 0
    investment_accounts_synced: int = 0
    debts_added: int = 0
    debts_updated: int = 0


_LIABILITY_ACCOUNT_TYPES = {"credit", "loan"}


def compute_net_balance_total(accounts: list[dict]) -> Optional[float]:
    """Pure logic — testable without a real Plaid client. Sums each
    account's balances["current"] (never "available") as an asset,
    except for credit/loan accounts which are subtracted as
    liabilities — real assets-minus-liabilities math for one
    institution's snapshot. Returns None only when every account lacks
    a usable current balance, so a genuine $0 net total is never
    confused with "no data" — same convention
    gui.home_dashboard.format_net_worth_line() already applies to a
    missing summary.total_value."""
    total = 0.0
    saw_any = False
    for account in accounts:
        current = (account.get("balances") or {}).get("current")
        if current is None:
            continue
        saw_any = True
        total += -current if account.get("type") in _LIABILITY_ACCOUNT_TYPES else current
    return total if saw_any else None


def map_plaid_category(primary: str, detailed: str, is_income: bool) -> Optional[str]:
    """Pure logic — testable without Qt or a real Plaid client. Maps a
    Plaid personal_finance_category (primary/detailed strings — see
    https://plaid.com/documents/pfc-taxonomy-all.csv, fetched live
    2026-09-08, not assumed from memory) onto MIA's own fixed
    INCOME_CATEGORIES/EXPENSE_CATEGORIES lists.

    Returns None to mean "skip this transaction entirely" — used only
    for TRANSFER_IN/TRANSFER_OUT, an internal transfer between the
    user's own linked accounts, which would otherwise double-count as
    fake income on one side and a fake expense on the other.

    Deliberately conservative: only primary categories with a clear,
    defensible MIA-category correspondence get a specific mapping;
    everything else — including any primary value Plaid adds in the
    future that this function doesn't recognize (the SDK does not
    locally enforce the taxonomy, it's validated server-side only) —
    falls through to "Other", never a guessed category. "Rental Income"
    is never auto-assigned here: Plaid's PFC has no reliable landlord
    signal, so rental income stays a manual-entry-only category via
    core.budget_manager's IncomeSource/property_id path."""
    primary = (primary or "").upper()
    detailed = (detailed or "").upper()

    if is_income:
        if primary == "INCOME":
            if "DIVIDEND" in detailed or "INTEREST" in detailed:
                return "Investment"
            return "Salary"
        if primary == "TRANSFER_IN":
            return None
        return "Other"  # LOAN_DISBURSEMENTS and anything unrecognized

    if primary == "RENT_AND_UTILITIES":
        # NOT "RENT" in detailed — the primary category name itself
        # contains "RENT" ("RENT_AND_UTILITIES"), and every detailed
        # value under it is prefixed with the primary name (e.g.
        # "RENT_AND_UTILITIES_GAS_AND_ELECTRICITY"), so a plain
        # substring check always matched. Plaid's real "it's actually
        # rent" detailed value ends with "_RENT" specifically.
        return "Mortgage/Rent" if detailed.endswith("_RENT") else "Utilities"
    if primary == "FOOD_AND_DRINK":
        return "Groceries"
    if primary == "TRANSPORTATION":
        return "Transportation"
    if primary == "HOME_IMPROVEMENT":
        return "Maintenance"
    if primary == "GENERAL_SERVICES":
        return "Insurance" if "INSURANCE" in detailed else "Other"
    if primary == "GOVERNMENT_AND_NON_PROFIT":
        return "Taxes" if "TAX" in detailed else "Other"
    if primary == "LOAN_PAYMENTS":
        return "Mortgage/Rent" if "MORTGAGE" in detailed else "Other"
    if primary == "TRANSFER_OUT":
        return None
    # 2026-09-09: these six previously fell through to "Other" — a real
    # gap for anyone with actual Plaid-synced spending, since a
    # meaningful fraction of real transactions land in exactly these
    # categories. EXPENSE_CATEGORIES grew a matching entry for each.
    if primary == "MEDICAL":
        return "Medical"
    if primary == "PERSONAL_CARE":
        return "Personal Care"
    if primary == "GENERAL_MERCHANDISE":
        return "Shopping"
    if primary == "BANK_FEES":
        return "Bank Fees"
    if primary == "ENTERTAINMENT":
        return "Entertainment"
    if primary == "TRAVEL":
        return "Travel"
    return "Other"  # OTHER, and any future Plaid category this function doesn't yet recognize


# Plaid error codes meaning the Item is already gone on Plaid's side —
# safe to forget locally without a successful /item/remove.
_ALREADY_GONE_ERROR_CODES = {"ITEM_NOT_FOUND", "INVALID_ACCESS_TOKEN"}


def plaid_error_code(exc) -> Optional[str]:
    """Pure logic — testable without a real Plaid client. Pulls
    Plaid's error_code out of a plaid.ApiException's JSON body; None
    when the body is missing or isn't Plaid's error JSON."""
    try:
        return json.loads(getattr(exc, "body", None) or "").get("error_code")
    except (ValueError, AttributeError):
        return None


@dataclass
class PlaidResetResult:
    removed: list[str] = field(default_factory=list)  # institution names
    failed: list[str] = field(default_factory=list)  # "Name: reason" — reset aborted if non-empty
    income_purged: int = 0
    expenses_purged: int = 0
    debts_purged: int = 0

    @property
    def completed(self) -> bool:
        return not self.failed


def granted_products(plaid_item) -> set[str]:
    """Pure logic — testable without a real Plaid client. The product
    names an Item actually has initialized (Plaid's Item.products),
    as plain strings. Missing/None means nothing is known to be
    granted — callers treat that as "not enabled," never assume."""
    return {str(p) for p in (getattr(plaid_item, "products", None) or [])}


def standard_card_apr(aprs) -> Optional[float]:
    """Pure logic — testable without a real Plaid client. The card's
    standard (non-promotional) rate: its purchase APR when reported,
    otherwise the highest non-"special" APR (cash/balance-transfer/
    penalty), since that's the conservative choice for payoff ranking.
    "special" is Plaid's promotional-rate bucket and is never used as
    the standard rate. None when no usable APR is reported at all."""
    usable = [a for a in (aprs or []) if a.apr_percentage is not None and str(a.apr_type) != "special"]
    for apr in usable:
        if str(apr.apr_type) == "purchase_apr":
            return apr.apr_percentage
    return max((a.apr_percentage for a in usable), default=None)


def liability_debt_fields(kind: str, liability, account, institution_name: str) -> Optional[dict]:
    """Pure logic — testable without a real Plaid client. One Plaid
    credit-card or student-loan liability (plus its matching account,
    for the balance and display name) -> the Debt fields Plaid owns.
    interest_rate/minimum_payment are None when Plaid didn't report
    them, so a sync never overwrites a real value with a guess.
    Returns None when there's no usable current balance to track."""
    balances = getattr(account, "balances", None)
    balance = getattr(balances, "current", None) if balances is not None else None
    if balance is None:
        balance = getattr(liability, "last_statement_balance", None)
    if balance is None:
        return None

    account_name = getattr(account, "name", None) or "Account"
    mask = getattr(account, "mask", None)
    mask_part = f" \u2022\u2022{mask}" if mask else ""

    if kind == "credit":
        return {
            "name": f"{institution_name} {account_name}{mask_part}",
            "debt_type": "Credit Card",
            "balance": max(0.0, balance),
            "interest_rate": standard_card_apr(liability.aprs),
            "minimum_payment": liability.minimum_payment_amount,
        }
    if kind == "student":
        return {
            "name": f"{liability.loan_name or account_name}{mask_part}",
            "debt_type": "Student Loan",
            "balance": max(0.0, balance),
            "interest_rate": liability.interest_rate_percentage,
            "minimum_payment": liability.minimum_payment_amount,
        }
    return None


_LOAN_DEBT_TYPES = {"auto": "Auto Loan", "personal": "Personal Loan", "consumer": "Personal Loan",
                    "loan": "Personal Loan", "line of credit": "Personal Loan", "student": "Student Loan"}
_NOT_A_DEBT_HERE = {"mortgage", "home equity"}  # the house's, in Real Estate (see Debt's docstring)
LOAN_RATE_NOTE = "The bank doesn't report this loan's interest rate or minimum payment. Add them so payoff advice is right."


def loan_account_debt_fields(account: dict, institution_name: str, liabilities_enabled: bool = False) -> Optional[dict]:
    """Pure logic. One /accounts/get account (as _account_to_dict makes
    it) -> Debt fields, for loans /liabilities/get doesn't cover: auto,
    personal, lines of credit (and student loans when the item has no
    Liabilities access). None for anything else, or no balance."""
    kind = (account.get("type") or "").lower()
    subtype = (account.get("subtype") or "").lower()
    if kind == "credit" and subtype != "line of credit":
        return None  # credit cards come from /liabilities/get
    if kind not in ("loan", "credit") or subtype in _NOT_A_DEBT_HERE:
        return None
    if subtype == "student" and liabilities_enabled:
        return None  # /liabilities/get has the real rate and minimum
    balance = (account.get("balances") or {}).get("current")
    if balance is None:
        return None
    mask = account.get("mask")
    name = account.get("name") or account.get("official_name") or "Loan"
    return {
        "name": f"{institution_name} {name}" + (f" \u2022\u2022{mask}" if mask else ""),
        "debt_type": _LOAN_DEBT_TYPES.get(subtype, "Other"),
        "balance": max(0.0, float(balance)),
    }


class PlaidManager:
    def __init__(self, context: AppContext, data_dir: Optional[Path] = None) -> None:
        # Whose data: a household's own folder (core/personal_data.py), or data/ by default.
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._vault_file = self.data_dir / "plaid_vault.enc" if data_dir is not None else _VAULT_FILE
        self.context = context
        self._vault: Optional[PlaidVault] = None
        self._client: Optional[plaid_api.PlaidApi] = None

    # ------------------------------------------------------------------
    # Vault setup / unlock
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return self._vault_file.exists()

    def is_unlocked(self) -> bool:
        return self._vault is not None

    @property
    def environment(self) -> Optional[str]:
        """"sandbox"/"production" while unlocked, else None."""
        return self._vault.environment if self._vault is not None else None

    def verify_passphrase(self, passphrase: str) -> bool:
        """True if passphrase decrypts the saved vault file."""
        if not self._vault_file.exists():
            return False
        try:
            decrypt_bytes(self._vault_file.read_bytes(), passphrase)
        except SecretsError:
            return False
        return True

    def setup(self, client_id: str, secret: str, environment: str, passphrase: str) -> None:
        """First-time setup — creates a new vault with the app's own
        Plaid credentials (obtained by the user from their own Plaid
        Dashboard signup — never fabricated or created on their
        behalf) and no connected banks yet."""
        vault = PlaidVault(
            client_id=client_id, secret=secret,
            environment=environment if environment in ENVIRONMENTS else "sandbox",
            items=[],
        )
        self._save_vault(vault, passphrase)
        self._vault = vault
        self._client = self._build_client(vault)
        log.info("Plaid vault created (%s environment).", vault.environment)

    def unlock(self, passphrase: str) -> None:
        """Raises core.secrets_manager.SecretsError on a wrong passphrase or corrupted vault file."""
        if not self._vault_file.exists():
            raise SecretsError("No Plaid vault has been set up yet.")
        blob = self._vault_file.read_bytes()
        plaintext = decrypt_bytes(blob, passphrase)
        vault = PlaidVault.from_dict(json.loads(plaintext))
        self._vault = vault
        self._client = self._build_client(vault)
        log.info("Plaid vault unlocked (%d connected item(s)).", len(vault.items))

    def _save_vault(self, vault: PlaidVault, passphrase: str) -> None:
        plaintext = json.dumps(vault.to_dict()).encode("utf-8")
        blob = encrypt_bytes(plaintext, passphrase)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._vault_file.write_bytes(blob)

    @staticmethod
    def _build_client(vault: PlaidVault) -> plaid_api.PlaidApi:
        host = plaid.Environment.Production if vault.environment == "production" else plaid.Environment.Sandbox
        configuration = plaid.Configuration(host=host, api_key={"clientId": vault.client_id, "secret": vault.secret})
        return plaid_api.PlaidApi(plaid.ApiClient(configuration))

    def _require_unlocked(self) -> None:
        if self._vault is None or self._client is None:
            raise RuntimeError("Plaid vault is locked — call unlock(passphrase) first.")

    # ------------------------------------------------------------------
    # Connecting a bank (Hosted Link + polling)
    # ------------------------------------------------------------------

    def create_hosted_link_session(self) -> tuple[str, str]:
        """Returns (link_token, hosted_link_url) — open hosted_link_url
        in the user's system browser (webbrowser.open()), then pass
        link_token to poll_for_public_token()."""
        self._require_unlocked()
        request = LinkTokenCreateRequest(
            client_name="MIA Home",
            language="en",
            country_codes=[CountryCode("US")],
            user=LinkTokenCreateRequestUser(client_user_id=uuid.uuid4().hex),
            products=[Products("transactions")],
            required_if_supported_products=[Products("investments"), Products("liabilities")],
            hosted_link=LinkTokenCreateHostedLink(),
        )
        response = self._client.link_token_create(request)
        return response.link_token, response.hosted_link_url

    def create_update_mode_session(self, item_id: str) -> tuple[str, str]:
        """Same shape as create_hosted_link_session(), but for an
        ALREADY-connected item that was linked before Transactions was
        requested (e.g. before this feature existed) — Plaid's
        documented "update mode" Link flow: pass the existing item's
        access_token plus additional_consented_products, completed via
        the exact same Hosted-Link-URL + check_public_token_once()
        polling as a fresh connection, then finish_transactions_upgrade()
        below (not finish_connection(), which would create a duplicate
        PlaidItem for an access_token MIA already has)."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        request = LinkTokenCreateRequest(
            client_name="MIA Home",
            language="en",
            country_codes=[CountryCode("US")],
            user=LinkTokenCreateRequestUser(client_user_id=uuid.uuid4().hex),
            access_token=item.access_token,
            additional_consented_products=[Products("transactions")],
            hosted_link=LinkTokenCreateHostedLink(),
        )
        response = self._client.link_token_create(request)
        return response.link_token, response.hosted_link_url

    def create_investments_upgrade_session(self, item_id: str) -> tuple[str, str]:
        """Same shape as create_update_mode_session() above, but for
        Investments — a separate method (not a generalized one) so the
        already-tested Transactions upgrade path stays untouched. See
        that method's docstring for the full update-mode reasoning."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        request = LinkTokenCreateRequest(
            client_name="MIA Home",
            language="en",
            country_codes=[CountryCode("US")],
            user=LinkTokenCreateRequestUser(client_user_id=uuid.uuid4().hex),
            access_token=item.access_token,
            additional_consented_products=[Products("investments")],
            hosted_link=LinkTokenCreateHostedLink(),
        )
        response = self._client.link_token_create(request)
        return response.link_token, response.hosted_link_url

    def create_liabilities_upgrade_session(self, item_id: str) -> tuple[str, str]:
        """Same shape as create_investments_upgrade_session(), for
        Liabilities — for an item connected before Liabilities was
        requested at connect time."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        request = LinkTokenCreateRequest(
            client_name="MIA Home",
            language="en",
            country_codes=[CountryCode("US")],
            user=LinkTokenCreateRequestUser(client_user_id=uuid.uuid4().hex),
            access_token=item.access_token,
            additional_consented_products=[Products("liabilities")],
            hosted_link=LinkTokenCreateHostedLink(),
        )
        response = self._client.link_token_create(request)
        return response.link_token, response.hosted_link_url

    def check_public_token_once(self, link_token: str) -> Optional[str]:
        """A single, non-blocking /link/token/get check — the piece a
        GUI event loop can safely call directly (e.g. once per QTimer
        tick) without freezing the UI thread the way a real sleep-loop
        would. poll_for_public_token() below is built out of repeated
        calls to this same method, so both share one source of truth
        for "how do we read a completion out of a response"."""
        self._require_unlocked()
        response = self._client.link_token_get(LinkTokenGetRequest(link_token=link_token))
        return extract_completed_public_token(response)

    def poll_for_public_token(
        self,
        link_token: str,
        timeout_seconds: float = 180,
        poll_interval_seconds: float = 3,
        sleep_fn: Callable[[float], None] = time.sleep,
        now_fn: Callable[[], float] = time.monotonic,
    ) -> Optional[str]:
        """Blocking convenience wrapper around check_public_token_once()
        for a non-GUI caller (tests, a future CLI/Assistant path) — polls
        until a public_token appears or timeout_seconds elapses
        (returning None). sleep_fn/now_fn are injectable so this loop's
        stopping logic is unit-testable without a real 180-second wait
        (see tests/test_plaid_manager.py). The GUI itself never calls
        this directly — see modules/budget/module.py's own QTimer-driven
        use of check_public_token_once() instead, which doesn't block
        the UI thread between checks."""
        deadline = now_fn() + timeout_seconds
        while True:
            token = self.check_public_token_once(link_token)
            if token is not None:
                return token
            if now_fn() >= deadline:
                return None
            sleep_fn(poll_interval_seconds)

    def finish_connection(self, public_token: str) -> PlaidItem:
        """Exchanges the temporary public_token for a real permanent
        access_token, looks up the institution's display name, and
        appends a new PlaidItem to the IN-MEMORY vault only — it does
        NOT persist to disk. Call save_current_vault(passphrase)
        afterward to actually encrypt and save; kept as two separate
        steps rather than caching the unlock passphrase in memory to
        auto-save here, same "never hold a passphrase longer than the
        one call that needs it" discipline core.backup_manager's own
        encrypted backup/restore already follows (its passphrase is a
        one-shot parameter, never stored on the instance either)."""
        self._require_unlocked()
        exchange_response = self._client.item_public_token_exchange(
            ItemPublicTokenExchangeRequest(public_token=public_token)
        )
        access_token = exchange_response.access_token
        item_id = exchange_response.item_id

        institution_name = "Unknown institution"
        accounts_response = self._client.accounts_get(AccountsGetRequest(access_token=access_token))
        if accounts_response.item is not None and accounts_response.item.institution_name:
            institution_name = accounts_response.item.institution_name
        # investments/liabilities are required-if-supported (see
        # create_hosted_link_session), so whether this institution
        # actually granted them is read from the Item, never assumed.
        granted = granted_products(accounts_response.item)

        new_item = PlaidItem(
            item_id=item_id, access_token=access_token, institution_name=institution_name,
            connected_at=datetime.now().isoformat(timespec="seconds"),
            transactions_enabled=True,  # the one required product — Link can't complete without it
            investments_enabled="investments" in granted,
            liabilities_enabled="liabilities" in granted,
        )
        self._vault.items.append(new_item)
        log.info("Connected Plaid item: '%s' (%s)", new_item.institution_name, new_item.item_id)
        return new_item

    def finish_transactions_upgrade(self, item_id: str, public_token: str) -> None:
        """The update-mode counterpart to finish_connection() — for an
        item that was connected before Transactions was requested.
        Exchanges the update-mode public_token (no new access_token or
        PlaidItem — the item already has one) and flips
        transactions_enabled True on the IN-MEMORY item only, same
        two-step "caller still calls save_current_vault(passphrase)"
        discipline as finish_connection()."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        self._client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        item.transactions_enabled = True
        log.info("Transactions access added for Plaid item '%s'.", item.institution_name)

    def finish_investments_upgrade(self, item_id: str, public_token: str) -> None:
        """The update-mode counterpart to finish_connection() for
        Investments — same shape as finish_transactions_upgrade()
        above, kept as a separate method for the same reason."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        self._client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        item.investments_enabled = True
        log.info("Investments access added for Plaid item '%s'.", item.institution_name)

    def finish_liabilities_upgrade(self, item_id: str, public_token: str) -> None:
        """The update-mode counterpart to finish_connection() for
        Liabilities — same shape as finish_investments_upgrade()."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        self._client.item_public_token_exchange(ItemPublicTokenExchangeRequest(public_token=public_token))
        item.liabilities_enabled = True
        log.info("Liabilities access added for Plaid item '%s'.", item.institution_name)

    def save_current_vault(self, passphrase: str) -> None:
        """Re-encrypts and persists the in-memory vault (e.g. after
        finish_connection() appended a new item) — a separate explicit
        call rather than auto-saving on every mutation, since the
        passphrase needed to encrypt isn't necessarily still held
        anywhere after unlock() returns (callers keep it only as long
        as they need it, same discipline core.backup_manager takes)."""
        self._require_unlocked()
        self._save_vault(self._vault, passphrase)

    def _remove_remote_item(self, item: PlaidItem) -> None:
        """/item/remove — raises plaid.ApiException on a real failure;
        returns quietly when Plaid says the item is already gone."""
        try:
            self._client.item_remove(ItemRemoveRequest(access_token=item.access_token))
        except plaid.ApiException as exc:
            if plaid_error_code(exc) not in _ALREADY_GONE_ERROR_CODES:
                raise
            log.info("Plaid item '%s' was already removed on Plaid's side.", item.institution_name)

    def _forget_item_locally(self, item: PlaidItem) -> None:
        self._vault.items = [i for i in self._vault.items if i.item_id != item.item_id]
        if self.context.finance is not None:
            self.context.finance.remove_snapshots([f"plaid_{item.item_id}", f"plaid_investments_{item.item_id}"])
        if self.context.budget is not None:
            self.context.budget.unlink_plaid_debts_for_item(item.item_id)

    def disconnect_item(self, item_id: str, passphrase: str) -> None:
        """Removes one bank connection on Plaid's side (freeing its
        Item slot), then forgets it locally and saves the vault. Its
        balance snapshots are dropped from net worth; its synced debts
        become manual debts; imported transactions stay (they're real
        history). Raises SecretsError for a wrong passphrase before
        touching anything, or plaid.ApiException if Plaid refuses the
        removal (the item is then kept, so it can be retried)."""
        self._require_unlocked()
        item = self._get_item(item_id)
        if item is None:
            raise ValueError(f"No connected Plaid item with id '{item_id}'.")
        if not self.verify_passphrase(passphrase):
            raise SecretsError("Wrong passphrase for the Plaid vault.")
        self._remove_remote_item(item)
        self._forget_item_locally(item)
        self._save_vault(self._vault, passphrase)
        log.info("Disconnected Plaid item '%s' (%s).", item.institution_name, item.item_id)

    def reset(self, passphrase: str, purge_imported_data: bool) -> PlaidResetResult:
        """Disconnects every item (as disconnect_item()), and — only if
        all of them were removed — deletes the vault and locks, so
        Set Up Plaid can be run again (e.g. with Production keys).
        If any removal fails, nothing more is deleted: the vault is
        saved with just the items still connected, and the result lists
        the failures so the user can retry. purge_imported_data also
        deletes every Plaid-imported transaction and synced debt (see
        BudgetManager.remove_plaid_imported_data()) — meant for clearing
        fake Sandbox data."""
        self._require_unlocked()
        if not self.verify_passphrase(passphrase):
            raise SecretsError("Wrong passphrase for the Plaid vault.")

        result = PlaidResetResult()
        removed_items = []
        for item in list(self._vault.items):
            try:
                self._remove_remote_item(item)
            except plaid.ApiException as exc:
                result.failed.append(f"{item.institution_name}: {plaid_error_code(exc) or exc.reason}")
                continue
            removed_items.append(item)
            result.removed.append(item.institution_name)

        if not result.completed:
            for item in removed_items:
                self._forget_item_locally(item)
            self._save_vault(self._vault, passphrase)
            log.warning("Plaid reset stopped — %d item(s) could not be removed.", len(result.failed))
            return result

        # Purge before forgetting items — forgetting unlinks synced
        # debts (clears plaid_account_id), which would hide them from
        # the purge.
        if purge_imported_data and self.context.budget is not None:
            result.income_purged, result.expenses_purged, result.debts_purged = (
                self.context.budget.remove_plaid_imported_data()
            )
        for item in removed_items:
            self._forget_item_locally(item)
        if self.context.finance is not None:
            leftover = [s.source for s in self.context.finance.all_latest_snapshots() if s.source.startswith("plaid_")]
            self.context.finance.remove_snapshots(leftover)

        self._vault_file.unlink(missing_ok=True)
        self._vault = None
        self._client = None
        log.info("Plaid reset complete — vault deleted, %d item(s) removed.", len(result.removed))
        return result

    def connected_items(self) -> list[PlaidItem]:
        self._require_unlocked()
        return list(self._vault.items)

    def _get_item(self, item_id: str) -> Optional[PlaidItem]:
        self._require_unlocked()
        for item in self._vault.items:
            if item.item_id == item_id:
                return item
        return None

    # ------------------------------------------------------------------
    # Sync — balances write into core.finance_manager's existing watched
    # folder (never hands live data straight to a widget, see module
    # docstring); transactions flow directly into core.budget_manager's
    # real IncomeEntry/ExpenseEntry records instead, since the whole
    # point is real transactions driving the SAME reporting (Summary,
    # nudges, Business Report) manual entries already do — a separate
    # read-only transaction list would defeat that.
    # ------------------------------------------------------------------

    def sync(self, passphrase: Optional[str] = None) -> PlaidSyncResult:
        """Fetches current balances for every connected item (unchanged
        behavior) and, for any item with transactions_enabled, also
        imports real transactions via _sync_transactions_for_item().
        passphrase is only needed when at least one item has
        transactions_enabled (its sync cursor needs persisting) —
        balance-only users see no new passphrase prompt at all. Without
        a passphrase, an advanced cursor stays in-memory only for this
        run; safe by construction, since _import_transaction()'s
        plaid_transaction_id dedup means re-fetching the same history
        next time never creates duplicate budget entries, just wastes
        an API round trip."""
        self._require_unlocked()
        written = []
        total_added = 0
        total_updated = 0
        investment_accounts_synced = 0
        debts_added = 0
        debts_updated = 0
        cursor_changed = False

        for item in self._vault.items:
            accounts_response = self._client.accounts_get(AccountsGetRequest(access_token=item.access_token))
            accounts = [self._account_to_dict(a) for a in accounts_response.accounts]
            snapshot_data = {
                "source": f"plaid_{item.item_id}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "institution_name": item.institution_name,
                "accounts": accounts,
                "summary": {"total_value": compute_net_balance_total(accounts)},
            }
            self._write_snapshot_file(snapshot_data)
            written.append(snapshot_data)

            if self.context.budget is not None:
                added, updated = self._sync_loan_accounts(item, accounts)
                debts_added += added
                debts_updated += updated

            if item.investments_enabled:
                holdings_snapshot = self._holdings_snapshot_for_item(item)
                if holdings_snapshot is not None:
                    self._write_snapshot_file(holdings_snapshot)
                    written.append(holdings_snapshot)
                    investment_accounts_synced += 1

            if item.transactions_enabled:
                if self.context.budget is None:
                    log.warning(
                        "Item '%s' has transactions access but context.budget is unavailable — skipping import.",
                        item.institution_name,
                    )
                else:
                    added, updated = self._sync_transactions_for_item(item)
                    total_added += added
                    total_updated += updated
                    cursor_changed = True

            if item.liabilities_enabled and self.context.budget is not None:
                try:
                    added, updated = self._sync_liabilities_for_item(item)
                except plaid.ApiException as exc:
                    # e.g. NO_LIABILITY_ACCOUNTS — one institution's
                    # liabilities error shouldn't abort every other
                    # item's sync.
                    log.warning("Liabilities sync failed for '%s': %s", item.institution_name, exc)
                else:
                    debts_added += added
                    debts_updated += updated

        if written and self.context.finance is not None:
            self.context.finance.scan_for_new_snapshots()

        if cursor_changed:
            if passphrase:
                self._save_vault(self._vault, passphrase)
            else:
                log.warning(
                    "Transaction sync cursor(s) advanced but no passphrase was given — not persisted to disk. "
                    "The next sync will re-fetch from the start of history; the plaid_transaction_id dedup "
                    "prevents duplicate budget entries, but wastes time and API calls."
                )

        return PlaidSyncResult(
            snapshots=written, transactions_added=total_added, transactions_updated=total_updated,
            investment_accounts_synced=investment_accounts_synced,
            debts_added=debts_added, debts_updated=debts_updated,
        )

    def _holdings_snapshot_for_item(self, item: PlaidItem) -> Optional[dict]:
        """Full-snapshot refetch every sync — unlike transactions,
        holdings has no cursor/state to persist, same cost/shape as the
        accounts_get call right above it in sync(). Returns None
        (writes nothing) when is_investments_fallback_item is True
        (Plaid's own signal this item doesn't actually have Investments
        access — e.g. Fidelity Pay-as-you-go without the support-ticket
        grant, see module docstring) or holdings is empty, rather than
        writing an empty snapshot every sync.

        Deliberately does NOT include its own summary.total_value —
        each holding's institution_value is already reflected in that
        same account's balances.current, which sync()'s own
        compute_net_balance_total() already sums above; adding a second
        total here would double-count. holdings_total_value exists only
        for the Bank Sync tab's holdings display."""
        response = self._client.investments_holdings_get(
            InvestmentsHoldingsGetRequest(access_token=item.access_token)
        )
        if response.is_investments_fallback_item or not response.holdings:
            return None

        securities_by_id = {s.security_id: s for s in response.securities}
        holdings = []
        total = 0.0
        for h in response.holdings:
            security = securities_by_id.get(h.security_id)
            holdings.append({
                "account_id": h.account_id,
                "security_name": security.name if security else None,
                "ticker_symbol": security.ticker_symbol if security else None,
                "quantity": h.quantity,
                "institution_price": h.institution_price,
                "institution_value": h.institution_value,
                "iso_currency_code": h.iso_currency_code,
            })
            total += h.institution_value or 0.0

        return {
            "source": f"plaid_investments_{item.item_id}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "institution_name": item.institution_name,
            "holdings": holdings,
            "holdings_total_value": total,
        }

    def _sync_liabilities_for_item(self, item: PlaidItem) -> tuple[int, int]:
        """/liabilities/get -> upserted core.budget_manager.Debt records,
        keyed by plaid_account_id. Only Plaid-owned fields (balance,
        and interest_rate/minimum_payment when reported) are written on
        update — see the module docstring for the full ownership split.
        Returns (added, updated)."""
        response = self._client.liabilities_get(LiabilitiesGetRequest(access_token=item.access_token))
        accounts_by_id = {a.account_id: a for a in response.accounts}
        liabilities = response.liabilities
        budget = self.context.budget
        added = 0
        updated = 0

        for kind in ("credit", "student"):
            for liability in getattr(liabilities, kind, None) or []:
                account = accounts_by_id.get(liability.account_id)
                if account is None:
                    continue
                fields = liability_debt_fields(kind, liability, account, item.institution_name)
                if fields is None:
                    continue
                existing = budget.get_debt_by_plaid_account_id(liability.account_id)
                if existing is not None:
                    changes = {"balance": fields["balance"], "plaid_item_id": item.item_id}
                    if fields["interest_rate"] is not None:
                        changes["interest_rate"] = fields["interest_rate"]
                    if fields["minimum_payment"] is not None:
                        changes["minimum_payment"] = fields["minimum_payment"]
                    budget.update_debt(existing.debt_id, **changes)
                    updated += 1
                else:
                    budget.add_debt(
                        name=fields["name"],
                        balance=fields["balance"],
                        interest_rate=fields["interest_rate"] or 0.0,
                        minimum_payment=fields["minimum_payment"] or 0.0,
                        debt_type=fields["debt_type"],
                        plaid_account_id=liability.account_id,
                        plaid_item_id=item.item_id,
                    )
                    added += 1
        return added, updated

    def _sync_loan_accounts(self, item: PlaidItem, accounts: list[dict]) -> tuple[int, int]:
        """Auto/personal loans and lines of credit -> Debts (see the module
        docstring). Only the balance is Plaid's to update."""
        budget = self.context.budget
        added = updated = 0
        for account in accounts:
            fields = loan_account_debt_fields(account, item.institution_name, item.liabilities_enabled)
            if fields is None:
                continue
            existing = budget.get_debt_by_plaid_account_id(account["account_id"])
            if existing is not None:
                budget.update_debt(existing.debt_id, balance=fields["balance"], plaid_item_id=item.item_id)
                updated += 1
            else:
                budget.add_debt(
                    name=fields["name"], balance=fields["balance"], interest_rate=0.0, minimum_payment=0.0,
                    debt_type=fields["debt_type"], notes=LOAN_RATE_NOTE,
                    plaid_account_id=account["account_id"], plaid_item_id=item.item_id,
                )
                added += 1
        return added, updated

    def _sync_transactions_for_item(self, item: PlaidItem) -> tuple[int, int]:
        """Loops /transactions/sync until has_more is False (Plaid's own
        documented cursor-based pagination), importing every added/
        modified transaction via _import_transaction(), then stores the
        final next_cursor on `item` IN-MEMORY only — sync() above
        decides whether/how to persist it. removed transactions are
        logged, never auto-deleted from the budget (see module
        docstring for why: auto-deleting a household's financial
        records off a bank's own reversal signal doesn't fit this
        project's no-silent-delete discipline elsewhere)."""
        added_count = 0
        updated_count = 0
        # TransactionsSyncRequest.cursor requires a plain str, never None
        # (confirmed against the real SDK model) — "" (the field's own
        # default) means "no cursor yet, start from the beginning".
        cursor = item.transactions_cursor
        while True:
            response = self._client.transactions_sync(TransactionsSyncRequest(
                access_token=item.access_token,
                cursor=cursor,
                options=TransactionsSyncRequestOptions(include_personal_finance_category=True),
            ))
            for txn in list(response.added) + list(response.modified):
                outcome = self._import_transaction(txn)
                if outcome == "added":
                    added_count += 1
                elif outcome == "updated":
                    updated_count += 1
            for removed in response.removed or []:
                log.info(
                    "Plaid reported a removed transaction (%s) on '%s' — not auto-deleted, see module docstring.",
                    removed.transaction_id, item.institution_name,
                )
            cursor = response.next_cursor
            if not response.has_more:
                break
        item.transactions_cursor = cursor
        return added_count, updated_count

    def _import_transaction(self, txn) -> str:
        """One Plaid Transaction -> one budget.add_income()/
        add_expense() call, or an update to an already-imported one.
        Returns "added"/"updated"/"skipped". Dedup key is
        transaction_id (not which Plaid batch — added vs. modified — it
        arrived in), which uniformly handles a genuinely new
        transaction, a real edit to one already imported, and the
        repeat-sync safety-net case the same way."""
        if txn.amount == 0:
            return "skipped"
        is_income = txn.amount < 0

        pfc = txn.personal_finance_category
        primary = pfc.primary if pfc is not None else ""
        detailed = pfc.detailed if pfc is not None else ""
        category = map_plaid_category(primary, detailed, is_income)
        if category is None:
            return "skipped"

        description = txn.merchant_name or txn.name or ""
        txn_date = txn.date.isoformat() if hasattr(txn.date, "isoformat") else str(txn.date)
        amount = abs(txn.amount)
        budget = self.context.budget

        if is_income:
            existing = budget.get_income_by_plaid_transaction_id(txn.transaction_id)
            if existing is not None:
                budget.update_income(existing.entry_id, amount=amount, category=category, description=description, date=txn_date)
                return "updated"
            budget.add_income(amount=amount, category=category, description=description, date=txn_date, plaid_transaction_id=txn.transaction_id)
            return "added"

        existing = budget.get_expense_by_plaid_transaction_id(txn.transaction_id)
        if existing is not None:
            budget.update_expense(existing.entry_id, amount=amount, category=category, description=description, date=txn_date)
            return "updated"
        budget.add_expense(amount=amount, category=category, description=description, date=txn_date, plaid_transaction_id=txn.transaction_id)
        return "added"

    @staticmethod
    def _account_to_dict(account) -> dict:
        return {
            "account_id": account.account_id,
            "name": account.name,
            "official_name": account.official_name,
            "type": str(account.type) if account.type else None,
            "subtype": str(account.subtype) if account.subtype else None,
            "mask": account.mask,
            "balances": account.balances.to_dict() if account.balances else {},
        }

    def _write_snapshot_file(self, snapshot_data: dict) -> None:
        if getattr(self, "private", False):
            # A private budget's bank connection (core/personal_data.py):
            # its balances never go into the household's net worth.
            log.info("Private bank connection: balances snapshot kept out of the household's net worth.")
            return
        import_folder = self.context.finance.import_folder_path
        import_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{snapshot_data['source']}_{uuid.uuid4().hex[:8]}.json"
        atomic_write_text(import_folder / filename, json.dumps(snapshot_data, indent=2))
