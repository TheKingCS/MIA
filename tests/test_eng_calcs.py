"""MIA's engineering calculators and the numbers-with-units under them (core/eng_calcs.py, core/quantities.py;
DEC-0197): each calculator against an example worked by hand, units that don't go together refused, a missing
input named, never guessed, and no input's description offering a value a model could copy. The hoodie's
calculators (acoustics, audio DSP, textiles, portable power) are checked the same way, with their units, and a
temperature given on another scale is read as a temperature, not a difference. Survival's water-bleach dose follows
the EPA's table (never under its 2-drop minimum, doubled for water still cloudy) and refuses a bleach strength
it isn't for; kitchen volumes (a cup, a quart) are read."""

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
    """The joist, a solar array (30 kWh a day at 4.5 sun hours: 8.9 kW, 23 panels of 400 W; 10 kWh for two days at
    80%: a 25 kWh battery), brine salt, meat cure (a level teaspoon of cure #1 for 5 lb at 156 ppm; nitrite past 200 refused)
    and candle wax against hand-worked examples."""
    joist = calculate("floor_joist", {"span": "12 ft"})
    assert joist["choice"].startswith("2x") and joist["caveat"] == CAVEAT
    with pytest.raises(CalcError, match="past my joist table"):
        calculate("floor_joist", {"span": "30 ft"})
    assert near(calculate("brine_salt", {"water": "1000 g", "vegetables": "500 g"})["values"]["salt"], 30, "g")
    assert near(calculate("brine_salt", {"water": "2 lb", "vegetables": "1 lb", "strength": "3 %"})["values"]["salt"],
                3 * 453.59237 * 0.03, "g")
    solar = calculate("solar_array", {"daily": "30 kWh", "sun": "4.5 h"})
    assert near(solar["values"]["array"], 30 / (4.5 * 0.75) * 1000, "W") and solar["values"]["panels"].si == 23
    assert calculate("solar_array", {"daily": "10 kWh", "days": "2"})["values"]["battery"].number("kWh") == 25
    cure = calculate("meat_cure", {"meat": "5 lb"})
    assert near(cure["values"]["cure"], 5 * 453.59237 * 156 / 1e6 / 0.0625, "g") and cure["caveat"] == CAVEAT
    assert abs(cure["values"]["teaspoons"].si - 1) < 0.01  # a level teaspoon for 5 lb at 156 ppm
    assert near(cure["values"]["salt"], 5 * 453.59237 * 0.025 - cure["values"]["cure"].number("g") * 0.9375, "g")
    with pytest.raises(CalcError, match="between 100 and 200 ppm"):
        calculate("meat_cure", {"meat": "5 lb", "nitrite": "500"})
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


def test_the_structural_and_crafts_calculators_match_hand_worked_examples():
    """108 in of rise is 14 risers of 7.714 in; ten 2x6x8s are 80 board feet; a 10 x 12 slab 4 in thick is 1.481 cu
    yd; 1000 g of olive oil at 5% superfat takes 1000 x 0.135 x 0.95 = 128.25 g of lye; 700 g olive and 300 g coconut
    take (94.5 + 54.9) x 0.95 = 141.93 g; 500 g of wool at 15% takes 75 g of alum."""
    stairs = calculate("stair_risers", {"rise": "108 in"})
    assert stairs["values"]["risers"].value == 14 and near(stairs["values"]["riser"], 108 / 14, "in")
    assert stairs["caveat"] == CAVEAT
    assert calculate("board_feet", {"thickness": "2 in", "width": "6 in", "length": "8 ft", "count": 10})[
        "values"]["board_feet"].value == 80
    slab = calculate("concrete_yards", {"length": "10 ft", "width": "12 ft", "thickness": "4 in", "extra": "0 %"})
    assert near(slab["values"]["concrete"], 40 / 27, "yd3")
    assert calculate("concrete_yards", {"length": "4 ft", "width": "4 ft", "thickness": "4 in"})[
        "values"]["bags_80lb"].value == 10
    lye = calculate("soap_lye", {"olive": "1000 grams"})
    assert near(lye["values"]["lye"], 128.25, "g") and near(lye["values"]["water"], 380, "g") and lye["caveat"]
    assert "never water to lye" in lye["said"]
    assert near(calculate("soap_lye", {"olive": "700 g", "coconut": "300 g"})["values"]["lye"], 141.93, "g")
    assert near(calculate("alum_mordant", {"fibre": "500 g"})["values"]["alum"], 75, "g")
    with pytest.raises(CalcError, match="needs the oils"):
        calculate("soap_lye", {})
    with pytest.raises(CalcError, match="needs fibre"):
        calculate("alum_mordant", {})



def test_the_acoustics_and_audio_calculators_match_hand_worked_examples():
    """The hoodie's specialists (S4's second batch). An 88 dB speaker on 10 W at 4 m: 88 + 10 - 12.04 = 85.96 dB;
    90 dB at 2 m from 85 dB with 3 dB headroom: 10^(14.02 / 10) = 25.24 W; Vas 20 L, Qts 0.35 to Qtc 0.707:
    20 / ((0.707 / 0.35)^2 - 1) = 6.493 L; 3.43 m in 20 degC air (343.42 m/s) is 9.988 ms; 94 dBA is 8 / 2^3 = 1 h a
    day. 256 samples at 48 kHz is 5.333 ms; 48 kHz x 16 bit x 2 is 1,536 kbps and 691.2 MB an hour; 24 bits are
    24 x 6.02 + 1.76 = 146.25 dB; a 1024 point FFT at 48 kHz has 46.875 Hz bins; 10 ms at 48 kHz is 480 samples."""
    assert near(calculate("spl_at_distance", {"sensitivity": "88 dB", "power": "10 W", "distance": "4 m"})
                ["values"]["spl"], 85.959, "dB")
    assert near(calculate("amp_power", {"target": "90 dB", "sensitivity": "85 dB SPL", "distance": "2 m"})
                ["values"]["power"], 25.238, "W")
    assert near(calculate("sealed_box", {"vas": "20 L", "qts": 0.35})["values"]["volume"], 6.4927, "L")
    with pytest.raises(CalcError, match="above its Qts"):
        calculate("sealed_box", {"vas": "20 L", "qts": 0.9})
    assert near(calculate("sound_delay", {"distance": "3.43 m"})["values"]["delay"], 9.9878, "ms")
    exposure = calculate("noise_exposure", {"level": "94 dBA"})
    assert near(exposure["values"]["hours"], 1.0, "h") and "doesn't come back" in exposure["said"]
    assert "full 8 hour day" in calculate("noise_exposure", {"level": "80 dB"})["said"]
    assert near(calculate("buffer_latency", {"buffer": 256, "rate": "48 kHz"})["values"]["latency"], 5.3333, "ms")
    rate = calculate("audio_bitrate", {"rate": "48000 Hz", "bits": 16})["values"]
    assert near(rate["bitrate"], 1536, "kbps") and near(rate["per_hour"], 691.2, "MB")
    assert near(calculate("dynamic_range", {"bits": 24})["values"]["range"], 146.25, "dB")
    assert near(calculate("fft_resolution", {"rate": "48 kHz", "size": 1024})["values"]["bin"], 46.875, "Hz")
    assert calculate("delay_samples", {"delay": "10 ms", "rate": "48 kHz"})["values"]["samples"].value == 480
    assert "fractional" in calculate("delay_samples", {"delay": "1 ms", "rate": "44.1 kHz"})["said"]
    with pytest.raises(CalcError, match="needs buffer"):
        calculate("buffer_latency", {"rate": "48 kHz"})


def test_the_textile_and_portable_power_calculators_match_hand_worked_examples_and_carry_the_caveat():
    """Four 24 x 20 in pieces with 1/2 in seams are cut 25 x 21: two fit across 58 in fabric, two rows, 50 in =
    1.389 yd (and 50 / 0.95 at 5% shrinkage); 1.5 x 2 m of 300 GSM is 900 g, 8.848 oz per sq yd; 36 in after 5%
    shrinkage is cut 37.89 in; 0.5 m of 10 ohm/m thread on 3.7 V is 5 ohm, 0.74 A, 2.738 W. A 2S2P pack of 3.7 V,
    3000 mAh cells is 7.4 V, 6000 mAh, 44.4 Wh; 3000 mAh at 1000 mA and 85% is 3.529 h; 1.5 A from 2000 mAh is
    0.75C; 5 V at 2 A from 3.7 V at 90% draws 3.003 A. Anything electric on the body, and every lithium figure,
    carries the caveat."""
    pieces = {"count": 4, "length": "24 in", "width": "20 in", "fabric": "58 in"}
    yardage = calculate("fabric_yardage", pieces)["values"]
    assert near(yardage["yards"], 50 / 36, "yd") and yardage["across"].value == 2 and yardage["rows"].value == 2
    assert near(calculate("fabric_yardage", {**pieces, "shrink": "5 %"})["values"]["yards"], 50 / 36 / 0.95, "yd")
    with pytest.raises(CalcError, match="fit across"):
        calculate("fabric_yardage", {**pieces, "fabric": "20 in"})
    weight = calculate("fabric_weight", {"gsm": "300 gsm", "length": "1.5 m", "width": "2 m"})["values"]
    assert near(weight["weight"], 900, "g") and near(weight["oz_per_yd2"], 8.848, "oz/yd2")
    assert near(calculate("shrink_allowance", {"finished": "36 in", "shrink": "5 %"})["values"]["cut"], 37.895, "in")
    thread = calculate("conductive_trace", {"resistance": "10 ohm/m", "length": "50 cm", "volts": "3.7 V"})
    assert near(thread["values"]["power"], 2.738, "W") and near(thread["values"]["current"], 0.74, "A")
    assert thread["caveat"] == CAVEAT and not calculate("fabric_weight", {"gsm": 300, "length": 1, "width": 1})["caveat"]
    pack = calculate("battery_pack", {"cell_volts": "3.7 V", "cell_capacity": "3000 mAh", "series": 2,
                                      "parallel": 2})
    assert near(pack["values"]["energy"], 44.4, "Wh") and near(pack["values"]["volts"], 7.4, "V")
    assert pack["caveat"] and "protection board" in pack["said"] and "airlines" not in pack["said"]
    big = calculate("battery_pack", {"cell_volts": "3.6 V", "cell_capacity": "3500 mAh", "series": 4, "parallel": 3})
    assert "100 Wh" in big["said"]  # 151.2 Wh can't go on a plane without approval
    assert near(calculate("charge_time", {"capacity": "3000 mAh", "current": "1 A"})["values"]["hours"], 3.5294, "h")
    assert "fast charge" in calculate("charge_time", {"capacity": "1000 mAh", "current": "2000 mA"})["said"]
    c = calculate("c_rate", {"capacity": "2000 mAh", "load": "1500 mA"})["values"]
    assert c["c_rate"].value == pytest.approx(0.75) and c["within"].value == 1
    assert calculate("c_rate", {"capacity": "2000 mAh", "load": "3 A"})["values"]["within"].value == 0
    assert near(calculate("boost_current", {"vout": "5 V", "iout": "2 A", "vin": "3.7 V"})["values"]
                ["input_current"], 3.003, "A")
    with pytest.raises(CalcError, match="needs current"):
        calculate("charge_time", {"capacity": "3000 mAh"})


def test_a_temperature_on_another_scale_is_read_as_a_temperature_not_a_difference():
    """7 degC into an input in degF is 44.6 degF (a point on the scale), where the arithmetic of a difference would
    make it 12.6; 68 degF of air is 20 degC, so sound covers 3.43 m in the same 9.988 ms; 77 degF around a regulator
    is 25 degC."""
    heat = calculate("greenhouse_heat", {"area": "100 ft2", "u": 1, "inside": "7 degC", "outside": "34.6 degF"})
    assert near(heat["values"]["heat_loss"], 100 * 10, "BTU/h")  # 44.6 - 34.6 = 10 degF
    assert near(calculate("sound_delay", {"distance": "3.43 m", "air": "68 degF"})["values"]["delay"], 9.9878, "ms")
    hot = calculate("regulator_heat", {"vin": "12 V", "vout": "5 V", "current": "100 mA", "theta": "50 degC/W",
                                       "ambient": "77 degF"})
    assert near(hot["values"]["junction"], 25 + 0.7 * 50, "degC")


def test_the_hoodies_units_are_read_in_the_ways_they_are_written():
    """Decibels as dB SPL and dBA, fabric weight as GSM or oz per sq yd, data rates and sizes, resistance per length,
    and metres, yards and kHz spelt out or in lower case."""
    assert parse("88 dB SPL").number("dB") == 88 and parse("94 dBA").unit == "dB"
    assert parse("300 gsm").number("g/m2") == 300 and round(parse("10 oz/sq yd").number("g/m2"), 1) == 339.1
    assert parse("1,536 kbps").number("bps") == 1_536_000 and round(parse("1 MB").number("bit")) == 8_000_000
    assert round(parse("3 ohms/ft").number("ohm/m"), 3) == 9.843 and parse("48 khz").number("Hz") == 48_000
    assert parse("2 metres").number("m") == 2 and round(parse("1.5 yards").number("in"), 6) == 54


def test_water_is_made_safe_with_the_epas_bleach_dose():
    from core.eng_calcs import CALCULATORS, CalcError

    calc = next(c for c in CALCULATORS if c.id == "water_bleach")
    one = calc.run(q(1, "gal"), q(6, "%"))
    assert one["values"]["drops"].value == 8 and "30 minutes" in one["said"]
    assert calc.run(q(1, "gal"), q(8.25, "%"))["values"]["drops"].value == 6  # the EPA's 8.25% row
    five = calc.run(q(5, "gal"), q(6, "%"))
    assert five["values"]["drops"].value == 40 and "teaspoons" in five["said"]
    for bad in (q(1, "%"), q(12, "%")):
        try:
            calc.run(q(1, "gal"), bad)
            raise AssertionError("expected CalcError")
        except CalcError:
            pass
    assert calc.safety


def test_a_small_amount_of_water_never_gets_less_than_the_epas_smallest_dose():
    calc = BY_ID["water_bleach"]
    assert calc.run(q(1, "cup"), q(6, "%"))["values"]["drops"].value == 2  # never 0: untreated water said treated
    assert calc.run(q(1, "qt"), q(8.25, "%"))["values"]["drops"].value == 2  # the EPA's quart row
    assert calc.run(q(500, "mL"), q(8.25, "%"))["values"]["drops"].value == 2
    one = calc.run(q(1, "gal"), q(6, "%"))
    assert one["values"]["cloudy_drops"].value == 16 and "16 drops" in one["said"]
    assert "812 teaspoons" in calc.run(q(10000, "gal"), q(6, "%"))["said"]
