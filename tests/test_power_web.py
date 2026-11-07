"""
tests.test_power_web
======================

Power by voice (DEC-0125): a reading said out loud ("log the propane at 60
percent") is logged through the Power screen's own action, `energy.reading`
(core/power_actions.py), so it's undoable. The screen itself is tested in
tests/test_web_power.py.
"""

from types import SimpleNamespace

from core.assistant_energy_actions import _action_log_energy_reading, _number


class _Energy:
    """A propane tank with a Level meter, and solar with none."""

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
        return SimpleNamespace(status="executed", result="Logged 60 % for Propane tank.")


def test_logging_the_propane_by_voice_goes_through_the_screen_s_action():
    """"Log the propane at 60 percent": the latest meter, the number, % from the words; undoable."""
    actions = _Actions()
    said = _action_log_energy_reading(SimpleNamespace(energy=_Energy(), actions=actions),
                                      {"source": "propane", "value": "60", "unit": "percent"})
    assert actions.proposed == [("energy.reading", {"source_id": "p1", "meter": "Level", "value": 60.0, "unit": "%"})]
    assert "undo that" in said


def test_logging_by_voice_asks_which_source_or_what_it_reads_when_unclear():
    """No source named, or no number: nothing is logged."""
    actions = _Actions()
    context = SimpleNamespace(energy=_Energy(), actions=actions)
    assert _action_log_energy_reading(context, {"source": "", "value": "60"}).startswith("Which source?")
    assert _action_log_energy_reading(context, {"source": "solar", "value": "lots"}) == "What does Solar array read?"
    assert not actions.proposed and _number("3.8 kWh") == 3.8


def test_a_reading_said_by_voice_really_logs_through_energy_reading(tmp_path):
    """End to end with the real action: the tool's params are the ones energy.reading takes."""
    from core.actions import ACTION_TYPES

    kind = ACTION_TYPES["energy.reading"]
    logged = []
    store = SimpleNamespace(get_energy_source=lambda sid: _Energy().sources[0] if sid == "p1" else None,
                            log_energy_reading=lambda *a: logged.append(a))
    params = {"source_id": "p1", "meter": "Level", "value": 60.0, "unit": "%"}
    context = SimpleNamespace(energy=store)
    assert "Propane tank" in kind.describe(context, params)
    kind.execute(context, params)
    assert logged == [("p1", "Level", 60.0, "%", "")]
