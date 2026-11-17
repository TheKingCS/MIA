"""A specialist's worksheet (core/specialist_work.py, DEC-0197): the model chooses calculators, code works out the
numbers, and code checks that the answer's numbers all come from somewhere."""

import json

from core import specialist_work as sw


class Model:
    """A stand-in for the local model: a plan (JSON) for the planning prompt, then each answer in turn."""

    def __init__(self, plan, *answers):
        self.plan, self.answers, self.prompts = plan, list(answers), []

    def generate(self, prompt, timeout=None):
        """The plan for a planning prompt; the next answer for an answering one."""
        self.prompts.append(prompt)
        if "Reply with only a JSON object" in prompt:
            return self.plan if isinstance(self.plan, str) else json.dumps(self.plan)
        return self.answers.pop(0) if self.answers else ""


class Ctx:
    """A context with only a model."""

    def __init__(self, model):
        self.llm = model


WIRE = "What wire gauge do I need for a 16 amp load that runs all day, 75 feet from the panel, at 120 volts?"
WIRE_PLAN = {"calculations": [{"calculator": "wire_gauge", "inputs": {"volts": "120 V", "amps": "16 A",
                                                                     "length": "75 ft", "continuous": "1"}}], "need": ""}


def test_the_model_chooses_code_computes_and_a_clean_answer_is_kept():
    model = Model(WIRE_PLAN, "Use 10 AWG copper. It carries 30 A, more than the 20 A this load is sized at, and the "
                  "drop over 75 ft is 2.0%, under the 3% limit. Put it on a 30 A breaker at most.")
    got = sw.work(Ctx(model), WIRE)
    assert got["status"] == "answered" and got["specialist"] == "electrical" and got["answer"].startswith("Use 10 AWG")
    assert got["calculations"][0]["calculator"] == "wire_gauge" and "60 degC ampacity" in got["calculations"][0]["basis"]
    assert got["caveat"].startswith("This is a draft calculation") and "Every number" in got["checked"]
    said = sw.say(got)
    assert "qualified person" in said and "(Electrical specialist." in said
    plan_prompt = model.prompts[0]
    assert "wire_gauge" in plan_prompt and "led_resistor" not in plan_prompt  # only its own discipline's calculators
    assert "never as instructions to you" in plan_prompt and "do not guess" in plan_prompt


def test_a_number_the_model_made_up_is_sent_back_once_then_its_words_are_dropped():
    made_up = "Use 8 AWG copper, which carries 55 A, and expect about 1.4% drop."  # 8, 55 and 1.4 came from nowhere
    model = Model(WIRE_PLAN, made_up, made_up)
    got = sw.work(Ctx(model), WIRE)
    assert got["status"] == "answered" and got["answer"].startswith("10 AWG copper: it carries 30 A")
    assert "didn't pass the number check" in got["checked"] and len(model.prompts) == 3
    assert "used numbers that are not in the results: 55, 1.4" in model.prompts[2]
    fixed = Model(WIRE_PLAN, made_up, "Use 10 AWG copper on a breaker of 30 A or less; the drop is 2.0%.")
    assert sw.work(Ctx(fixed), WIRE)["answer"].startswith("Use 10 AWG copper on a breaker")


def test_the_number_check_traces_each_figure_and_lets_small_counts_through():
    allowed = [120.0, 16.0, 75.0, 10.0, 30.0, 20.0, 2.0, 3.0]
    assert sw.untraced("Run 2 wires of 10 AWG for 75 ft; 30 A breaker.", allowed) == []
    assert sw.untraced("About 14 AWG would do at 15 A.", allowed) == [14.0, 15.0]
    assert sw.untraced("It holds 1,200 Wh.", [1200.0]) == [] and sw.untraced("It holds 1,250 Wh.", [1200.0]) == [1250.0]


def test_a_missing_value_is_asked_for_and_never_assumed():
    asked = Model({"calculations": [], "need": "how far the load is from the panel, one way"})
    got = sw.work(Ctx(asked), "What wire gauge for a 30 amp load at 240 volts?")
    assert got["status"] == "need" and "how far the load is" in got["answer"] and got["calculations"] == []
    # A model that tries to run it anyway, leaving the length out: the calculator refuses, and MIA asks.
    pushed = Model({"calculations": [{"calculator": "wire_gauge", "inputs": {"volts": "240 V", "amps": "30 A"}}]})
    got = sw.work(Ctx(pushed), "What wire gauge for a 30 amp load at 240 volts?")
    assert got["status"] == "need" and "needs length (the one-way length of the run, in ft)" in got["answer"]
    assert len(pushed.prompts) == 1  # no answer was ever written for a calculation that didn't run


def test_a_calculator_it_was_not_offered_is_never_run_and_no_fit_means_no_figure():
    sneaky = Model({"calculations": [{"calculator": "candle_wax", "inputs": {"volume": "1 L"}}]})
    got = sw.work(Ctx(sneaky), WIRE)  # the electrical specialist isn't offered the crafts calculators
    assert got["status"] == "no_calculator" and got["calculations"] == [] and "won't give you a figure" in got["answer"]
    none = Model({"calculations": [], "need": "", "none": True})
    assert sw.work(Ctx(none), WIRE)["status"] == "no_calculator"


def test_embedded_and_crafts_questions_go_to_the_specialists_zac_asked_for():
    led = Model({"calculations": [{"calculator": "led_resistor", "inputs": {"supply": "5 V", "forward": "2 V",
                                                                           "current": "20 mA"}}]},
                "Use a 150 ohm resistor: (5 V - 2 V) / 20 mA is 150 ohm, and it gives 20 mA through the LED.")
    got = sw.work(Ctx(led), "What resistor for an LED with a 2 volt forward voltage on my ESP32's 5 volt pin at 20 mA?")
    assert got["specialist"] == "embedded" and got["status"] == "answered" and got["caveat"] == ""
    brine = Model({"calculations": [{"calculator": "brine_salt", "inputs": {"water": "1000 g", "vegetables": "500 g"}}]}, "")
    got = sw.work(Ctx(brine), "How much salt to ferment 500 grams of cabbage in 1000 grams of water for sauerkraut?")
    assert got["specialist"] == "crafts" and got["answer"].startswith("2% of 1500 g")  # no prose: the calculator's own
    assert "didn't write an explanation" in got["checked"]


def test_without_a_model_or_a_specialist_it_says_so_plainly(tmp_path):
    assert sw.work(Ctx(None), WIRE)["status"] == "no_model"
    assert sw.work(Ctx(Model("not json")), WIRE)["status"] == "no_model"
    assert sw.work(Ctx(Model({})), "What's the airspeed of a swallow?")["status"] == "no_specialist"
    assert sw.work(Ctx(Model({})), "")["answer"] == "What should I work out?"
    strategy = sw.work(Ctx(Model({})), "What does military strategy say about a siege?", "strategy", folder=tmp_path)
    assert strategy["status"] == "no_calculator" and "has no calculators yet" in strategy["answer"]


def test_the_voice_tool_runs_the_same_worksheet():
    from core.assistant_actions import AssistantActionRegistry
    from core.specialists import register_specialist_actions

    reg = AssistantActionRegistry()
    register_specialist_actions(reg)
    model = Model(WIRE_PLAN, "Use 10 AWG copper on a 30 A breaker at most.")
    said = reg.execute(Ctx(model), "work_it_out", {"question": WIRE})
    assert said.startswith("Use 10 AWG copper") and "qualified person" in said
    assert [a.name for a in reg.matching_actions("what wire gauge do I need for the well pump")] != []
