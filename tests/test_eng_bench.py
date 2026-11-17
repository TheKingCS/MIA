"""The engineering bench (core/eng_bench.py, DEC-0197): each task's answer comes from MIA's own calculator, a reply
is judged right, wrong, guessed, asked or unreadable, and a model is measured alone and with the calculators."""

import json

import pytest

from core import eng_bench as bench
from core.eng_bench import ASKED, BY_TASK, GUESSED, RIGHT, TASKS, UNREADABLE, WRONG


def test_every_task_has_an_answer_code_can_check_or_names_what_is_missing():
    assert len({t.id for t in TASKS}) == len(TASKS) and {t.discipline for t in TASKS} >= {"electrical", "embedded", "crafts"}
    for t in TASKS:
        if t.missing:
            assert t.missing not in t.inputs and bench.expected(t) is None, t.id
            with pytest.raises(Exception, match="needs"):
                bench.calculate(t.calculator, t.inputs)  # the calculator itself refuses without it
        else:
            assert bench.expected(t).to(t.unit) is not None, t.id
    assert sum(1 for t in TASKS if t.missing) >= 4


def _perfect(prompt: str) -> str:
    """A model that always does the right thing, in whichever form it's asked."""
    task = next(t for t in TASKS if t.ask in prompt)
    if "JSON" in prompt:
        return json.dumps({"need": task.missing} if task.missing else {"calculator": task.calculator, "inputs": task.inputs})
    return f"NEED: {task.missing}" if task.missing else f"Working...\nANSWER: {bench.expected(task).to(task.unit)}"


def test_a_model_that_does_everything_right_scores_full_marks_both_ways():
    for mode in bench.MODES:
        rows = bench.run(_perfect, mode)
        assert all(r["verdict"] in (RIGHT, ASKED) for r in rows), [r for r in rows if r["verdict"] not in (RIGHT, ASKED)]
        cells = bench.summary(rows)[mode]
        assert all(c["good"] == 1.0 and c["guessed"] == 0 for c in cells.values())
        assert cells["embedded"]["asked"] == 2 and cells["embedded"]["tasks"] == 8


def test_alone_answers_are_read_with_units_and_judged_within_tolerance():
    e1, e3, e7 = BY_TASK["e1"], BY_TASK["e3"], BY_TASK["e7"]
    assert bench.score(e1, "alone", "P = V x I\nANSWER: 1,500 W")["verdict"] == RIGHT
    assert bench.score(e1, "alone", "ANSWER: 1.5 kW")["verdict"] == RIGHT  # another unit of the same thing
    assert bench.score(e1, "alone", "ANSWER: 1500")["verdict"] == RIGHT  # a bare number is taken in the asked unit
    assert bench.score(e1, "alone", "ANSWER: 1800 W")["verdict"] == WRONG
    assert bench.score(e1, "alone", "ANSWER: 1500 V")["verdict"] == WRONG  # the right number in the wrong unit
    assert bench.score(e1, "alone", "It's fifteen hundred watts.")["verdict"] == UNREADABLE
    assert bench.score(e1, "alone", "NEED: the power factor")["verdict"] == WRONG  # nothing was missing
    assert bench.score(e3, "alone", "ANSWER: 10 AWG")["verdict"] == RIGHT
    assert bench.score(e3, "alone", "ANSWER: 12 AWG")["verdict"] == WRONG  # a gauge is exact, never "close"
    assert bench.score(e7, "alone", "NEED: the length of the run")["verdict"] == ASKED
    assert bench.score(e7, "alone", "ANSWER: 10 AWG")["verdict"] == GUESSED  # the dangerous one


def test_with_tools_the_model_only_chooses_and_code_does_the_sum():
    m1, m8, e2 = BY_TASK["m1"], BY_TASK["m8"], BY_TASK["e2"]
    good = json.dumps({"calculator": "led_resistor", "inputs": {"supply": "5 V", "forward": "2 V", "current": "20 mA"}})
    assert bench.score(m1, "tools", "Here you go:\n" + good)["verdict"] == RIGHT
    wrong_input = json.dumps({"calculator": "led_resistor", "inputs": {"supply": "5 V", "forward": "2 V", "current": "2 mA"}})
    assert bench.score(m1, "tools", wrong_input)["verdict"] == WRONG
    other = json.dumps({"calculator": "voltage_divider", "inputs": {"vin": "5 V", "r1": "2 ohm", "r2": "20 ohm"}})
    got = bench.score(m1, "tools", other)
    assert got["verdict"] == WRONG and "expected the led_resistor calculator" in got["detail"]
    assert bench.score(m1, "tools", "I think about 150 ohms.")["verdict"] == UNREADABLE
    assert bench.score(m8, "tools", '{"need": "the LED\'s forward voltage"}')["verdict"] == ASKED
    invented = json.dumps({"calculator": "led_resistor", "inputs": {"supply": "5 V", "forward": "2 V", "current": "20 mA"}})
    got = bench.score(m8, "tools", invented)  # it made up a forward voltage the question never gave
    assert got["verdict"] == GUESSED and "didn't give forward" in got["detail"]
    assert bench.score(e2, "tools", json.dumps({"calculator": "voltage_drop", "inputs": {
        "volts": "120 V", "amps": "15 A", "length": "100 ft", "gauge": "12"}}))["verdict"] == RIGHT


def test_the_tools_prompt_lists_only_that_disciplines_calculators_and_says_never_guess():
    prompt = bench.prompt_for(BY_TASK["m8"], "tools")
    assert "led_resistor" in prompt and "wire_gauge" not in prompt and "do not guess" in prompt
    assert "forward (the LED's forward voltage, in V, must be given)" in prompt
    assert "ANSWER:" in bench.prompt_for(BY_TASK["m8"], "alone") and "NEED:" in bench.prompt_for(BY_TASK["m8"], "alone")


def test_a_model_that_fails_or_says_nothing_is_unreadable_and_the_run_goes_on():
    calls = []

    def flaky(prompt):
        """Fails on every second question."""
        calls.append(1)
        if len(calls) % 2 == 0:
            raise TimeoutError("no answer")
        return ""
    rows = bench.run(flaky, "alone", tasks=TASKS[:4])
    assert len(rows) == 4 and all(r["verdict"] == UNREADABLE for r in rows) and "TimeoutError" in rows[1]["detail"]
    with pytest.raises(ValueError, match="modes are"):
        bench.run(flaky, "telepathy")


def test_the_command_line_runs_a_model_keeps_the_results_and_prints_a_table(tmp_path, monkeypatch, capsys):
    from tools import eng_bench as tool

    monkeypatch.setattr(tool, "WORK_DIR", tmp_path)
    monkeypatch.setattr(tool, "ollama", lambda model, url=tool.URL, timeout=600.0: _perfect)
    assert tool.main([]) == 1
    assert tool.main(["--model", "test:27b"]) == 0
    kept = json.loads((tmp_path / "eng_bench" / "test_27b.json").read_text(encoding="utf-8"))
    assert kept["model"] == "test:27b" and len(kept["rows"]) == 2 * len(TASKS)
    said = capsys.readouterr().out
    assert "tools  embedded    good 100.0%" in said and "Kept in" in said


def test_a_thinking_models_working_is_left_out_before_its_answer_is_read():
    """qwen3 writes <think>...</think> first; an ANSWER or a brace inside it is working, not the answer."""
    task = BY_TASK["g2"]
    said = '<think>Maybe ANSWER: 99 cfm? {"calculator": "power"} no.</think>\nANSWER: 2304 cfm'
    assert bench.score(task, "alone", said)["verdict"] == RIGHT
    tools = '<think>{"calculator": "power", "inputs": {}}</think>{"calculator": "vent_fan", "inputs": {"floor": "288 ft2"}}'
    assert bench.score(task, "tools", tools)["verdict"] == RIGHT
    assert bench.score(task, "alone", "<think>still working it out, ANSWER: 2304 cfm")["verdict"] == UNREADABLE



def test_only_a_readable_value_for_the_missing_input_counts_as_a_guess():
    """From the first full PC run (2026-11-17): models wrote placeholders ("unknown mAh", "need run length") for the
    missing input, which the calculator refuses as the worksheet would; that's a slip in form, not a guess."""
    task = BY_TASK["m7"]  # capacity is missing
    placeholder = '{"calculator": "battery_life", "inputs": {"capacity": "unknown mAh", "active": "80 mA"}}'
    assert bench.score(task, "tools", placeholder)["verdict"] == UNREADABLE
    invented = '{"calculator": "battery_life", "inputs": {"capacity": "2000 mAh", "active": "80 mA", "sleep": "10 uA", "awake": "2 s", "period": "600 s"}}'
    assert bench.score(task, "tools", invented)["verdict"] == GUESSED
    asked = '{"need": "the battery capacity"}'
    assert bench.score(task, "tools", asked)["verdict"] == ASKED
