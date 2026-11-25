"""
tests.test_watchdog_lab
=========================

The ESP32 course's capstone, the greenhouse's safety brain (core/esp32_path.py stage 7, core/esp32_sim.py
`_watchdog`): a watchdog that goes safe on its own after 15 seconds without a heartbeat, refuses a dose while safe or
mid-dose, recovers on a heartbeat, and stays stopped after BOOT whatever comes next; its checks judged from what the
board said, its sketch never blocking, and an LED, never a real pump.
A stop by hand says MIA STOP alone: MIA FALLBACK is the quiet's.
"""

from core import esp32_sim as sim
from core.esp32_lab import READ_FOR, checks_of
from core.esp32_path import LABS, PROGRAM, judge

GOOD_LED = [("GPIO 2", "r1.a"), ("r1.b", "led1.anode"), ("led1.cathode", "GND")]


def _said(result) -> list:
    """The lines the simulated board printed."""
    return [t["line"] for t in result["trace"]]


def test_the_capstone_is_the_last_stage_with_both_checks():
    stage = PROGRAM.stages[-1]
    assert stage.lessons[0].id == "watchdog" and "greenhouse" in stage.name.lower()
    assert {c.id for c in checks_of("watchdog")} == {"esp_fallback", "esp_stop"}
    assert READ_FOR["watchdog"] > 15  # a read long enough for the quiet that makes it go safe


def test_the_sketch_never_blocks_and_starts_the_pump_off():
    code = LABS["watchdog"]["code"]
    loop = code.split("void loop()")[1]
    assert "delay(" not in loop  # a dose done with delay() would stop it hearing the stop button
    assert "digitalWrite(PUMP, LOW);            // start off" in code
    assert "never wire a real pump" in code


def test_quiet_makes_it_go_safe_and_a_heartbeat_brings_it_back():
    """15 seconds without hb: MIA FALLBACK; hb after it: MIA RECOVERED, and a dose runs again."""
    said = _said(sim.simulate("watchdog", GOOD_LED, {"heartbeats": [1, 17], "doses": [17.5]}, 20))
    assert said.index("MIA FALLBACK 1") < said.index("MIA HEARTBEAT 2") < said.index("MIA RECOVERED")
    assert "MIA DOSE 1" in said  # after recovering, a dose runs again


def test_a_dose_is_refused_while_safe_and_while_one_is_running():
    said = _said(sim.simulate("watchdog", GOOD_LED, {"doses": [1, 1.5, 16]}, 20))
    assert said[:4] == ["MIA SAFE_START", "MIA DOSE 1", "MIA REFUSED busy", "MIA DOSED 1"]
    assert "MIA REFUSED safe" in said  # at 16 s it had gone quiet


def test_a_stop_by_hand_is_never_undone_by_a_heartbeat():
    """BOOT: MIA STOP alone (never a FALLBACK, the quiet's), no RECOVERED after it, and the pump left off."""
    result = sim.simulate("watchdog", GOOD_LED, {"heartbeats": [1, 3, 5], "doses": [2.5], "presses": [2.8]}, 8)
    said = _said(result)
    assert "MIA STOP 1" in said and not any(l.startswith("MIA FALLBACK") for l in said)
    assert "MIA RECOVERED" not in said
    pump = [o["led"] for o in result["outputs"] if "led" in o]
    assert pump[-1] == 0.0  # the dose it cut short left the pump off


def test_the_lab_shown_passes_both_checks_and_the_board_text_is_judged():
    """The lab as shown passes both checks in the simulator; MIA FALLBACK passes the quiet's from the board's text."""
    result = sim.simulate("watchdog")
    assert all(c["would_pass"] for c in result["checks"])
    stop, fallback = {c.id: c for c in checks_of("watchdog")}["esp_stop"], \
        {c.id: c for c in checks_of("watchdog")}["esp_fallback"]
    assert judge(fallback, "MIA SAFE_START\nMIA FALLBACK 1\n")[0]
    assert not judge(stop, "MIA SAFE_START\nMIA HEARTBEAT 1\n")[0]


def test_simulate_and_a_why_about_a_named_lab_are_answered_in_code(tmp_path):
    from types import SimpleNamespace

    from core import paths

    asked = []

    class _LLM:
        """Stands in for the model: keeps what it was given."""

        def chat_with_tools(self, messages, tools=None):
            """Answers once, keeping the system text it was handed."""
            asked.append(messages[0]["content"])
            return SimpleNamespace(content="Because the PC asking may be the broken part.")

    added = []
    store = SimpleNamespace(add_message=lambda *a: added.append(a), get_active_conversation_id=lambda: None,
                            start_new_active_conversation=lambda: SimpleNamespace(conversation_id="c1"))
    context = SimpleNamespace(paths=paths.PathBook(None, data_dir=tmp_path), llm=_LLM(), conversations=store)
    empty = SimpleNamespace(messages=[])
    assert sim.reply(context, empty, "Simulate the watchdog lab").startswith("The watchdog lab, wired as built")
    answer = sim.reply(context, empty, "Why does the watchdog lab refuse a dose?")
    assert answer.startswith("Because") and "guards against the PC failing" in asked[0]
    assert added == []  # the voice turn keeps its own conversation
    assert sim.reply(context, empty, "Why did my watchdog lab check fail?") is None
