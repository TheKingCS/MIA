"""
tests.test_outdoor_work
=========================

"Is it safe to work outside today?" (core/outdoor_work.py): the NWS heat index and wind chill match the Weather
Service's own tables, a hot day names its level and cooler hours with the heat-stroke signs, a bitter day the minutes
to frostbite, a mild day says so, and the forecast's hours come through core/weather.read.
"""

from core import outdoor_work as ow
from core import weather


def _forecast(temps, rh, wind, iso="2026-07-15", unit="°F"):
    """A forecast whose working day has these hourly figures from 6 am."""
    hours = [{"time": f"{iso}T{6 + i:02d}:00", "temp": t, "rh": rh[i], "wind": wind[i]} for i, t in enumerate(temps)]
    return {"unit": unit, "days": [{"date": iso}], "hours": hours}


def test_the_heat_index_and_wind_chill_match_the_nws_tables():
    """96 °F at 65% is about 121 on the NWS chart; a mild 70 °F stays under 75 (the simple form); 0 °F in a 15 mph
    wind is -19; 60 °F or a still day has no chill."""
    assert round(ow.heat_index(96, 65)) == 121
    assert ow.heat_index(70, 50) < 75
    assert round(ow.wind_chill(0, 15)) == -19
    assert ow.wind_chill(60, 20) is None and ow.wind_chill(20, 2) is None
    assert ow.frostbite_minutes(-20) == 30 and ow.frostbite_minutes(-40) == 10 and ow.frostbite_minutes(0) is None


def test_a_hot_day_names_its_level_the_cool_hours_and_heat_stroke():
    """Hot from 9 am to 6 pm (index 91 to 123): danger at the peak, heavy work before 9 am and after 7 pm, water and
    911."""
    temps = [78, 80, 83, 86, 92, 95, 97, 98, 98, 97, 95, 92, 88, 84, 80]
    said = ow.judge(_forecast(temps, [60] * 15, [5] * 15), "2026-07-15", "911")
    assert "danger" in said and "around 1 pm" in said
    assert "before 9 am and after 7 pm" in said
    assert "every 15 to 20 minutes" in said and "call 911" in said


def test_a_bitter_day_says_the_minutes_to_frostbite_and_a_mild_one_is_fine():
    """-5 °F in 20 mph wind (chill about -29): 30 minutes; 65 °F all day: good to work."""
    cold = ow.judge(_forecast([-5] * 15, [70] * 15, [20] * 15, "2026-01-10"), "2026-01-10")
    assert "wind chill gets down to about -29°F" in cold and "about 30 minutes" in cold
    mild = ow.judge(_forecast([60, 62, 65] + [65] * 12, [50] * 15, [5] * 15), "2026-07-15")
    assert mild.startswith("Good for working outside: 60 to 65°F")


def test_celsius_is_answered_in_celsius():
    """36 °C at 60% (about 115 °F heat index) is said in °C."""
    said = ow.judge(_forecast([36] * 15, [60] * 15, [5] * 15, unit="°C"), "2026-07-15")
    assert "°C" in said and "°F" not in said and "danger" in said


def test_the_forecast_carries_its_hours():
    """Open-Meteo's hourly temperature, humidity and wind come through read(), and the request asks for them."""
    raw = {"current": {"temperature_2m": 80, "weather_code": 0},
           "daily": {"time": ["2026-07-15"], "temperature_2m_max": [98], "temperature_2m_min": [75], "weather_code": [0]},
           "hourly": {"time": ["2026-07-15T13:00"], "temperature_2m": [98], "relative_humidity_2m": [60],
                      "wind_speed_10m": [5]}}
    got = weather.read(raw, "fahrenheit")
    assert got["hours"] == [{"time": "2026-07-15T13:00", "temp": 98, "rh": 60, "wind": 5}]
    assert "relative_humidity_2m" in weather.forecast_url(40.0, -90.0, "fahrenheit")
