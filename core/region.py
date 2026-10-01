"""
core.region
=============

Where a person lives (2026-10-01, accounts stage 4): MIA is built for
anyone, so the safety floor's crisis lines and the money symbol follow
the person's country instead of assuming the US.

**Crisis lines** (core/safety_floor.py) are listed only where they're
known well: the US and Canada (988, call or text; 911), the UK and
Ireland (Samaritans 116 123; 999 / 112), Australia (Lifeline 13 11 14;
000) and New Zealand (1737, call or text; 111). Anywhere else MIA gives
the local emergency number advice (112 works from mobiles in much of the
world) and findahelpline.com, rather than a number that might be wrong.
Re-check these when adding a country; a wrong crisis number is worse
than none.

**Money**: `money(amount, spec)` formats with the signed-in person's
currency symbol (set on sign-in, `use_for()`). Everything that used to
write "$" goes through it. US-only features (the IRS mileage rate, US
tax notes) say so where they appear.

The country is each person's own setting (`region.country`,
core/person_settings.py), falling back to the device's
(`region.country` in config) and then the US, which is what MIA assumed
before.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core import person_settings


@dataclass(frozen=True)
class Region:
    code: str
    name: str
    currency: str  # ISO code
    symbol: str
    crisis: str  # spoken sentence: who to call or text
    emergency: str  # the emergency number


REGIONS: dict[str, Region] = {r.code: r for r in (
    Region("US", "United States", "USD", "$",
           "call or text 988, the Suicide and Crisis Lifeline. It's free and open all day and night", "911"),
    Region("CA", "Canada", "CAD", "$",
           "call or text 988, the Suicide Crisis Helpline. It's free and open all day and night", "911"),
    Region("GB", "United Kingdom", "GBP", "£",
           "call Samaritans free on 116 123, any time, day or night", "999"),
    Region("IE", "Ireland", "EUR", "€",
           "call Samaritans free on 116 123, any time, day or night", "112 or 999"),
    Region("AU", "Australia", "AUD", "$",
           "call Lifeline on 13 11 14, any time, day or night", "000"),
    Region("NZ", "New Zealand", "NZD", "$",
           "call or text 1737, free, any time, to talk with a trained counsellor", "111"),
)}

DEFAULT = "US"

# Somewhere without a listed crisis line: honest, general advice.
OTHER = Region("OTHER", "Somewhere else", "", "",
               "reach a crisis line near you; findahelpline.com lists free ones for your country",
               "your local emergency number (112 works from mobile phones in many countries)")

# Currencies to pick from when the country isn't listed (symbol only).
CURRENCIES: dict[str, str] = {
    "USD": "$", "CAD": "$", "AUD": "$", "NZD": "$", "GBP": "£", "EUR": "€", "INR": "₹", "JPY": "¥",
    "MXN": "$", "ZAR": "R", "CHF": "CHF ", "SEK": "kr ", "NOK": "kr ", "DKK": "kr ", "PHP": "₱", "BRL": "R$",
}


def region(code: Optional[str]) -> Region:
    """Pure logic. A listed region, or OTHER."""
    return REGIONS.get((code or "").upper(), OTHER)


def country_of(context) -> str:
    own = person_settings.get(context, "region.country", None) if getattr(context, "config", None) else None
    device = context.config.get("region.country", DEFAULT) if getattr(context, "config", None) else DEFAULT
    return (own or device or DEFAULT).upper()


def region_for(context) -> Region:
    return region(country_of(context))


def currency_symbol_for(context) -> str:
    """The person's chosen currency, else their country's, else "$"."""
    chosen = person_settings.get(context, "region.currency", None) if getattr(context, "config", None) else None
    if chosen and chosen.upper() in CURRENCIES:
        return CURRENCIES[chosen.upper()]
    reg = region_for(context)
    return reg.symbol or "$"


# ------------------------------------------------------------------ money on screen

_symbol = "$"


def use_for(context) -> None:
    """On sign-in: every money amount shows in this person's currency."""
    global _symbol
    _symbol = currency_symbol_for(context)


def symbol() -> str:
    return _symbol


def money(amount, spec: str = ",.2f") -> str:
    """The signed-in person's currency: money(1234.5) -> "$1,234.50"."""
    try:
        return f"{_symbol}{format(amount, spec)}"
    except (TypeError, ValueError):
        return f"{_symbol}{amount}"
