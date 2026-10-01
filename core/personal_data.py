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

**Household** (shared `data/`): maintenance, kitchen and groceries,
builds, rentals, inventory, chores, the document inbox, the calendar,
and the budget, for now.

How it works:
- Every personal store takes an optional `data_dir`; `stores_for(id)`
  builds (once) that person's set from their folder.
- `view(id)` is that person's AppContext: the shared services plus their
  stores. Every Assistant tool already receives a context, so the phone
  server runs a phone user's turn on their view (core/phone_server.py,
  server/app.py), even while someone else is signed in at the desktop.
- `activate(id)` (on "profile.switched") puts the person's stores on the
  main context, so every screen shows their data.
- **Moving existing data:** the first time, the files that used to be
  shared in `data/` move into the folder of the *first profile ever
  created* (the owner), whoever signs in first; a marker file records it
  so it happens once. Nothing is copied to anyone else.
"""

from __future__ import annotations

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.communication_gate import CommunicationGate
from core.conversation_manager import ConversationManager
from core.intent_manager import IntentManager
from core.journal_manager import JournalManager
from core.logger import get_logger
from core.online_watch import OnlineReminders
from core.private_journal import PrivateJournalManager
from core.user_memory_manager import UserMemoryManager

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
)

# The files that used to live in the shared data/ folder, moved into the
# owner's folder once.
LEGACY_FILES = (
    "journal_entries.json", "intents.json", "why_checkpoints.json", "conversations.json", "user_memories.json",
    "private_journal_keys.json", "private_journal.json", "communication_log.json", "online_reminders.json",
)

PERSONAL_ATTRIBUTES = tuple(attr for attr, _ in PERSONAL_STORES)


class PersonView:
    """One person's AppContext: their own stores, and everything else read
    live from the main context (so a model, voice or service set up later
    is seen too). Setting a shared attribute sets it on the main context."""

    def __init__(self, base, profile_id: str) -> None:
        object.__setattr__(self, "_base", base)
        object.__setattr__(self, "_stores", {})
        object.__setattr__(self, "profile_id", profile_id)

    def __getattr__(self, name):
        stores = object.__getattribute__(self, "_stores")
        if name in stores:
            return stores[name]
        return getattr(object.__getattribute__(self, "_base"), name)

    def __setattr__(self, name, value) -> None:
        if name in PERSONAL_ATTRIBUTES:
            self._stores[name] = value
        else:
            setattr(self._base, name, value)


class PersonalData:
    def __init__(self, context, profiles_dir: Optional[Path] = None, shared_dir: Optional[Path] = None) -> None:
        self.context = context  # the main (desktop) context
        self.profiles_dir = Path(profiles_dir) if profiles_dir is not None else _profiles_dir()
        self.shared_dir = Path(shared_dir) if shared_dir is not None else _DATA_DIR
        self._views: dict[str, object] = {}
        self.active_profile_id: Optional[str] = None

    # ------------------------------------------------------------------

    def folder(self, profile_id: str) -> Path:
        return self.profiles_dir / profile_id

    def view(self, profile_id: str):
        """That person's AppContext: shared services plus their own stores."""
        if profile_id not in self._views:
            self._claim_shared_data_if_owner(profile_id)
            view = PersonView(self.context, profile_id)
            folder = self.folder(profile_id)
            for attr, store in PERSONAL_STORES:
                setattr(view, attr, store(view, data_dir=folder))
            self._views[profile_id] = view
            log.info("Loaded personal data for profile %s.", profile_id)
        return self._views[profile_id]

    def stores_for(self, profile_id: str) -> dict:
        view = self.view(profile_id)
        return {attr: getattr(view, attr) for attr in PERSONAL_ATTRIBUTES}

    def activate(self, profile_id: Optional[str]) -> None:
        """Put this person's stores on the main context (every screen)."""
        if not profile_id:
            return
        stores = self.stores_for(profile_id)
        for attr, store in stores.items():
            previous = getattr(self.context, attr, None)
            if previous is not None and previous is not store and previous not in self._all_stores():
                _close(previous)  # the boot-time shared-folder store: stop it listening
            setattr(self.context, attr, store)
        self.active_profile_id = profile_id

    def watch(self, events) -> None:
        """Follow sign-ins: a switch, and a new profile made active
        (the setup wizard creates the first one that way, without a switch)."""
        events.subscribe("profile.switched", self._on_switched)
        events.subscribe("profile.created", self._on_created)

    def _on_switched(self, profile_id: str = "", **_kwargs) -> None:
        self.activate(profile_id)

    def _on_created(self, profile_id: str = "", **_kwargs) -> None:
        profiles = getattr(self.context, "profiles", None)
        active = profiles.get_active_profile() if profiles is not None else None
        if active is not None and active.profile_id == profile_id:
            self.activate(profile_id)

    def activate_current(self) -> None:
        profiles = getattr(self.context, "profiles", None)
        active = profiles.get_active_profile() if profiles is not None else None
        if active is not None:
            self.activate(active.profile_id)

    def _all_stores(self) -> list:
        return [getattr(v, attr) for v in self._views.values() for attr in PERSONAL_ATTRIBUTES]

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
        if marker.exists() or profile_id != self.owner_profile_id():
            return
        folder = self.folder(profile_id)
        folder.mkdir(parents=True, exist_ok=True)
        moved = []
        for name in LEGACY_FILES:
            source, target = self.shared_dir / name, folder / name
            if source.exists() and not target.exists():
                shutil.move(str(source), str(target))
                moved.append(name)
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        marker.write_text(json.dumps({"profile_id": profile_id, "moved": moved,
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
