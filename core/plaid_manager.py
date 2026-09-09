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
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_hosted_link import LinkTokenCreateHostedLink
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.link_token_get_request import LinkTokenGetRequest
from plaid.model.products import Products
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.transactions_sync_request_options import TransactionsSyncRequestOptions

from core.app_context import AppContext
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

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id, "access_token": self.access_token,
            "institution_name": self.institution_name, "connected_at": self.connected_at,
            "transactions_enabled": self.transactions_enabled, "transactions_cursor": self.transactions_cursor,
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
    return "Other"  # MEDICAL, PERSONAL_CARE, GENERAL_MERCHANDISE, BANK_FEES, ENTERTAINMENT, TRAVEL, OTHER, unrecognized


class PlaidManager:
    def __init__(self, context: AppContext) -> None:
        self.context = context
        self._vault: Optional[PlaidVault] = None
        self._client: Optional[plaid_api.PlaidApi] = None

    # ------------------------------------------------------------------
    # Vault setup / unlock
    # ------------------------------------------------------------------

    def is_configured(self) -> bool:
        return _VAULT_FILE.exists()

    def is_unlocked(self) -> bool:
        return self._vault is not None

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
        if not _VAULT_FILE.exists():
            raise SecretsError("No Plaid vault has been set up yet.")
        blob = _VAULT_FILE.read_bytes()
        plaintext = decrypt_bytes(blob, passphrase)
        vault = PlaidVault.from_dict(json.loads(plaintext))
        self._vault = vault
        self._client = self._build_client(vault)
        log.info("Plaid vault unlocked (%d connected item(s)).", len(vault.items))

    def _save_vault(self, vault: PlaidVault, passphrase: str) -> None:
        plaintext = json.dumps(vault.to_dict()).encode("utf-8")
        blob = encrypt_bytes(plaintext, passphrase)
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _VAULT_FILE.write_bytes(blob)

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
            products=[Products("balance"), Products("transactions")],
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

        new_item = PlaidItem(
            item_id=item_id, access_token=access_token, institution_name=institution_name,
            connected_at=datetime.now().isoformat(timespec="seconds"),
            transactions_enabled=True,  # new connections always request both products now (see create_hosted_link_session)
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

    def save_current_vault(self, passphrase: str) -> None:
        """Re-encrypts and persists the in-memory vault (e.g. after
        finish_connection() appended a new item) — a separate explicit
        call rather than auto-saving on every mutation, since the
        passphrase needed to encrypt isn't necessarily still held
        anywhere after unlock() returns (callers keep it only as long
        as they need it, same discipline core.backup_manager takes)."""
        self._require_unlocked()
        self._save_vault(self._vault, passphrase)

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
        cursor_changed = False

        for item in self._vault.items:
            accounts_response = self._client.accounts_get(AccountsGetRequest(access_token=item.access_token))
            snapshot_data = {
                "source": f"plaid_{item.item_id}",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "institution_name": item.institution_name,
                "accounts": [self._account_to_dict(a) for a in accounts_response.accounts],
            }
            self._write_snapshot_file(snapshot_data)
            written.append(snapshot_data)

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

        return PlaidSyncResult(snapshots=written, transactions_added=total_added, transactions_updated=total_updated)

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
        import_folder = self.context.finance.import_folder_path
        import_folder.mkdir(parents=True, exist_ok=True)
        filename = f"{snapshot_data['source']}_{uuid.uuid4().hex[:8]}.json"
        (import_folder / filename).write_text(json.dumps(snapshot_data, indent=2), encoding="utf-8")
