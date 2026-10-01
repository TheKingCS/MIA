"""
core.personal_data
=====================

Each person's own MIA (2026-10-01, "People and ownership" in
docs/ROADMAP.md): MIA is built for any person or household, so what's
personal belongs to the person, not the device.

**Personal** (each profile's own folder, `data/profiles/<id>/`):
conversations, what MIA remembers about you, the private journal (each
person's own passphrase), notes, your reasons ("remember why") and their
monthly checkpoints, MIA's own message log and breaks
(core/communication_gate.py), and "remind me when we're back online".
Missions and skills were already per person (profile_id on each record).

Workouts, classes and notifications too (2026-10-01): a notification
raised on a person's view is theirs; the desktop shows a toast only for
whoever is signed in and the phone push goes only to that person's
phones.

**Household** (core/household_manager.py): maintenance, kitchen and
groceries, builds, rentals, inventory, chores, the document inbox, the
calendar, the budget and the rest of HOUSEHOLD_STORES are shared only
by the people in one household. The device's first household keeps the
main `data/` folder (the stores built at boot); any other household has
its own folder, `data/households/<id>/`.

How it works:
- Every personal store takes an optional `data_dir`; `stores_for(id)`
  builds (once) that person's set from their folder.
- `view(id)` is that person's AppContext: the shared services plus their
  own stores and their household's. Every Assistant tool already receives a context, so the phone
  server runs a phone user's turn on their view (core/phone_server.py,
  server/app.py), even while someone else is signed in at the desktop.
- `activate(id)` (on "profile.switched") puts the person's stores and
  their household's on the main context, so every screen shows their data.
  Joining or leaving a household ("household.changed") swaps the
  household half.
- **Moving existing data:** the first time, the files that used to be
  shared in `data/` move into the folder of the *first profile ever
  created* (the owner), whoever signs in first; a marker file records
  which files were claimed, so each moves once (files that became
  personal later, like workouts, are claimed then). Nothing is copied to
  anyone else.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.alarm_manager import AlarmManager
from core.budget_manager import BudgetManager
from core.business_use import BusinessUseManager
from core.calendar_manager import CalendarManager
from core.classroom_manager import ClassroomManager
from core.communication_gate import CommunicationGate
from core.component_manager import ComponentManager
from core.conversation_manager import ConversationManager
from core.data_logger_manager import DataLoggerManager
from core.email_drafts import EmailDrafts
from core.energy_manager import EnergyManager
from core.expedition_manager import ExpeditionManager
from core.finance_manager import FinanceManager
from core.homestead_manager import HomesteadManager
from core.inbox_manager import InboxManager
from core.insight_manager import InsightManager
from core.intent_manager import IntentManager
from core.inventory_manager import InventoryManager
from core.job_manager import JobManager
from core.journal_manager import JournalManager
from core.kitchen_manager import KitchenManager
from core.ledger_manager import LedgerManager
from core.lite_capture_manager import LiteCaptureManager
from core.logger import get_logger
from core.maintenance_manager import MaintenanceManager
from core.material_manager import MaterialManager
from core.notification_manager import NotificationManager
from core.online_watch import OnlineReminders
from core.plaid_manager import PlaidManager
from core.private_journal import PrivateJournalManager
from core.product_manager import ProductManager
from core.project_manager import ProjectManager
from core import region
from core.real_estate_manager import RealEstateManager
from core.relationships_manager import RelationshipsManager
from core.script_library_manager import ScriptLibraryManager
from core.task_manager import TaskManager
from core.textbook_manager import TextbookManager
from core.trip_manager import TripManager
from core.user_memory_manager import UserMemoryManager
from core.waypoint_manager import WaypointManager
from core.workout_manager import WorkoutManager

log = get_logger(__name__)

# Where the formerly shared personal files used to live (moved once to
# the owner's folder). tests/conftest.py points this at a temp folder so
# a test run can never move anyone's real files.
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_CLAIM_MARKER = ".shared_data_claimed"


def _profiles_dir() -> Path:
    """The same folder ProfileManager keeps each profile's data in."""
    import core.profile_manager as profile_manager_module

    return profile_manager_module._DATA_PROFILES_DIR

# (AppContext attribute, store class), in construction order.
PERSONAL_STORES: tuple[tuple[str, type], ...] = (
    ("journal", JournalManager),
    ("intents", IntentManager),
    ("conversations", ConversationManager),
    ("user_memories", UserMemoryManager),
    ("private_journal", PrivateJournalManager),
    ("communication", CommunicationGate),
    ("online_reminders", OnlineReminders),
    ("workout", WorkoutManager),
    ("classroom", ClassroomManager),
    ("notifications", NotificationManager),
    ("email_drafts", EmailDrafts),
)

# Shared by the people in one household (core/household_manager.py), in
# the order the app builds them.
HOUSEHOLD_STORES: tuple[tuple[str, type], ...] = (
    ("calendar", CalendarManager),
    ("alarms", AlarmManager),
    ("inventory", InventoryManager),
    ("data_logger", DataLoggerManager),
    ("components", ComponentManager),
    ("materials", MaterialManager),
    ("products", ProductManager),
    ("jobs", JobManager),
    ("ledger", LedgerManager),
    ("waypoints", WaypointManager),
    ("scripts", ScriptLibraryManager),
    ("expeditions", ExpeditionManager),
    ("trips", TripManager),
    ("projects", ProjectManager),
    ("tasks", TaskManager),
    ("business_use", BusinessUseManager),
    ("textbooks", TextbookManager),
    ("inbox", InboxManager),
    ("finance", FinanceManager),
    ("homestead", HomesteadManager),
    ("lite_captures", LiteCaptureManager),
    ("maintenance", MaintenanceManager),
    ("insights", InsightManager),
    ("budget", BudgetManager),
    ("real_estate", RealEstateManager),
    ("energy", EnergyManager),
    ("plaid", PlaidManager),
    ("kitchen", KitchenManager),
    ("relationships", RelationshipsManager),
)

# The files that used to live in the shared data/ folder, moved into the
# owner's folder once each. The first nine moved on 2026-10-01 together
# (an older marker without a "claimed" list means exactly those).
FIRST_LEGACY_FILES = (
    "journal_entries.json", "intents.json", "why_checkpoints.json", "conversations.json", "user_memories.json",
    "private_journal_keys.json", "private_journal.json", "communication_log.json", "online_reminders.json",
)
LEGACY_FILES = FIRST_LEGACY_FILES + (
    "workout_exercises.json", "workout_templates.json", "workout_sessions.json",
    "classroom_subjects.json", "classroom_courses.json", "classroom_lessons.json", "notifications.json",
)

# A person who keeps their money private gets these from their own folder
# instead of the household's (set_private_budget()).
PRIVATE_MONEY_STORES: tuple[tuple[str, type], ...] = (
    ("budget", BudgetManager),
    ("plaid", PlaidManager),
)

PERSONAL_ATTRIBUTES = tuple(attr for attr, _ in PERSONAL_STORES)
HOUSEHOLD_ATTRIBUTES = tuple(attr for attr, _ in HOUSEHOLD_STORES)


class ScopedView:
    """An AppContext with some stores of its own (`own`: the attributes it
    keeps), and everything else read live from the main context (so a
    model, voice or service set up later is seen too). Setting another
    attribute sets it on the main context."""

    def __init__(self, base, own: tuple[str, ...], **ids) -> None:
        object.__setattr__(self, "_base", base)
        object.__setattr__(self, "_own", own)
        object.__setattr__(self, "_stores", {})
        for key, value in ids.items():
            object.__setattr__(self, key, value)

    def __getattr__(self, name):
        stores = object.__getattribute__(self, "_stores")
        if name in stores:
            return stores[name]
        return getattr(object.__getattribute__(self, "_base"), name)

    def __setattr__(self, name, value) -> None:
        if name in self._own:
            self._stores[name] = value
        else:
            setattr(self._base, name, value)


def PersonView(base, profile_id: str) -> ScopedView:
    """One person's AppContext: their own stores and their household's."""
    return ScopedView(base, PERSONAL_ATTRIBUTES + HOUSEHOLD_ATTRIBUTES, profile_id=profile_id)


class PersonalData:
    def __init__(self, context, profiles_dir: Optional[Path] = None, shared_dir: Optional[Path] = None) -> None:
        self.context = context  # the main (desktop) context
        self.profiles_dir = Path(profiles_dir) if profiles_dir is not None else _profiles_dir()
        self.shared_dir = Path(shared_dir) if shared_dir is not None else _DATA_DIR
        self._personal: dict[str, dict] = {}  # profile_id -> their own stores
        self._households: dict[str, dict] = {}  # household_id -> its stores
        self._boot_household: Optional[dict] = None  # the stores built at boot: the first household's
        self._views: dict[str, ScopedView] = {}
        self._private: dict[str, dict] = {}  # profile_id -> their private budget and bank sync
        self.active_profile_id: Optional[str] = None

    # ------------------------------------------------------------------

    def folder(self, profile_id: str) -> Path:
        return self.profiles_dir / profile_id

    def _household_manager(self):
        return getattr(self.context, "households", None)

    def household_stores(self, household_id: Optional[str]) -> dict:
        """The household's shared stores: the ones built at boot for the
        device's first household, built from its own folder for any other.
        Only stores this app has (the Core runtime builds fewer)."""
        if self._boot_household is None:  # before anything is swapped
            self._boot_household = {attr: getattr(self.context, attr, None) for attr in HOUSEHOLD_ATTRIBUTES}
            self._boot_household = {k: v for k, v in self._boot_household.items() if v is not None}
        households = self._household_manager()
        if households is None or not household_id:
            return self._boot_household
        folder = households.folder(household_id)
        if folder is None:
            return self._boot_household
        if household_id not in self._households:
            view = ScopedView(self.context, HOUSEHOLD_ATTRIBUTES, household_id=household_id)
            for attr, store in HOUSEHOLD_STORES:
                if attr in self._boot_household:
                    setattr(view, attr, store(view, data_dir=folder))
            self._households[household_id] = {attr: getattr(view, attr) for attr in self._boot_household}
            log.info("Loaded household %s's shared things.", household_id)
        return self._households[household_id]

    def _personal_stores(self, profile_id: str, view: ScopedView) -> dict:
        if profile_id not in self._personal:
            self._claim_shared_data_if_owner(profile_id)
            folder = self.folder(profile_id)
            for attr, store in PERSONAL_STORES:
                setattr(view, attr, store(view, data_dir=folder))
            self._personal[profile_id] = {attr: view._stores[attr] for attr in PERSONAL_ATTRIBUTES}
            log.info("Loaded personal data for profile %s.", profile_id)
        return self._personal[profile_id]

    def view(self, profile_id: str):
        """That person's AppContext: shared services, their own stores and
        their household's."""
        if profile_id not in self._views:
            view = PersonView(self.context, profile_id)
            households = self._household_manager()
            household_id = households.household_of(profile_id) if households is not None else None
            # Household first: a personal store built next may read it.
            for attr, store in self.household_stores(household_id).items():
                setattr(view, attr, store)
            for attr, store in self._personal_stores(profile_id, view).items():
                setattr(view, attr, store)
            # A private budget (and its bank sync) instead of the household's.
            if self.has_private_budget(profile_id):
                for attr, store in self._private_money(profile_id, view).items():
                    setattr(view, attr, store)
            object.__setattr__(view, "household_id", household_id)
            self._views[profile_id] = view
        return self._views[profile_id]

    # ------------------------------------------------------------------
    # A private budget (2026-10-01): one person's money kept apart from
    # the household's. Budget and bank sync come from the person's own
    # folder; everyone else keeps the shared ones.
    # ------------------------------------------------------------------

    def has_private_budget(self, profile_id: str) -> bool:
        record = (self.context.config.get(f"profiles.{profile_id}") or {}) if getattr(self.context, "config", None) else {}
        return bool((record.get("settings") or {}).get("budget.private"))

    def _private_money(self, profile_id: str, view) -> dict:
        if profile_id not in self._private:
            folder = self.folder(profile_id) / "private_budget"
            stores = {attr: store(view, data_dir=folder) for attr, store in PRIVATE_MONEY_STORES
                      if attr in (self._boot_household or {})}
            if "plaid" in stores:
                stores["plaid"].private = True  # keeps its balances out of the household's net worth
            self._private[profile_id] = stores
            log.info("Loaded a private budget for profile %s.", profile_id)
        return self._private[profile_id]

    def set_private_budget(self, profile_id: str, private: bool) -> None:
        """Turn a person's private budget on or off. Off keeps it saved;
        turning it on again brings it back."""
        record = dict(self.context.config.get(f"profiles.{profile_id}") or {})
        record["settings"] = {**(record.get("settings") or {}), "budget.private": bool(private)}
        self.context.config.set(f"profiles.{profile_id}", record)
        self.context.config.save()
        self._views.pop(profile_id, None)  # rebuilt with the right budget
        if profile_id == self.active_profile_id:
            self.activate(profile_id)
        publish = getattr(self.context.events, "publish", None)
        if publish is not None:
            publish("records.changed", action="budget.private")

    def stores_for(self, profile_id: str) -> dict:
        view = self.view(profile_id)
        return dict(view._stores)

    def activate(self, profile_id: Optional[str]) -> None:
        """Put this person's stores and their household's on the main
        context (every screen)."""
        if not profile_id:
            return
        stores = self.stores_for(profile_id)
        known = self._all_stores()
        for attr, store in stores.items():
            previous = getattr(self.context, attr, None)
            if previous is not None and previous is not store and not any(previous is k for k in known):
                _close(previous)  # a boot-time store for personal data: stop it listening
            setattr(self.context, attr, store)
        self.active_profile_id = profile_id
        region.use_for(self.context)  # money in this person's currency (core/region.py)

    def watch(self, events) -> None:
        """Follow sign-ins: a switch, and a new profile made active
        (the setup wizard creates the first one that way, without a switch),
        and joining or leaving a household."""
        events.subscribe("profile.switched", self._on_switched)
        events.subscribe("profile.created", self._on_created)
        events.subscribe("household.changed", self._on_household_changed)
        events.subscribe("profile.deleted", self._on_deleted)

    def _on_switched(self, profile_id: str = "", **_kwargs) -> None:
        self.activate(profile_id)

    def _on_created(self, profile_id: str = "", **_kwargs) -> None:
        profiles = getattr(self.context, "profiles", None)
        active = profiles.get_active_profile() if profiles is not None else None
        if active is not None and active.profile_id == profile_id:
            self.activate(profile_id)

    def _on_household_changed(self, profile_id: str = "", **_kwargs) -> None:
        self._views.pop(profile_id, None)  # rebuilt with the new household's stores
        if profile_id and profile_id == self.active_profile_id:
            self.activate(profile_id)
            publish = getattr(self.context.events, "publish", None)
            if publish is not None:
                publish("records.changed", action="household.changed")

    def _on_deleted(self, profile_id: str = "", **_kwargs) -> None:
        """A deleted account's stores stop, so nothing writes into its
        archived (or erased) folder again."""
        for store in list(self._personal.pop(profile_id, {}).values()) + list(self._private.pop(profile_id, {}).values()):
            _close(store)
        self._views.pop(profile_id, None)
        if self.active_profile_id == profile_id:
            self.active_profile_id = None

    def activate_current(self) -> None:
        profiles = getattr(self.context, "profiles", None)
        active = profiles.get_active_profile() if profiles is not None else None
        if active is not None:
            self.activate(active.profile_id)

    # ------------------------------------------------------------------
    # Undo (core/undo_log.py): a store re-read from its restored files
    # ------------------------------------------------------------------

    @staticmethod
    def registered_store_types() -> set:
        return {store for _attr, store in PERSONAL_STORES + HOUSEHOLD_STORES}

    def all_known_stores(self) -> list:
        return self._all_stores()

    def replace_store(self, old, new) -> None:
        """Swap a store everywhere it's referenced: the main context, every
        person's view, and the household and personal caches."""
        groups = [self._boot_household or {}] + list(self._personal.values()) + list(self._households.values())
        groups += list(self._private.values())
        groups += [view._stores for view in self._views.values()]
        for group in groups:
            for attr, store in list(group.items()):
                if store is old:
                    group[attr] = new
        for attr, value in list(vars(self.context).items()):
            if value is old:
                setattr(self.context, attr, new)
        _close(old)

    def _all_stores(self) -> list:
        stores = list((self._boot_household or {}).values())
        for group in list(self._personal.values()) + list(self._households.values()) + list(self._private.values()):
            stores.extend(group.values())
        return stores

    # ------------------------------------------------------------------
    # Moving the formerly shared files to the owner, once
    # ------------------------------------------------------------------

    def owner_profile_id(self) -> Optional[str]:
        profiles = getattr(self.context, "profiles", None)
        listed = profiles.list_profiles() if profiles is not None else []
        if not listed:
            return None
        # Stable sort: profiles made in the same second keep the order they
        # were created in (their order in the config).
        return sorted(listed, key=lambda p: p.created_at or "")[0].profile_id

    def _claim_shared_data_if_owner(self, profile_id: str) -> None:
        marker = self.profiles_dir / _CLAIM_MARKER
        record = {}
        if marker.exists():
            try:
                record = json.loads(marker.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                record = {"claimed": list(LEGACY_FILES)}  # unreadable: never risk moving twice
            claimed = set(record.get("claimed", FIRST_LEGACY_FILES))
            owner = record.get("profile_id")
        else:
            claimed, owner = set(), self.owner_profile_id()
        if profile_id != owner or claimed.issuperset(LEGACY_FILES):
            return
        folder = self.folder(profile_id)
        folder.mkdir(parents=True, exist_ok=True)
        moved = []
        for name in LEGACY_FILES:
            if name in claimed:
                continue
            source, target = self.shared_dir / name, folder / name
            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))
                moved.append(name)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"profile_id": profile_id, "claimed": list(LEGACY_FILES),
                                      "moved": list(record.get("moved", [])) + moved,
                                      "at": datetime.now().isoformat(timespec="seconds")}, indent=2), encoding="utf-8")
        if moved:
            log.info("Moved %d formerly shared personal file(s) to the owner's folder: %s", len(moved), ", ".join(moved))


def _close(store) -> None:
    close = getattr(store, "close", None)
    if callable(close):
        try:
            close()
        except Exception:  # never let cleanup break a sign-in
            log.exception("Closing %s failed.", type(store).__name__)


def view_for(context, profile_id: Optional[str]):
    """The context to run a person's turn on: their own view when personal
    data is set up, else the context itself (tests, single-store setups)."""
    personal = getattr(context, "personal_data", None)
    if personal is None or not profile_id:
        return context
    return personal.view(profile_id)
