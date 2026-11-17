"""MIA's engineering calculators and the numbers-with-units under them (core/eng_calcs.py, core/quantities.py;
DEC-0197): each calculator against an example worked by hand, units that don't go together refused, a missing
input named, never guessed, and no input's description offering a value a model could copy."""

import pytest

from core.eng_calcs import AWG, BY_ID, CALCULATORS, CAVEAT, CalcError, calculate, catalogue
from core.quantities import UnitError, parse, q, temperature


def near(got, want, unit, within=0.005):
    """Whether a calculated quantity is within half a percent of a hand-worked value in a unit."""
    return abs(got.number(unit) - want) <= abs(want) * within


def test_units_convert_combine_and_refuse_what_does_not_go_together():
    assert str(q(12, "V") * q(2, "A")) == "24 W" and str(q(12, "V") / q(4, "ohm")) == "3 A"
    assert round((q(10, "ft") + q(2, "m")).value, 2) == 16.56 and (q(10, "ft") + q(2, "m")).unit == "ft"
    assert round(parse("2200 mAh").number("Ah"), 3) == 2.2 and round((q(100, "Ah") * q(12, "V")).number("Wh")) == 1200
    assert parse("1,500 W").value == 1500 and parse("2,5 mm").value == 2.5 and parse("4.7 kΩ").number("ohm") == 4700
    assert round(temperature(77, "degF", "degC"), 2) == 25.0 and round(temperature(0, "degC", "K"), 2) == 273.15
    with pytest.raises(UnitError, match="Can't add m and V"):
        q(1, "m") + q(1, "V")
    with pytest.raises(UnitError, match="different things"):
        q(5, "V").to("A")
    with pytest.raises(UnitError, match="don't know the unit"):
        q(5, "furlongs")
    with pytest.raises(UnitError, match="divide by zero"):
        q(5, "V") / q(0, "ohm")
    with pytest.raises(UnitError, match="can't read"):
        parse("about twelve")


def test_every_calculator_is_described_whole_and_the_safety_ones_carry_the_caveat():
    assert len({c.id for c in CALCULATORS}) == len(CALCULATORS)
    for c in CALCULATORS:
        assert c.label and c.about and c.basis and c.inputs and callable(c.run), c.id
        for name, (unit, what, default) in c.inputs.items():
            assert what and (default is None or parse(default) is not None), (c.id, name)
            q(1, unit)  # every declared unit is one MIA knows
    assert {c["id"] for c in catalogue("embedded")} == {"led_resistor", "voltage_divider", "battery_life",
                                                        "regulator_heat", "adc_step"}
    assert calculate("wire_gauge", {"volts": 120, "amps": 10, "length": 20})["caveat"] == CAVEAT
    assert calculate("led_resistor", {"supply": 5, "forward": 2, "current": 20})["caveat"] == ""
    for kind in ("wire_gauge", "voltage_drop", "circuit_load", "battery_runtime", "regulator_heat", "floor_joist"):
        assert BY_ID[kind].safety, kind


def test_electrical_calculators_match_examples_worked_by_hand():
    assert near(calculate("power", {"volts": "120 V", "amps": 12.5})["values"]["power"], 1500, "W")
    # 12 AWG is 1.588 ohms per 1000 ft; 100 ft out and back is 200 ft = 0.3176 ohm; at 15 A that's 4.764 V.
    drop = calculate("voltage_drop", {"volts": 120, "amps": 15, "length": "100 ft", "gauge": 12})["values"]
    assert near(drop["drop"], 4.764, "V") and near(drop["percent"], 3.97, "") and near(drop["at_load"], 115.236, "V")
    # 16 A all day is sized at 20 A: 12 AWG carries 20 but drops 3.18% over 75 ft; 10 AWG drops 2.0%.
    wire = calculate("wire_gauge", {"volts": 120, "amps": 16, "length": "75 ft", "continuous": 1})
    assert wire["values"]["gauge"].value == 10 and wire["values"]["breaker"].value == 30 and "125%" in wire["said"]
    assert calculate("wire_gauge", {"volts": 120, "amps": 16, "length": "30 ft", "continuous": 1})["values"]["gauge"].value == 12
    assert calculate("wire_gauge", {"volts": 120, "amps": 12, "length": "25 ft"})["values"]["gauge"].value == 14
    # 12 V, 20 A, 30 ft: 6 AWG drops 0.474 V (3.95%); 4 AWG drops 0.298 V (2.49%).
    assert calculate("wire_gauge", {"volts": 12, "amps": 20, "length": "30 ft"})["values"]["gauge"].value == 4
    load = calculate("circuit_load", {"breaker": 20, "volts": 120})["values"]
    assert near(load["continuous_amps"], 16, "A") and near(load["continuous_watts"], 1920, "W")
    # 100 Ah x 12 V = 1200 Wh; x 0.8 x 0.9 = 864 Wh; / 60 W = 14.4 h.
    run = calculate("battery_runtime", {"capacity": "100 Ah", "volts": 12, "load": "60 W"})["values"]
    assert near(run["energy"], 1200, "Wh") and near(run["runtime"], 14.4, "h")
    assert near(calculate("battery_runtime", {"capacity": "100 Ah", "volts": 12, "load": "0.06 kW", "usable": "50 %",
                                              "efficiency": "100 %"})["values"]["runtime"], 10, "h")
    assert all(AWG[a][1] >= AWG[a][2] or a in (14, 12, 10) for a in AWG)  # a breaker never above the wire's rating


def test_embedded_calculators_match_examples_worked_by_hand():
    led = calculate("led_resistor", {"supply": 5, "forward": "2 V", "current": "20 mA"})["values"]
    assert near(led["exact"], 150, "ohm") and led["resistor"].value == 150 and near(led["resistor_power"], 60, "mW")
    led = calculate("led_resistor", {"supply": 3.3, "forward": 2, "current": 5})["values"]  # 260 exact: next up is 270
    assert near(led["exact"], 260, "ohm") and led["resistor"].value == 270 and near(led["current"], 4.815, "mA")
    assert calculate("led_resistor", {"supply": 12, "forward": 3.2, "current": 350})["values"]["resistor"].value == 27
    assert calculate("led_resistor", {"supply": 24, "forward": 2, "current": 2})["values"]["resistor"].value == 12000
    divider = calculate("voltage_divider", {"vin": 5, "r1": "10 kohm", "r2": "20 kohm"})["values"]
    assert near(divider["vout"], 3.3333, "V") and near(divider["current"], 0.16667, "mA")
    # awake 2 s in 600 s at 80 mA: 0.26667 mA; asleep 598/600 at 0.010 mA: 0.00997 mA; together 0.27663 mA.
    life = calculate("battery_life", {"capacity": "2000 mAh", "active": "80 mA", "sleep": "10 uA", "awake": "2 s",
                                      "period": "10 min"})["values"]
    assert near(life["average_current"], 0.27663, "mA") and near(life["life"], 2000 * 0.85 / 0.27663, "h")
    heat = calculate("regulator_heat", {"vin": 12, "vout": 5, "current": "500 mA", "theta": 50})
    assert near(heat["values"]["heat"], 3.5, "W") and heat["values"]["junction"].value == pytest.approx(200)
    assert heat["values"]["within_limit"].value == 0 and "OVER its 125 degC limit" in heat["said"]
    cool = calculate("regulator_heat", {"vin": 9, "vout": 3.3, "current": 300, "theta": 62})  # 1.71 W x 62 = 106 degC rise
    assert cool["values"]["junction"].value == pytest.approx(131.02, abs=0.01) and "OVER" in cool["said"]
    assert calculate("regulator_heat", {"vin": 5, "vout": 3.3, "current": 100, "theta": 62})["values"]["within_limit"].value == 1
    step = calculate("adc_step", {"vref": 3.3, "bits": 12})["values"]
    assert step["steps"].value == 4096 and near(step["step"], 0.80566, "mV")


def test_structural_and_craft_calculators():
    joist = calculate("floor_joist", {"span": "12 ft"})
    assert joist["choice"].startswith("2x") and joist["caveat"] == CAVEAT
    with pytest.raises(CalcError, match="past my joist table"):
        calculate("floor_joist", {"span": "30 ft"})
    assert near(calculate("brine_salt", {"water": "1000 g", "vegetables": "500 g"})["values"]["salt"], 30, "g")
    assert near(calculate("brine_salt", {"water": "2 lb", "vegetables": "1 lb", "strength": "3 %"})["values"]["salt"],
                3 * 453.59237 * 0.03, "g")
    wax = calculate("candle_wax", {"volume": "0.25 L"})["values"]
    assert near(wax["wax"], 215, "g") and near(wax["fragrance"], 17.2, "g")


def test_a_missing_input_is_named_and_nothing_is_guessed_or_taken_in_the_wrong_unit():
    with pytest.raises(CalcError, match=r"needs amps \(the load's current, in A\); length"):
        calculate("wire_gauge", {"volts": 120})
    with pytest.raises(CalcError, match="should be in V"):
        calculate("led_resistor", {"supply": "5 m", "forward": 2, "current": 20})
    with pytest.raises(CalcError, match="doesn't take colour"):
        calculate("led_resistor", {"supply": 5, "forward": 2, "current": 20, "colour": "red"})
    with pytest.raises(CalcError, match="don't have a calculator"):
        calculate("perpetual_motion", {})
    with pytest.raises(CalcError, match="has to be higher than the LED's forward voltage"):
        calculate("led_resistor", {"supply": 1.8, "forward": 2, "current": 20})
    with pytest.raises(CalcError, match="needs a larger conductor than I can size"):
        calculate("wire_gauge", {"volts": 12, "amps": 90, "length": "200 ft"})
    with pytest.raises(CalcError, match="negative"):
        calculate("power", {"volts": -5, "amps": 1})
    with pytest.raises(CalcError, match="don't have 3 AWG"):
        calculate("voltage_drop", {"volts": 120, "amps": 10, "length": 10, "gauge": 3})


def test_the_greenhouse_calculators_match_hand_worked_examples_and_name_what_is_missing():
    """The greenhouse systems specialist's calculators (S4): heat loss 600 x 0.7 x 40 = 16,800 BTU/h; a 12 x 24 floor
    at 8 cfm per square foot is 2,304 cfm; 40 emitters at 0.5 gph for 2 h is 40 gal; 16,800 BTU/h for 10 h at 80%
    is 168,000 / 73,200 = 2.295 gal of propane. Heat loss and the heater carry the caveat."""
    heat = calculate("greenhouse_heat", {"area": "600 ft2", "u": "0.7 BTU/h/ft2/degF", "inside": "45 degF",
                                         "outside": "5 degF"})
    assert near(heat["values"]["heat_loss"], 16_800, "BTU/h") and near(heat["values"]["watts"], 4923.6, "W", 0.01)
    assert heat["caveat"] == CAVEAT
    assert near(calculate("vent_fan", {"floor": "288 sq ft"})["values"]["flow"], 2304, "cfm")
    drip = calculate("drip_irrigation", {"emitters": 40, "rate": "0.5 gph", "hours": "2 h"})
    assert near(drip["values"]["water"], 40, "gal") and near(drip["values"]["gpm"], 20 / 60, "gpm")
    fuel = calculate("heater_fuel", {"load": "16,800 Btu/h", "hours": "10 h"})
    assert near(fuel["values"]["propane"], 168_000 / (91_500 * 0.8), "gal") and fuel["caveat"]
    with pytest.raises(CalcError, match="u"):
        calculate("greenhouse_heat", {"area": "600 ft2", "inside": "45 degF", "outside": "5 degF"})
    with pytest.raises(CalcError, match="warmer"):
        calculate("greenhouse_heat", {"area": "600 ft2", "u": "0.7", "inside": "40 degF", "outside": "50 degF"})
    cold = calculate("greenhouse_heat", {"area": "600 ft2", "u": "0.7", "inside": "45 degF", "outside": "-10 degF"})
    assert near(cold["values"]["heat_loss"], 600 * 0.7 * 55, "BTU/h")  # below zero outside is a winter night
    with pytest.raises(CalcError, match="area can't be negative"):
        calculate("greenhouse_heat", {"area": "-600 ft2", "u": "0.7", "inside": "45 degF", "outside": "5 degF"})
    assert near(calculate("greenhouse_heat", {"area": "55.74 m2", "u": "3.975 W/m2K", "inside": "7.22 degC",
                                              "outside": "-15 degC"})["values"]["heat_loss"], 16_800, "BTU/h", 0.01)


def test_millilitres_and_the_greenhouse_units_are_read_in_every_way_they_are_written():
    """The bench's first run on the PC (2026-11-17) found "mL" unreadable, so a candle answer couldn't be judged."""
    assert parse("250 mL").number("L") == 0.25 and parse("250 ml").number("L") == 0.25
    assert round(parse("2 litres").number("mL")) == 2000
    assert round(parse("12,000 BTU/hr").number("W")) == 3517 and round(parse("1 gpm").number("gph")) == 60
    assert round(parse("100 CFM").number("m3/s"), 5) == 0.04719


def test_no_input_description_offers_a_value_a_model_could_copy_instead_of_asking():
    """On the PC's run two models answered a heat-loss question with no U-value by copying the "about 1.15" the
    description offered; a description says what an input is, never what it might be."""
    import re

    for calc in CALCULATORS:
        for name, (_unit, what, _default) in calc.inputs.items():
            assert not re.search(r"\babout\s+\d", what), (calc.id, name, what)
    assert near(calculate("vent_fan", {"floor": "288 ft2", "rate": "8 cfm/sq ft"})["values"]["flow"], 2304, "cfm")
