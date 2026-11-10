"""
core.id_wallet
================

The ID wallet (DEC-0129 follow-up, Zac 2026-11-08 00:25: "IDs and passports
securely and safely stored and legally used or pulled up... same with
insurance cards, registrations"). In Security.

- **What's kept:** each card's kind (driver's license, passport, insurance
  card, registration...), a name for it, who issued it, the number, the
  issue and expiry dates, notes, and photos of the front and back.
- **How it's kept:** `id_wallet.json` in the person's own folder, sealed at
  rest (core/at_rest.SEALED, DEC-0126); each photo its own sealed file in
  `id_wallet/` (`seal()` directly: a photo isn't a store file).
- **Numbers are like passwords:** never in an action, a proposal, the undo
  log, a notification or anything the model reads. Adding and editing go
  through their own endpoints (server/app.py `/api/wallet`); only deleting
  is an action (`wallet.delete`, undoable: the photos stay on disk until
  the card is gone for good). Lists show a number masked (`masked`); the
  full number appears only on the card's own Show view.
- **Expiry:** a card shows on Today from RENEW_DAYS before it expires
  (`due`), so there's time to renew; past its date, it's overdue.
- **By voice:** `wants_card` opens a card's Show view for "show my
  driver's license" (core/assistant_turn.py, before the model); `describe`
  answers "when does my passport expire?" with names and dates only.
- **Legally:** a copy is a backup and a quick reference, not the ID itself.
  Where a state issues an official mobile ID or accepts proof of insurance on
  a phone, that's the state's own app or the insurer's card; `LEGAL_NOTE`
  says so on the page.
"""

from __future__ import annotations

import base64
import json
import uuid
from datetime import date
from pathlib import Path
from typing import Optional

from core.atomic_write import atomic_write_text
from core import life_events
from core.logger import get_logger

log = get_logger(__name__)

FILE_NAME = "id_wallet.json"
PHOTO_DIR = "id_wallet"
KINDS = ("Driver's license", "State ID", "Passport", "Passport card", "Health insurance", "Auto insurance",
         "Vehicle registration", "Other")
SIDES = ("front", "back")
PHOTO_TYPES = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
RENEW_DAYS = 60
LEGAL_NOTE = ("A copy here is a backup and a quick reference, not the ID itself. For a legal ID on your phone, use "
              "your state's official mobile ID if it has one; many states accept proof of insurance on a phone.")


def masked(number: str) -> str:
    """Pure logic. A number for lists: its last four characters only ("•••• 4821"); "" when there's none."""
    number = (number or "").strip()
    if not number:
        return ""
    return "•••• " + number[-4:] if len(number) > 4 else "••••"


def expiry_state(expires: str, today: date) -> dict:
    """Pure logic. How close a card is to expiring: {"days": days left or None, "state": "ok" | "soon" | "expired" |
    "none"} (soon from RENEW_DAYS out)."""
    try:
        days = (date.fromisoformat(expires) - today).days
    except (TypeError, ValueError):
        return {"days": None, "state": "none"}
    return {"days": days, "state": "expired" if days < 0 else "soon" if days <= RENEW_DAYS else "ok"}


class IdWallet:
    """The person's cards: their details and numbers in id_wallet.json, their photos sealed beside it."""

    def __init__(self, context=None, data_dir: Optional[Path] = None) -> None:
        """Loads id_wallet.json from the person's folder (or data/); a file that won't open starts empty (at_rest
        keeps a copy aside)."""
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else Path(__file__).resolve().parent.parent / "data"
        self._file = self.data_dir / FILE_NAME
        self._load()

    def _load(self) -> None:
        """Reads the cards (sealed or plain)."""
        from core.at_rest import open_text

        self.cards: list[dict] = []
        if not self._file.exists():
            return
        try:
            data = json.loads(open_text(self._file))
        except (OSError, ValueError):
            log.exception("ID wallet: couldn't read %s; starting empty", self._file)
            return
        if isinstance(data, dict):
            self.cards = list(data.get("cards") or [])

    def _save(self) -> None:
        """Writes the cards atomically (sealed at rest where the PC can)."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"version": 1, "cards": self.cards}, indent=2))

    def get(self, card_id: str) -> Optional[dict]:
        """One card (with its number), or None."""
        return next((c for c in self.cards if c["id"] == card_id), None)

    @staticmethod
    def _clean(fields: dict) -> dict:
        """The editable fields, trimmed and checked (dates as ISO, kind from KINDS)."""
        out = {}
        for key in ("kind", "name", "issued_by", "number", "issued", "expires", "notes"):
            if key in fields and fields[key] is not None:
                value = str(fields[key]).strip()
                if key in ("issued", "expires") and value:
                    date.fromisoformat(value)
                if key == "kind" and value not in KINDS:
                    value = "Other"
                out[key] = value
        return out

    @life_events.on_change("card_added", "a card to the wallet", named=False)
    def add(self, **fields) -> dict:
        """Adds a card; ValueError without a name or with a date that isn't one. The history notes it without its name
        or number (2026-11-09)."""
        clean = self._clean(fields)
        if not clean.get("name"):
            raise ValueError("Give the card a name, like “Texas driver's license”.")
        card = {"id": uuid.uuid4().hex[:10], "kind": "Other", "issued_by": "", "number": "", "issued": "",
                "expires": "", "notes": "", "photos": {}, "added": date.today().isoformat(), **clean}
        self.cards.append(card)
        self._save()
        return card

    def update(self, card_id: str, **fields) -> dict:
        """Changes a card's details; KeyError when it's gone."""
        card = self.get(card_id)
        if card is None:
            raise KeyError("That card isn't in your wallet anymore.")
        card.update(self._clean(fields))
        self._save()
        return card

    @life_events.on_change("card_removed", "a card from the wallet", named=False)
    def remove(self, card_id: str) -> dict:
        """Takes a card out of the wallet (its photo files stay until removed for good, so undo can bring it back);
        the history notes it without its name."""
        card = self.get(card_id)
        if card is None:
            raise KeyError("That card isn't in your wallet anymore.")
        self.cards = [c for c in self.cards if c["id"] != card_id]
        self._save()
        return card

    # ------------------------------------------------------------- photos
    def _photo_path(self, card_id: str, side: str) -> Path:
        """Where a side's photo is kept."""
        return self.data_dir / PHOTO_DIR / f"{card_id}-{side}.photo"

    def set_photo(self, card_id: str, side: str, data: bytes, filename: str) -> None:
        """Keeps a photo of one side, sealed; ValueError for a side or a kind of file that isn't one."""
        from core.at_rest import seal

        card = self.get(card_id)
        if card is None:
            raise KeyError("That card isn't in your wallet anymore.")
        if side not in SIDES:
            raise ValueError("A card has a front and a back.")
        mime = PHOTO_TYPES.get(Path(filename).suffix.lower())
        if mime is None or not data:
            raise ValueError("A photo has to be a JPG, PNG or WebP picture.")
        path = self._photo_path(card_id, side)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"type": mime, "data": base64.b64encode(data).decode("ascii")})
        atomic_write_text(path, seal(payload))
        card.setdefault("photos", {})[side] = True
        self._save()

    def photo(self, card_id: str, side: str) -> Optional[tuple[bytes, str]]:
        """(bytes, mimetype) of one side's photo, or None when there isn't one (or it won't open here)."""
        from core.at_rest import open_text

        card = self.get(card_id)
        if card is None or side not in SIDES or not (card.get("photos") or {}).get(side):
            return None
        path = self._photo_path(card_id, side)
        try:
            payload = json.loads(open_text(path))
            return base64.b64decode(payload["data"]), payload["type"]
        except (OSError, ValueError, KeyError):
            log.exception("ID wallet: couldn't open a photo")
            return None

    # ------------------------------------------------------------- reading
    def listing(self, today: Optional[date] = None) -> list[dict]:
        """The cards for a list: everything but the number, which is masked; with expiry state; soonest to expire
        first, then by name."""
        today = today or date.today()
        rows = []
        for c in self.cards:
            rows.append({**{k: v for k, v in c.items() if k != "number"}, "number": masked(c.get("number", "")),
                         "has_number": bool(c.get("number")), **{"expiry": expiry_state(c.get("expires", ""), today)}})
        order = {"expired": 0, "soon": 1, "ok": 2, "none": 3}
        return sorted(rows, key=lambda r: (order[r["expiry"]["state"]], r["expiry"]["days"] if r["expiry"]["days"]
                                           is not None else 0, r["name"].lower()))

    def due(self, today: Optional[date] = None) -> list[dict]:
        """Cards to renew, for Today: expired, or expiring within RENEW_DAYS. [{id, title, days}] (no numbers)."""
        today = today or date.today()
        out = []
        for c in self.cards:
            state = expiry_state(c.get("expires", ""), today)
            if state["state"] in ("expired", "soon"):
                out.append({"id": c["id"], "days": state["days"],
                            "title": f"{c['name']} {'expired' if state['days'] < 0 else 'expires'}"})
        return sorted(out, key=lambda d: d["days"])


# ---------------------------------------------------------------- by voice: never a number
_SHOW = __import__("re").compile(r"^\s*(?:hey\s+mia[,\s]+)?(?:please\s+)?(?:show(?: me)?|pull up|bring up|open|get)\s+"
                                 r"(?:my|the)\s+(.+?)[\s.!?]*$", __import__("re").I)
_WORDS = {"license": "Driver's license", "licence": "Driver's license", "driver's license": "Driver's license",
          "drivers license": "Driver's license", "id": "State ID", "state id": "State ID", "passport": "Passport",
          "passport card": "Passport card", "insurance card": "Health insurance", "health insurance": "Health insurance",
          "insurance": "Auto insurance", "auto insurance": "Auto insurance", "car insurance": "Auto insurance",
          "proof of insurance": "Auto insurance", "registration": "Vehicle registration",
          "vehicle registration": "Vehicle registration", "truck registration": "Vehicle registration"}


def find_card(cards: list, asked: str) -> Optional[dict]:
    """Pure logic. The card the words mean: one whose name is the words (or holds them), else the only card of the
    kind the words name; None when it's none or more than one."""
    asked = " ".join((asked or "").lower().replace("’", "'").split())
    by_name = [c for c in cards if asked and (c["name"].lower() == asked or asked in c["name"].lower())]
    if len(by_name) == 1:
        return by_name[0]
    kind = _WORDS.get(asked)
    by_kind = [c for c in cards if kind and c.get("kind") == kind]
    return by_kind[0] if len(by_kind) == 1 else None


def wants_card(context, prompt: str) -> Optional[tuple[str, str]]:
    """("wallet.html?show=<id>", its name) when the words ask to see one of the person's cards ("show my driver's
    license", "pull up my insurance card"); None otherwise. The number is never said: the card opens on screen."""
    wallet = getattr(context, "id_wallet", None)
    m = _SHOW.match(prompt or "")
    if wallet is None or not m:
        return None
    card = find_card(wallet.cards, m.group(1))
    return (f"wallet.html?show={card['id']}", card["name"]) if card else None


def describe(context, today: Optional[date] = None) -> str:
    """The wallet in words, for get_wallet: each card's name and when it expires (never a number)."""
    wallet = getattr(context, "id_wallet", None)
    if wallet is None:
        return "The ID wallet isn't on this MIA."
    rows = wallet.listing(today)
    if not rows:
        return "Your wallet is empty. Add your license, passport, insurance cards and registrations in Security, ID Wallet."

    def line(r) -> str:
        """One card: its name and its expiry in words."""
        e = r["expiry"]
        when = ("expired " + str(-e["days"]) + " days ago" if e["state"] == "expired" else
                f"expires {r['expires']}" + (f", in {e['days']} days" if e["state"] == "soon" else "") if r["expires"]
                else "no expiry saved")
        return f"{r['name']} ({when})"
    return "In your wallet: " + "; ".join(line(r) for r in rows) + ". Say \"show my\" and a card to open it."


# ---------------------------------------------------------------- the one action: taking a card out (undoable)
def _wallet(context):
    """The person's wallet; ActionError without one."""
    from core.actions import _need

    return _need(context, "id_wallet")


def _card(context, params) -> dict:
    """The card the params name; ActionError when it's gone."""
    from core.actions import ActionError

    card = _wallet(context).get(str(params.get("card_id") or ""))
    if card is None:
        raise ActionError("That card isn't in your wallet anymore.")
    return card


def _delete(context, params) -> str:
    """Does wallet.delete (the card's name only in what's said; never its number)."""
    card = _card(context, params)
    _wallet(context).remove(card["id"])
    return f"Took {card['name']} out of your wallet."


def _register() -> None:
    """Adds wallet.delete to the action kinds (its only parameter is the card's id: no number goes through an action)."""
    from core.actions import ACTION_TYPES, ActionType

    ACTION_TYPES["wallet.delete"] = ActionType("wallet.delete", "Remove", {"card_id": "the card"},
                                               lambda c, p: f"Take {_card(c, p)['name']} out of your wallet", _delete)


_register()
