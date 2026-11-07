"""
tests.test_power_web
======================

Power on the web and by voice (DEC-0125): the screen's data (the battery,
each energy source's meters with their latest reading), its action kinds,
and logging a reading out loud through the same action.
"""

from datetime import datetime
from types import SimpleNamespace

from core import web_power
from core.actions import ACTION_TYPES
from core.assistant_energy_actions import _action_log_energy_reading, _number

NOW = datetime(2026, 11, 7, 17, 0)


def _reading(value, unit, stamp):
    """One Data Logger reading."""
    return SimpleNamespace(value=value, unit=unit, note="", timestamp=stamp)


class _Energy:
    """A propane tank with two readings, and solar with none."""

    def __init__(self):
        """Two sources."""
        self.sources = [SimpleNamespace(source_id="p1", name="Propane tank", source_type="Propane", notes=""),
                        SimpleNamespace(source_id="s1", name="Solar array", source_type="Solar", notes="")]

    def all_energy_sources(self):
        """Both."""
        return self.sources

    def energy_source_meter_names(self, source_id):
        """Propane has a Level meter."""
        return ["Level"] if source_id == "p1" else []

    def energy_source_readings(self, source_id, meter):
        """An old reading and the latest."""
        return [_reading(70, "%", "2026-10-20T09:00:00"), _reading(62, "%", "2026-11-07T16:05:00")]


def test_the_power_page_shows_each_source_s_latest_reading_with_a_fill_for_percent():
    """The latest reading wins; percent gets a fill; when it was logged in words; no battery on a desktop."""
    context = SimpleNamespace(energy=_Energy(), data_logger=object(), power=None)
    page = web_power.power_page(context, NOW)
    propane, solar = page["sources"]
    assert propane["meters"] == [{"meter": "Level", "value": 62, "unit": "%", "note": "", "percent": 62,
                                  "when": "today, 4 pm", "at": "2026-11-07T16:05:00"}]
    assert solar["meters"] == [] and page["battery"] == {"present": False}
    assert "source" in page["forms"] and page["kinds"][0] == "Solar"


def test_a_reading_says_when_it_was_logged_in_words():
    """Today with the hour, the weekday this week, then weeks."""
    assert web_power._ago("2026-11-05T08:00:00", NOW) == "Thu"
    assert web_power._ago("2026-10-20T08:00:00", NOW) == "2 weeks ago"
    assert web_power._ago("not a date", NOW) == ""


def test_the_power_screen_s_changes_are_actions():
    """Sources added, edited and removed, and a reading logged, all on the action contract (undoable)."""
    assert {"energy_source.add", "energy_source.edit", "energy_source.delete", "energy.reading"} <= set(ACTION_TYPES)


class _Actions:
    """Keeps what was proposed and runs it."""

    def __init__(self):
        """Nothing yet."""
        self.proposed = []

    def propose(self, context, kind, params, proposed_by):
        """Keeps it."""
        self.proposed.append((kind, params))
        return SimpleNamespace(proposal_id="p")

    def approve(self, context, proposal_id):
        """Done."""
        return SimpleNamespace(status="executed", result="Logged Level on Propane tank.")


def test_logging_the_propane_by_voice_goes_through_the_screen_s_action():
    """"Log the propane at 60 percent": the latest meter, the number, % from the words; undoable."""
    actions = _Actions()
    said = _action_log_energy_reading(SimpleNamespace(energy=_Energy(), actions=actions),
                                      {"source": "propane", "value": "60", "unit": "percent"})
    assert actions.proposed == [("energy.reading", {"source_id": "p1", "meter_name": "Level", "value": 60.0, "unit": "%"})]
    assert "undo that" in said


def test_logging_by_voice_asks_which_source_or_what_it_reads_when_unclear():
    """No source named, or no number: nothing is logged."""
    actions = _Actions()
    context = SimpleNamespace(energy=_Energy(), actions=actions)
    assert _action_log_energy_reading(context, {"source": "", "value": "60"}).startswith("Which source?")
    assert _action_log_energy_reading(context, {"source": "solar", "value": "lots"}) == "What does Solar array read?"
    assert not actions.proposed and _number("3.8 kWh") == 3.8
