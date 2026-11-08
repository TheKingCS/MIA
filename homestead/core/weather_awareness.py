"""
MIA Homestead — Weather Awareness
v0.1

Everything else in this system reacts to what's happening INSIDE the
tank/cell — nothing looks outside. A frost or heat wave warning, even a
day ahead, is the difference between a proactive fix and a dead crop.

Deliberately opportunistic, same "nice when connected, never required"
posture as SMS delivery and cloud escalation
(docs/OFFLINE_ASSISTANT_PLAN.md's own stated distinction: alerting
inherently needs *some* network path, which is a different category of
dependency than the assistant's core reasoning). The control loop must
never depend on this succeeding — every network/config failure mode
here is a silent, honest skip, never a crash and never a fabricated
forecast.

Two real, physically-grounded signals, not invented thresholds:
1. Frost risk — forecasted low at or below 32F, dangerous to nearly
   everything regardless of species specifics.
2. Species-relative risk — forecasted low/high outside the documented
   temp_air range of whatever's actually currently planted (real
   species_profiles data, same source core/experiment_manager.py and
   core/biofilter_model.py already treat as ground truth).

Uses Open-Meteo (https://open-meteo.com) — free, keyless, no account —
matching this project's established no-vendor-dependency stance (see
core/notifications.py's carrier email-to-SMS gateway for the same
reasoning applied to SMS).
"""

import json
import logging
import sqlite3
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from contracts.capability import Describable
from contracts.mia_homestead_contract import Severity, raise_alert

logger = logging.getLogger("mia_homestead.weather_awareness")

FROST_THRESHOLD_F = 32.0
DEFAULT_CHECK_INTERVAL_HOURS = 6
FORECAST_URL_TEMPLATE = (
    "https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
    "&daily=temperature_2m_max,temperature_2m_min&temperature_unit=fahrenheit"
    "&forecast_days=2&timezone=auto"
)
REQUEST_TIMEOUT_SECONDS = 10


class WeatherAwareness(Describable):
    def __init__(self, db_conn: sqlite3.Connection, config_path: str = "config/location.yaml", notifier=None):
        self.db = db_conn
        self.config_path = config_path
        self.notifier = notifier

    def _load_location(self) -> tuple[float, float] | None:
        path = Path(self.config_path)
        if not path.exists():
            return None
        try:
            raw = yaml.safe_load(path.read_text()) or {}
        except yaml.YAMLError:
            return None
        lat, lon = raw.get("latitude"), raw.get("longitude")
        if lat is None or lon is None:
            return None
        return float(lat), float(lon)

    def _fetch_forecast(self, lat: float, lon: float) -> dict | None:
        url = FORECAST_URL_TEMPLATE.format(lat=lat, lon=lon)
        try:
            with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read())
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            logger.info("Weather check skipped — could not reach Open-Meteo: %s", e)
            return None

    def should_check_now(self, interval_hours: float = DEFAULT_CHECK_INTERVAL_HOURS) -> bool:
        row = self.db.execute("SELECT timestamp FROM weather_checks ORDER BY id DESC LIMIT 1").fetchone()
        if not row:
            return True
        last = datetime.fromisoformat(row[0])
        return (datetime.utcnow() - last).total_seconds() / 3600 >= interval_hours

    def _active_species_temp_range(self) -> tuple[float | None, float | None]:
        """The coldest tolerable min and hottest tolerable max across
        every currently-active planting's real documented species
        range — never invented, and correctly None/None if nothing's
        planted or no active planting has a documented range."""
        rows = self.db.execute(
            "SELECT sp.temp_air_min, sp.temp_air_max FROM bed_plantings bp "
            "JOIN species_profiles sp ON sp.id = bp.species_id "
            "WHERE bp.status = 'active'"
        ).fetchall()
        mins = [r[0] for r in rows if r[0] is not None]
        maxs = [r[1] for r in rows if r[1] is not None]
        return (min(mins) if mins else None, max(maxs) if maxs else None)

    def check_weather(self) -> dict | None:
        """Called periodically (main.py) — honestly returns None (skips
        entirely) if location isn't configured or the API isn't
        reachable, never a fabricated forecast. Logs a real
        weather_checks row every time it DOES get real data, whether or
        not anything concerning was found."""
        location = self._load_location()
        if location is None:
            return None
        forecast = self._fetch_forecast(*location)
        if forecast is None or "daily" not in forecast:
            return None

        daily = forecast["daily"]
        lows = daily.get("temperature_2m_min", [])
        highs = daily.get("temperature_2m_max", [])
        if not lows or not highs:
            return None
        forecast_low, forecast_high = min(lows), max(highs)

        frost_risk = forecast_low <= FROST_THRESHOLD_F
        cold_min, hot_max = self._active_species_temp_range()
        violation = None
        if cold_min is not None and forecast_low < cold_min:
            violation = f"forecast low {forecast_low:.1f}F is below the coldest active planting's documented min ({cold_min:.1f}F)"
        elif hot_max is not None and forecast_high > hot_max:
            violation = f"forecast high {forecast_high:.1f}F is above the most heat-sensitive active planting's documented max ({hot_max:.1f}F)"

        self.db.execute(
            "INSERT INTO weather_checks (forecast_low_f, forecast_high_f, frost_risk, species_range_violation) "
            "VALUES (?, ?, ?, ?)",
            (forecast_low, forecast_high, int(frost_risk), violation),
        )
        self.db.commit()

        if frost_risk:
            raise_alert(
                self.db, "weather_awareness", Severity.WARNING,
                f"Frost risk in the next 2 days — forecasted low {forecast_low:.1f}F "
                f"(at or below the {FROST_THRESHOLD_F:.0f}F frost threshold)",
                self.notifier,
            )
        if violation:
            raise_alert(self.db, "weather_awareness", Severity.WARNING, violation, self.notifier)

        return {
            "forecast_low_f": forecast_low, "forecast_high_f": forecast_high,
            "frost_risk": frost_risk, "species_range_violation": violation,
        }

    def get_last_check(self) -> dict | None:
        self.db.row_factory = sqlite3.Row
        row = self.db.execute("SELECT * FROM weather_checks ORDER BY id DESC LIMIT 1").fetchone()
        return dict(row) if row else None

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="weather_awareness",
            display_name="Weather Awareness",
            purpose=(
                "Checks a real, free weather forecast for frost or heat-wave risk relevant to "
                "what's currently planted — the only thing in this system that looks outside the "
                "tank/cell instead of only reacting to internal sensor data."
            ),
            data_produced=["logged forecast checks: low/high temp, frost risk, species-range violations"],
            actions_possible=["check the weather forecast for frost/heat risk", "get the last weather check performed"],
            limits_and_safety=(
                "Deliberately opportunistic — the control loop never depends on this succeeding. "
                "Honestly skips (returns None, no fabricated forecast, no alert) if "
                "config/location.yaml has no coordinates set, or Open-Meteo isn't reachable. Uses "
                "a free, keyless weather API (Open-Meteo) — no account, no vendor dependency, "
                "same stance as core/notifications.py's carrier email-to-SMS gateway. Frost "
                "threshold (32F) is a real physical fact, not invented; species-range comparisons "
                "use only real, currently-active plantings' documented temp_air ranges, never a "
                "guessed range."
            ),
            example_questions=["Is there a frost risk coming up?", "When was the weather last checked?"],
            verification_evidence=[
                "Live test 2026-08-31: confirmed a real call to Open-Meteo's public forecast API "
                "(no key) returns real current data for a real coordinate pair.",
                "scenarios.py::scenario_weather_awareness — confirmed check_weather() honestly "
                "returns None with no config/location.yaml coordinates set (no fabricated "
                "forecast, no alert); confirmed a real forecast with a low at/below 32F raises a "
                "real frost-risk WARNING; confirmed a forecast within every active planting's "
                "documented temp_air range raises nothing; confirmed a forecast outside the "
                "coldest active planting's real documented range raises a real, correctly-worded "
                "species-range-violation WARNING citing the actual numbers.",
            ],
        )

    def describe_hardware_requirements(self) -> list:
        return []  # pure software + an optional internet connection, no hardware of its own
