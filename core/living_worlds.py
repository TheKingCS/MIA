"""
core.living_worlds
====================

Living Worlds Phase 1 (DEC-0134): the persistent data models for MIA's interactive worlds — **universes**,
**campaigns**, **characters** and their per-universe **versions** — so a campaign survives sessions and context
limits by living in a store, not in a conversation (the spec's §3.3). Phase 1 is the data layer and creation only;
the Dungeon-Master turn loop (the model proposes narrative, this layer commits state), world simulation, the
Convergence and generative artwork are later phases.

The model never writes here — only code does, the same rule the rest of MIA follows (`core/actions.py`,
"model phrases, code decides"). A `CharacterVersion` is one alternate version of the player's central `Character` in a
particular universe; a version's growth in one world never touches another's (the spec's §4.1). Relationships are by
id for now; the cross-world link graph (`core/links.py`) and the Convergence arrive in Phase 4. A campaign can carry
fictional **quests** (DEC-0137) — the same assign-and-track shape as a real Mission, but tagged fictional and XP-free.

One personal store (`living_worlds.json` in the person's own folder), written through `atomic_write_text` (undoable)
and sealed at rest (DEC-0126). Every create records a `life_events` entry — the spec's event log (§11.2).
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import life_events
from core.at_rest import open_text
from core.environment import FICTIONAL
from core.atomic_write import atomic_write_text
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "living_worlds.json"
CAMPAIGN_STATUSES = ("active", "paused", "ended")


def _id() -> str:
    """A short unique id."""
    return uuid.uuid4().hex[:10]


def _now() -> str:
    """Now, to the second, ISO."""
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class Universe:
    """One fictional world: its name, genre, the premise in a sentence, and free-text tone/rules notes (a formal
    ruleset is a later phase)."""

    universe_id: str
    name: str
    genre: str = ""
    premise: str = ""
    rules: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Universe":
        """From a stored dict, tolerant of missing keys."""
        return Universe(**{k: d.get(k, "") for k in Universe.__dataclass_fields__})


@dataclass
class Campaign:
    """One ongoing adventure inside a universe: its name, a running summary, status and when it was last played, so it
    can be paused and resumed."""

    campaign_id: str
    universe_id: str
    name: str
    summary: str = ""
    status: str = "active"
    created_at: str = ""
    last_played: str = ""

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Campaign":
        """From a stored dict; status falls back to 'active'."""
        out = {k: d.get(k, "") for k in Campaign.__dataclass_fields__}
        out["status"] = d.get("status") or "active"
        return Campaign(**out)


@dataclass
class Character:
    """The player's central identity across the multiverse — the self whose alternate versions live in each universe.
    Deliberately thin in Phase 1: the real substance lives on each CharacterVersion."""

    character_id: str
    name: str
    note: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Character":
        """From a stored dict, tolerant of missing keys."""
        return Character(**{k: d.get(k, "") for k in Character.__dataclass_fields__})


@dataclass
class CharacterVersion:
    """One alternate version of the central character, living in a particular universe and campaign: how they're known
    there, their origin and background, and the attributes, skills and inventory that grow through play. A version's
    history is its own — never overwritten by another version's (the spec's §4.1)."""

    version_id: str
    character_id: str
    universe_id: str
    campaign_id: str
    name: str
    origin: str = ""
    background: str = ""
    attributes: dict = field(default_factory=dict)
    skills: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    progression: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "CharacterVersion":
        """From a stored dict; the dict/list fields default to empty copies, never a shared mutable."""
        return CharacterVersion(
            version_id=d.get("version_id", ""), character_id=d.get("character_id", ""),
            universe_id=d.get("universe_id", ""), campaign_id=d.get("campaign_id", ""),
            name=d.get("name", ""), origin=d.get("origin", ""), background=d.get("background", ""),
            attributes=dict(d.get("attributes") or {}), skills=list(d.get("skills") or []),
            inventory=list(d.get("inventory") or []), progression=d.get("progression", ""),
            created_at=d.get("created_at", ""))


@dataclass
class Quest:
    """A fictional objective inside a campaign — the same shape as a real Mission (a name, an objective, a status and
    who set it), but it lives in the campaign and earns no real XP (DEC-0137). `assigned_by`: "dm" (MIA, the Voice of
    the Convergence) or "player"."""

    quest_id: str
    campaign_id: str
    name: str
    objective: str = ""
    status: str = "open"  # open | done
    assigned_by: str = "dm"  # dm | player
    created_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        """As a plain dict for JSON."""
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "Quest":
        """From a stored dict; status falls back to 'open', assigned_by to 'dm'."""
        out = {k: d.get(k, "") for k in Quest.__dataclass_fields__}
        out["status"] = d.get("status") or "open"
        out["assigned_by"] = d.get("assigned_by") or "dm"
        return Quest(**out)


class LivingWorldsBook:
    """A person's Living Worlds (living_worlds.json in their own folder): universes, campaigns, characters and their
    per-universe versions, created and persisted here so a campaign survives any conversation."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Points at the person's living_worlds.json (data/ by default) and loads it."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE if data_dir is not None else _DATA_DIR / _FILE
        self.universes: list[Universe] = []
        self.campaigns: list[Campaign] = []
        self.characters: list[Character] = []
        self.versions: list[CharacterVersion] = []
        self.quests: list[Quest] = []
        self._load()

    def _load(self) -> None:
        """Reads the worlds; a missing file starts empty, and a sealed file that won't open is copied aside and counts
        as damaged (DEC-0126) rather than stopping MIA."""
        try:
            raw = json.loads(open_text(self._file))
        except FileNotFoundError:
            return
        except (ValueError, OSError):
            log.exception("Couldn't read living_worlds.json — starting empty.")
            return
        self.universes = [Universe.from_dict(d) for d in raw.get("universes", [])]
        self.campaigns = [Campaign.from_dict(d) for d in raw.get("campaigns", [])]
        self.characters = [Character.from_dict(d) for d in raw.get("characters", [])]
        self.versions = [CharacterVersion.from_dict(d) for d in raw.get("versions", [])]
        self.quests = [Quest.from_dict(d) for d in raw.get("quests", [])]

    def _save(self) -> None:
        """Writes everything atomically (so undo can restore it), sealed at rest."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({
            "universes": [u.to_dict() for u in self.universes],
            "campaigns": [c.to_dict() for c in self.campaigns],
            "characters": [c.to_dict() for c in self.characters],
            "versions": [v.to_dict() for v in self.versions],
            "quests": [q.to_dict() for q in self.quests],
        }, indent=1, ensure_ascii=False))

    # ------------------------------------------------------------------ create

    def create_universe(self, name: str, genre: str = "", premise: str = "", rules: str = "") -> Universe:
        """A new world."""
        u = Universe(universe_id=_id(), name=name, genre=genre, premise=premise, rules=rules, created_at=_now())
        self.universes.append(u)
        self._save()
        life_events.record(self, "universe_created", name, [f"universe:{u.universe_id}"], environment=FICTIONAL)
        return u

    def create_campaign(self, universe_id: str, name: str, summary: str = "") -> Campaign:
        """A new campaign in a universe (ValueError if the universe isn't one of this person's)."""
        if self.get_universe(universe_id) is None:
            raise ValueError(f"No universe with id '{universe_id}'.")
        c = Campaign(campaign_id=_id(), universe_id=universe_id, name=name, summary=summary,
                     status="active", created_at=_now(), last_played=_now())
        self.campaigns.append(c)
        self._save()
        life_events.record(self, "campaign_created", name, [f"campaign:{c.campaign_id}", f"universe:{universe_id}"], environment=FICTIONAL)
        return c

    def create_character(self, name: str, note: str = "") -> Character:
        """The player's central character."""
        c = Character(character_id=_id(), name=name, note=note, created_at=_now())
        self.characters.append(c)
        self._save()
        life_events.record(self, "character_created", name, [f"character:{c.character_id}"], environment=FICTIONAL)
        return c

    def create_version(self, character_id: str, universe_id: str, campaign_id: str, name: str, origin: str = "",
                       background: str = "", attributes: Optional[dict] = None,
                       skills: Optional[list] = None) -> CharacterVersion:
        """One alternate version of the character in a universe/campaign (ValueError if any of the three isn't this
        person's)."""
        if self.get_character(character_id) is None:
            raise ValueError(f"No character with id '{character_id}'.")
        if self.get_universe(universe_id) is None:
            raise ValueError(f"No universe with id '{universe_id}'.")
        if self.get_campaign(campaign_id) is None:
            raise ValueError(f"No campaign with id '{campaign_id}'.")
        v = CharacterVersion(version_id=_id(), character_id=character_id, universe_id=universe_id,
                             campaign_id=campaign_id, name=name, origin=origin, background=background,
                             attributes=dict(attributes or {}), skills=list(skills or []), created_at=_now())
        self.versions.append(v)
        self._save()
        life_events.record(self, "character_version_created", name,
                           [f"version:{v.version_id}", f"character:{character_id}", f"universe:{universe_id}"], environment=FICTIONAL)
        return v

    def assign_quest(self, campaign_id: str, name: str, objective: str = "", assigned_by: str = "dm") -> Quest:
        """Set a fictional quest in a campaign — the same act as MIA assigning a real mission, but fictional and
        XP-free (ValueError if the campaign isn't this person's)."""
        if self.get_campaign(campaign_id) is None:
            raise ValueError(f"No campaign with id '{campaign_id}'.")
        q = Quest(quest_id=_id(), campaign_id=campaign_id, name=name, objective=objective, status="open",
                  assigned_by=assigned_by, created_at=_now())
        self.quests.append(q)
        self._save()
        life_events.record(self, "quest_assigned", name, [f"quest:{q.quest_id}", f"campaign:{campaign_id}"],
                           environment=FICTIONAL)
        return q

    def complete_quest(self, quest_id: str) -> Quest:
        """Mark a quest done (ValueError for an unknown quest). Records a fictional event; grants no real XP."""
        q = self.get_quest(quest_id)
        if q is None:
            raise ValueError(f"No quest with id '{quest_id}'.")
        q.status = "done"
        q.completed_at = _now()
        self._save()
        life_events.record(self, "quest_completed", q.name, [f"quest:{q.quest_id}", f"campaign:{q.campaign_id}"],
                           environment=FICTIONAL)
        return q

    def get_quest(self, quest_id: str) -> Optional[Quest]:
        """The quest with this id, or None."""
        return next((q for q in self.quests if q.quest_id == quest_id), None)

    def quests_in(self, campaign_id: str) -> list[Quest]:
        """The quests set in one campaign."""
        return [q for q in self.quests if q.campaign_id == campaign_id]

    # ------------------------------------------------------------------ read

    def get_universe(self, universe_id: str) -> Optional[Universe]:
        """The universe with this id, or None."""
        return next((u for u in self.universes if u.universe_id == universe_id), None)

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """The campaign with this id, or None."""
        return next((c for c in self.campaigns if c.campaign_id == campaign_id), None)

    def get_character(self, character_id: str) -> Optional[Character]:
        """The character with this id, or None."""
        return next((c for c in self.characters if c.character_id == character_id), None)

    def get_version(self, version_id: str) -> Optional[CharacterVersion]:
        """The character version with this id, or None."""
        return next((v for v in self.versions if v.version_id == version_id), None)

    def campaigns_in(self, universe_id: str) -> list[Campaign]:
        """The campaigns in a universe."""
        return [c for c in self.campaigns if c.universe_id == universe_id]

    def versions_of(self, character_id: str) -> list[CharacterVersion]:
        """Every alternate version of one character, across universes."""
        return [v for v in self.versions if v.character_id == character_id]

    def versions_in(self, campaign_id: str) -> list[CharacterVersion]:
        """The character versions playing in one campaign."""
        return [v for v in self.versions if v.campaign_id == campaign_id]

    # ------------------------------------------------------------------ update / resume

    def update_version(self, version_id: str, **fields) -> CharacterVersion:
        """Change a version's fields (ValueError for an unknown version or field)."""
        v = self.get_version(version_id)
        if v is None:
            raise ValueError(f"No character version with id '{version_id}'.")
        for key, value in fields.items():
            if not hasattr(v, key):
                raise ValueError(f"CharacterVersion has no field '{key}'.")
            setattr(v, key, value)
        self._save()
        return v

    def set_campaign_status(self, campaign_id: str, status: str) -> Campaign:
        """Pause, resume or end a campaign (ValueError for an unknown status or campaign)."""
        if status not in CAMPAIGN_STATUSES:
            raise ValueError(f"Status is one of {CAMPAIGN_STATUSES}.")
        c = self.get_campaign(campaign_id)
        if c is None:
            raise ValueError(f"No campaign with id '{campaign_id}'.")
        c.status = status
        self._save()
        return c

    def resume(self, campaign_id: str) -> dict:
        """Everything needed to pick a campaign back up: the campaign (marked active, last_played now), its universe,
        and the character versions in it. ValueError for an unknown campaign."""
        c = self.get_campaign(campaign_id)
        if c is None:
            raise ValueError(f"No campaign with id '{campaign_id}'.")
        c.status = "active"
        c.last_played = _now()
        self._save()
        return {
            "campaign": c.to_dict(),
            "universe": (self.get_universe(c.universe_id) or Universe("", "")).to_dict(),
            "versions": [v.to_dict() for v in self.versions_in(campaign_id)],
        }
