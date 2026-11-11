"""
core.weather
==============

The weather on the Dashboard (DEC-0153, Zac 2026-11-11: "yes", she may
fetch it online). MIA had no weather source; this is it.

What it does: the person names their town once (on the Dashboard or by
voice); MIA finds it with Open-Meteo's geocoding and keeps it as their own
setting (`weather.place`: name, latitude, longitude). The Dashboard and the
frame then show the weather there: now, today's high and low, and
tomorrow, from Open-Meteo's forecast (no account, no key), in Fahrenheit
for the US and Celsius elsewhere (core/region.py).

How:
- `place(context)` / `unit_for(context)`: the person's town, and °F or °C.
- `read(raw, unit)` (pure): Open-Meteo's answer as the card's words.
- `find_place(words, fetch)`: a town by name, or None.
- `card(context, fetch)`: what the Dashboard shows. A forecast is kept for
  FRESH_MINUTES; an older one is shown while a new one is fetched on a
  thread of its own (the one network wait this module has), so a page never
  waits on the internet. With no town it says so; offline it keeps the last
  forecast or shows nothing. Nothing goes online from a test run unless the
  test hands in its own `fetch`.
- The action `weather.place` sets the town (undoable: the setting writes
  through atomic_write), from the Dashboard's box and the voice tool.
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.parse
import urllib.request
from typing import Callable, Optional

from core import person_settings
from core.actions import ACTION_TYPES, ActionError, ActionType
from core.logger import get_logger

log = get_logger(__name__)

KEY = "weather.place"
FRESH_MINUTES = 30
AGENT = "MIA-personal-assistant/1.0 (weather on her dashboard)"
GEOCODE = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST = "https://api.open-meteo.com/v1/forecast"
# WMO weather codes as Open-Meteo sends them, in plain words.
CODES = {0: "Clear", 1: "Mostly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Freezing fog",
         51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle", 56: "Freezing drizzle", 57: "Freezing drizzle",
         61: "Light rain", 63: "Rain", 65: "Heavy rain", 66: "Freezing rain", 67: "Freezing rain", 71: "Light snow",
         73: "Snow", 75: "Heavy snow", 77: "Snow grains", 80: "Light showers", 81: "Showers", 82: "Heavy showers",
         85: "Snow showers", 86: "Heavy snow showers", 95: "Thunderstorms", 96: "Thunderstorms with hail",
         99: "Thunderstorms with hail"}
FAHRENHEIT_COUNTRIES = {"US", "LR", "BS", "BZ", "KY", "PW"}

_kept: dict[tuple, dict] = {}  # (lat, lon, unit) -> {"at": monotonic seconds, "card": the read forecast}
_fetching: set[tuple] = set()
_lock = threading.Lock()


def _fetch_json(url: str) -> dict:
    """One Open-Meteo request with MIA's own user agent (10-second timeout, at most 1 MB)."""
    request = urllib.request.Request(url, headers={"User-Agent": AGENT})
    with urllib.request.urlopen(request, timeout=10) as answer:
        return json.loads(answer.read(1_000_000).decode("utf-8"))


def place(context) -> Optional[dict]:
    """The person's town for the weather ({name, lat, lon}), or None until they name one."""
    got = person_settings.get(context, KEY, None) if getattr(context, "config", None) is not None else None
    if isinstance(got, dict) and isinstance(got.get("lat"), (int, float)) and isinstance(got.get("lon"), (int, float)):
        return {"name": str(got.get("name") or ""), "lat": float(got["lat"]), "lon": float(got["lon"])}
    return None


def unit_for(context) -> str:
    """ "fahrenheit" in the countries that use it (the person's country, core/region.py), else "celsius"."""
    try:
        from core.region import country_of

        return "fahrenheit" if country_of(context) in FAHRENHEIT_COUNTRIES else "celsius"
    except Exception:  # noqa: BLE001 - no region to read: the metric default
        return "celsius"


def forecast_url(lat: float, lon: float, unit: str) -> str:
    """Pure logic. The forecast request: now, and today's and tomorrow's high, low and weather."""
    query = {"latitude": f"{lat:.4f}", "longitude": f"{lon:.4f}", "current": "temperature_2m,weather_code",
             "daily": "temperature_2m_max,temperature_2m_min,weather_code", "forecast_days": 2,
             "temperature_unit": unit, "timezone": "auto"}
    return FORECAST + "?" + urllib.parse.urlencode(query)


def read(raw: dict, unit: str) -> Optional[dict]:
    """Pure logic. Open-Meteo's answer as {temp, words, high, low, tomorrow: {high, low, words}, unit: "°F"}, every
    temperature rounded; None when it isn't a forecast."""
    try:
        now, daily = raw["current"], raw["daily"]
        sign = "°F" if unit == "fahrenheit" else "°C"

        def day(i: int) -> dict:
            """One day's high, low and words."""
            return {"high": round(daily["temperature_2m_max"][i]), "low": round(daily["temperature_2m_min"][i]),
                    "words": CODES.get(int(daily["weather_code"][i]), "")}

        today = day(0)
        return {"temp": round(now["temperature_2m"]), "words": CODES.get(int(now["weather_code"]), ""),
                "high": today["high"], "low": today["low"],
                "tomorrow": day(1) if len(daily.get("time") or []) > 1 else None, "unit": sign}
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def find_place(words: str, fetch: Callable[[str], dict] = _fetch_json) -> Optional[dict]:
    """A town by name through Open-Meteo's geocoding: {name ("Springfield, Illinois"), lat, lon}, or None."""
    words = " ".join(str(words or "").split())[:80]
    if not words:
        return None
    raw = fetch(GEOCODE + "?" + urllib.parse.urlencode({"name": words.split(",")[0], "count": 5, "language": "en"}))
    results = raw.get("results") or []
    rest = [w.strip().lower() for w in words.split(",")[1:] if w.strip()]
    if rest:  # "Springfield, Illinois": the one in the state or country they named
        results = [r for r in results if any(w in (str(r.get("admin1", "")) + " " + str(r.get("country", ""))).lower()
                                             for w in rest)] or results
    if not results:
        return None
    r = results[0]
    name = ", ".join(x for x in (r.get("name"), r.get("admin1") or r.get("country")) if x)
    return {"name": name, "lat": float(r["latitude"]), "lon": float(r["longitude"])}


def _refresh(key: tuple, fetch: Callable[[str], dict]) -> None:
    """Fetches and keeps one forecast; a failure leaves the last one in place."""
    try:
        got = read(fetch(forecast_url(key[0], key[1], key[2])), key[2])
        if got is not None:
            with _lock:
                _kept[key] = {"at": time.monotonic(), "card": got}
    except Exception as problem:  # noqa: BLE001 - offline or Open-Meteo down: keep what we had
        log.info("Weather: no forecast this time (%s)", problem)
    finally:
        with _lock:
            _fetching.discard(key)


def card(context, fetch: Optional[Callable[[str], dict]] = None) -> dict:
    """The Dashboard's weather: {status, place, ...the forecast} once there is one; {status: "PLANNED", set: True} with
    no town yet; {status: "REAL", loading: True} the first time, while it's fetched. A forecast older than
    FRESH_MINUTES is shown while a new one comes (fetched on its own thread, never during a test run unless `fetch` is
    given, which runs at once)."""
    where = place(context)
    if where is None:
        return {"status": "PLANNED", "set": True, "text": None}
    key = (round(where["lat"], 3), round(where["lon"], 3), unit_for(context))
    with _lock:
        kept = _kept.get(key)
        stale = kept is None or time.monotonic() - kept["at"] > FRESH_MINUTES * 60
        start = stale and key not in _fetching
        if start:
            _fetching.add(key)
    if start:
        if fetch is not None:
            _refresh(key, fetch)
        elif os.environ.get("PYTEST_CURRENT_TEST"):
            with _lock:
                _fetching.discard(key)  # never online from a test run
        else:
            threading.Thread(target=_refresh, args=(key, _fetch_json), daemon=True, name="mia-weather").start()
        with _lock:
            kept = _kept.get(key)
    if kept is None:
        return {"status": "REAL", "place": where["name"], "loading": True, "text": None}
    c = kept["card"]
    text = f"{c['temp']}{c['unit']}, {c['words'].lower()}" if c["words"] else f"{c['temp']}{c['unit']}"
    return {"status": "REAL", "place": where["name"], "text": text, **c}


def say(context) -> str:
    """The weather in a sentence, for "what's the weather?"."""
    got = card(context)
    if got.get("set"):
        return "I don't know your town yet. Tell me which one, like \"my town is Springfield, Illinois\"."
    if got.get("loading") or not got.get("text"):
        return f"I'm getting the weather for {got.get('place') or 'your town'}; ask me again in a moment."
    line = f"In {got['place']} it's {got['text']}; today {got['high']} and {got['low']}."
    t = got.get("tomorrow")
    return line + (f" Tomorrow: {t['words'].lower()}, {t['high']} and {t['low']}." if t else "")


def _describe(context, params) -> str:
    """The approval sentence for `weather.place`."""
    words = " ".join(str(params.get("place") or "").split())
    if not words:
        raise ActionError("Which town? Its name, and the state or country if there are several.")
    return f"Use {words[:80]} for the weather"


def _do(context, params, fetch: Callable[[str], dict] = _fetch_json) -> str:
    """Does `weather.place`: finds the town online and keeps it as the person's own."""
    _describe(context, params)
    try:
        found = find_place(str(params["place"]), fetch)
    except Exception:  # noqa: BLE001 - offline
        raise ActionError("I couldn't reach the weather service to find that town. Try again when you're online.") from None
    if found is None:
        raise ActionError("I couldn't find a town by that name. Try adding the state or country.")
    person_settings.put(context, KEY, found)
    return f"The weather is for {found['name']} now."


WEATHER_ACTIONS = {a.kind: a for a in (
    ActionType("weather.place", "Use This Town", {"place": "the town's name, with its state or country if needed"},
               _describe, _do),
)}
ACTION_TYPES.update(WEATHER_ACTIONS)
