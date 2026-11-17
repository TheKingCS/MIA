"""
core.eng_calcs
================

MIA's engineering calculators (the local specialists plan, S2 first part;
DEC-0197): where a specialist's numbers come from.

Why: Zac wants specialists that do real engineering on local models. A
local model can choose the right calculation and its inputs; it can't be
trusted to do the arithmetic or remember a table. So every number a
specialist gives comes from here, the way material lists come from
`core/build_calcs.py` (DEC-0118). The model never works one out.

What it is: `CALCULATORS`, each described once (`Calculator`): its
discipline, what it works out, its inputs with their units, the rule or
table it follows (`basis`), and whether its result is safety-critical
(`safety`: then it carries the caveat that a qualified person must check
it, DEC-0198 Q-57). `calculate(id, inputs)` reads the inputs with units
(core/quantities.py), refuses a missing one by name, runs it, and returns
the values, a sentence, the basis and the caveat.

The first set: electrical (power, voltage drop, wire gauge, circuit load,
battery runtime), embedded (LED resistor, voltage divider, battery life
with sleep, regulator heat, ADC step), structural (floor joist), and
structural (stair risers, board feet, concrete), homestead crafts (brine salt, candle wax, soap
lye, alum mordant), and the greenhouse (heat loss, fan size, drip water, heater propane; S4's first specialist).
S4's second batch, the hoodie's: acoustics (SPL at distance, amplifier power, sealed box, sound delay, safe
listening time), audio DSP (buffer latency, data rate, dynamic range, FFT resolution, delay in samples), textiles
(yardage, fabric weight, shrinkage, conductive thread) and portable power (battery pack, charge time, C-rate,
converter input current). Each is checked in tests/test_eng_calcs.py against a worked example done by hand.

Tables here are for copper wire at ordinary indoor temperatures and are a
starting point, never a substitute for the code where the person lives.

Pure logic: no I/O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable

from core.quantities import Quantity, UnitError, parse, q, unit_of

CAVEAT = ("This is a draft calculation. Electrical, battery, structural and chemical work (lye, fuel) must be "
          "checked by a qualified person and against the code where you live before anything is built, energised "
          "or mixed.")

# Copper wire by AWG: (ohms per 1000 ft at 20 degC, ampacity at the 60 degC column, the largest breaker allowed).
# The 60 degC column is the conservative one for ordinary cable; 14, 12 and 10 AWG are capped at 15, 20 and 30 A.
AWG = {14: (2.525, 15, 15), 12: (1.588, 20, 20), 10: (0.9989, 30, 30), 8: (0.6282, 40, 40), 6: (0.3951, 55, 50),
       4: (0.2485, 70, 70), 2: (0.1563, 95, 90)}
SMALL_AWG = {24: 25.67, 22: 16.14, 20: 10.15, 18: 6.385, 16: 4.016}  # ohms per 1000 ft, for low-voltage runs
E12 = (10, 12, 15, 18, 22, 27, 33, 39, 47, 56, 68, 82)  # standard resistor values per decade


class CalcError(ValueError):
    """A calculation that can't be done as asked; its message is a plain sentence (what's missing, or why)."""


@dataclass(frozen=True)
class Calculator:
    """One calculator: its id, discipline, name, what it works out, its inputs (name -> (unit, what it is, the
    default as text or None when it must be given)), what it runs, the rule or table it follows, and whether the
    result is safety-critical, and which inputs may be negative (`signed`)."""
    id: str
    discipline: str
    label: str
    about: str
    inputs: dict
    run: Callable[..., dict] = field(repr=False, compare=False, default=None)
    basis: str = ""
    safety: bool = False
    signed: tuple = ()  # inputs that may be below zero (a temperature on a scale); every other input may not


def _ohms_per_ft(awg: int) -> float:
    """Copper's resistance per foot for a gauge in the tables. CalcError for one that isn't."""
    if awg in AWG:
        return AWG[awg][0] / 1000
    if awg in SMALL_AWG:
        return SMALL_AWG[awg] / 1000
    raise CalcError(f"I don't have {awg} AWG in my table (I have {', '.join(str(a) for a in sorted({**AWG, **SMALL_AWG}))}).")


def _gauge(value: Quantity) -> int:
    """The AWG number from a plain-number input."""
    return int(round(value.value))


def _power(volts: Quantity, amps: Quantity) -> dict:
    """Power from voltage and current."""
    watts = (volts * amps).to("W")
    return {"values": {"power": watts}, "said": f"{volts} at {amps} is {watts}."}


def _voltage_drop(volts: Quantity, amps: Quantity, length: Quantity, gauge: Quantity) -> dict:
    """The drop over a two-wire copper run: out and back, so twice the one-way length."""
    awg = _gauge(gauge)
    ohms = q(2 * length.number("ft") * _ohms_per_ft(awg), "ohm")
    drop = (amps * ohms).to("V")
    percent = q(100 * drop.si / volts.si, "")
    return {"values": {"drop": drop, "percent": percent, "at_load": (volts - drop).to("V")},
            "said": f"{awg} AWG copper, {length} one way at {amps}: a drop of {drop} ({percent.value:.1f}% of {volts}), "
                    f"leaving {(volts - drop).to('V')} at the load."}


def _wire_gauge(volts: Quantity, amps: Quantity, length: Quantity, max_drop: Quantity, continuous: Quantity) -> dict:
    """The smallest copper gauge that carries the current and keeps the drop within the limit."""
    need = amps.number("A") * (1.25 if continuous.value else 1.0)  # a continuous load is sized at 125%
    limit = max_drop.si * 100 if max_drop.unit == "%" else max_drop.value
    for awg in sorted(AWG, reverse=True):
        _ohms, ampacity, breaker = AWG[awg]
        if ampacity < need:
            continue
        drop = _voltage_drop(volts, amps, length, q(awg))["values"]
        if drop["percent"].value <= limit:
            return {"values": {"gauge": q(awg), "ampacity": q(ampacity, "A"), "breaker": q(breaker, "A"),
                               "drop": drop["drop"], "percent": drop["percent"]},
                    "said": f"{awg} AWG copper: it carries {ampacity} A (you need {need:.4g} A"
                            f"{', sized at 125% for a continuous load' if continuous.value else ''}), and over {length} "
                            f"one way the drop is {drop['percent'].value:.1f}% (limit {limit:g}%). Largest breaker: "
                            f"{breaker} A."}
    raise CalcError(f"Nothing up to 2 AWG in my table carries {need:.4g} A over {length} within {limit:g}% drop. "
                    f"This needs a larger conductor than I can size.")


def _circuit_load(breaker: Quantity, volts: Quantity) -> dict:
    """What a breaker may carry: its full rating, and 80% of it for a load that runs three hours or more."""
    steady = (breaker * 0.8).to("A")
    return {"values": {"continuous_amps": steady, "continuous_watts": (steady * volts).to("W"),
                       "peak_watts": (breaker * volts).to("W")},
            "said": f"A {breaker} breaker at {volts}: up to {(breaker * volts).to('W')} briefly, and {steady} "
                    f"({(steady * volts).to('W')}) for a load that runs three hours or more."}


def _battery_runtime(capacity: Quantity, volts: Quantity, load: Quantity, usable: Quantity, efficiency: Quantity) -> dict:
    """How long a battery runs a load: its energy, times the part that may be used, times the converter's efficiency."""
    energy = (capacity * volts).to("Wh")
    hours = q(energy.value * usable.si * efficiency.si / load.number("W"), "h")
    return {"values": {"energy": energy, "runtime": hours},
            "said": f"{capacity} at {volts} holds {energy}. Using {usable.si * 100:g}% of it at {efficiency.si * 100:g}% "
                    f"efficiency, a {load} load runs about {hours}."}


def _led_resistor(supply: Quantity, forward: Quantity, current: Quantity) -> dict:
    """The series resistor for an LED: the voltage left over divided by the current, then the next standard value up."""
    if supply <= forward:
        raise CalcError(f"The supply ({supply}) has to be higher than the LED's forward voltage ({forward}).")
    exact = ((supply - forward) / current).to("ohm")
    decade = 10.0 ** (math.floor(math.log10(exact.value)) - 1)  # E12 runs 10 to 82, so 150 ohm is 15 x 10
    standard = next((v * decade for v in E12 if v * decade >= exact.value * 0.9999), 100 * decade)
    chosen = q(standard, "ohm")
    actual = ((supply - forward) / chosen).to("mA")
    heat = ((supply - forward) * actual).to("mW")
    return {"values": {"exact": exact, "resistor": chosen, "current": actual, "resistor_power": heat},
            "said": f"({supply} - {forward}) / {current} = {exact}. The next standard value up is {chosen}, giving "
                    f"{actual} through the LED and {heat} in the resistor."}


def _voltage_divider(vin: Quantity, r1: Quantity, r2: Quantity) -> dict:
    """The output of two resistors in series, taken across the lower one, unloaded."""
    vout = q(vin.si * r2.si / (r1.si + r2.si), "V")
    current = (vin / (r1 + r2)).to("mA")
    return {"values": {"vout": vout, "current": current},
            "said": f"{vin} across {r1} over {r2} gives {vout} at the middle, drawing {current} (with nothing "
                    f"connected to the output; a load pulls it lower)."}


def _battery_life(capacity: Quantity, active: Quantity, sleep: Quantity, awake: Quantity, period: Quantity,
                  usable: Quantity) -> dict:
    """A device that wakes for a while each period: its average current, and the life of a battery at that."""
    if period < awake:
        raise CalcError("The time awake can't be longer than the whole period.")
    share = awake.si / period.si
    average = q((active.si * share + sleep.si * (1 - share)) * 1000, "mA")
    hours = q(capacity.number("mAh") * usable.si / average.value, "h")
    return {"values": {"average_current": average, "life": hours, "life_days": q(hours.value / 24, "day")},
            "said": f"Awake {awake} of every {period} at {active}, asleep at {sleep}: an average of {average}. "
                    f"{capacity} with {usable.si * 100:g}% usable lasts about {hours.value:.4g} hours "
                    f"({hours.value / 24:.3g} days)."}


def _regulator_heat(vin: Quantity, vout: Quantity, current: Quantity, theta: Quantity, ambient: Quantity,
                    limit: Quantity) -> dict:
    """A linear regulator's heat: the voltage it drops times the current, and how hot its junction gets."""
    if vin <= vout:
        raise CalcError(f"A linear regulator needs its input ({vin}) above its output ({vout}).")
    heat = ((vin - vout) * current).to("W")
    rise = q(heat.value * theta.value, "degC")
    junction = q(ambient.value + rise.value, "degC")
    ok = junction.value <= limit.value
    return {"values": {"heat": heat, "rise": rise, "junction": junction, "within_limit": q(1 if ok else 0)},
            "said": f"({vin} - {vout}) x {current} = {heat} of heat. At {theta.value:g} degC/W that is {rise.value:.4g} "
                    f"degC above the {ambient.value:g} degC around it: a junction at {junction.value:.4g} degC, "
                    + (f"under its {limit.value:g} degC limit." if ok else
                       f"OVER its {limit.value:g} degC limit. It needs a heatsink, less drop, or a switching regulator.")}


def _adc_step(vref: Quantity, bits: Quantity) -> dict:
    """The smallest change an analog-to-digital converter can see: the reference divided by its number of steps."""
    n = int(round(bits.value))
    if not 1 <= n <= 32:
        raise CalcError("An ADC has between 1 and 32 bits.")
    step = q(vref.si / (2 ** n) * 1000, "mV")
    return {"values": {"steps": q(2 ** n), "step": step},
            "said": f"A {n}-bit converter on a {vref} reference has {2 ** n} steps of {step} each."}


def _joist(span: Quantity) -> dict:
    """The floor joist size for a span, from the builder's table (16 inches on centre)."""
    from core.build_calcs import joist_for

    size = joist_for(span.number("ft"))
    if not size:
        raise CalcError(f"A {span.to('ft')} span is past my joist table: it needs a beam or an engineered joist, "
                        f"sized by an engineer.")
    return {"values": {"span": span.to("ft")}, "choice": size,
            "said": f"A {span.to('ft')} span at 16 inches on centre: {size} joists, from my span table."}


def _brine_salt(water: Quantity, vegetables: Quantity, strength: Quantity) -> dict:
    """Salt for fermenting vegetables: a percentage of the combined weight of the water and the vegetables."""
    total = water.number("g") + vegetables.number("g")
    salt = q(total * strength.si, "g")
    return {"values": {"salt": salt},
            "said": f"{strength.si * 100:g}% of {total:.4g} g (water and vegetables together) is {salt} of salt."}


def _candle_wax(volume: Quantity, fragrance: Quantity) -> dict:
    """Wax for a container candle: the container's volume times wax's density, and fragrance as a share of the wax."""
    wax = q(volume.number("L") * 1000 * 0.86, "g")
    oil = q(wax.value * fragrance.si, "g")
    return {"values": {"wax": wax, "fragrance": oil},
            "said": f"A {volume} container takes about {wax} of wax (wax is lighter than water: 0.86 g per mL), and "
                    f"{fragrance.si * 100:g}% fragrance is {oil}."}


PROPANE_BTU_PER_GAL = 91_500  # the heat in a US gallon of propane (higher heating value, the figure suppliers give)
VENT_CFM_PER_FT2 = 8  # summer cooling: 8 cfm per square foot of floor below 1000 ft elevation (NGMA, ASABE EP406)


def _greenhouse_heat(area: Quantity, u: Quantity, inside: Quantity, outside: Quantity) -> dict:
    """Heat lost through a greenhouse's glazing on the coldest night: U x A x the inside-outside difference."""
    from core.quantities import temperature

    diff = temperature(inside.value, inside.unit, "degF") - temperature(outside.value, outside.unit, "degF")
    if diff <= 0:
        raise CalcError("Inside must be warmer than outside for there to be heat to make up.")
    loss = q(u.number("BTU/h/ft2/degF") * area.number("ft2") * diff, "BTU/h")
    return {"values": {"heat_loss": loss, "watts": loss.to("W")},
            "said": f"{area.to('ft2')} of glazing at U {u.number('BTU/h/ft2/degF'):g}, {diff:g} degF colder outside, "
                    f"loses {loss} ({loss.to('W')}) through the glazing; air leaks add to it."}


def _vent_fan(floor: Quantity, rate: Quantity) -> dict:
    """Fan capacity for summer cooling: the floor area times the airflow per square foot."""
    per_ft2 = rate.number("cfm/ft2")
    flow = q(floor.number("ft2") * per_ft2, "cfm")
    return {"values": {"flow": flow},
            "said": f"{floor.to('ft2')} of floor at {per_ft2:g} cfm per square foot needs fans moving {flow} "
                    f"(more at high elevation or under glazing with no shade)."}


def _drip(emitters: Quantity, rate: Quantity, hours: Quantity) -> dict:
    """Water for a drip zone: emitters x their flow x hours run."""
    flow = q(emitters.value * rate.number("gph"), "gph")
    used = q(flow.value * hours.number("h"), "gal")
    return {"values": {"flow": flow, "gpm": flow.to("gpm"), "water": used},
            "said": f"{emitters.value:g} emitters at {rate.to('gph')} is {flow} ({flow.to('gpm')}); "
                    f"run {hours.to('h')} that's {used}."}


def _heater_fuel(load: Quantity, hours: Quantity, efficiency: Quantity) -> dict:
    """Propane for a heater: the heat needed over the hours, divided by propane's heat per gallon and the heater's
    efficiency."""
    if efficiency.si <= 0:
        raise CalcError("A heater's efficiency has to be more than 0%.")
    heat = load.number("BTU/h") * hours.number("h")
    gallons = q(heat / (PROPANE_BTU_PER_GAL * efficiency.si), "gal")
    return {"values": {"propane": gallons},
            "said": f"{load.to('BTU/h')} for {hours.to('h')} at {efficiency.si * 100:g}% efficiency burns {gallons} "
                    f"of propane ({PROPANE_BTU_PER_GAL:,} BTU a gallon)."}


# NaOH saponification values (grams of sodium hydroxide per gram of oil), as published lye calculators use them.
SAP_NAOH = {"olive": 0.135, "coconut": 0.183, "lard": 0.138, "tallow": 0.143, "castor": 0.128}


def _stair_risers(rise: Quantity) -> dict:
    """The fewest equal risers that keep each at or under 7 3/4 in, from MIA's stair rule (core/build_calcs.py)."""
    from core.build_calcs import MAX_RISE_IN

    total = rise.number("in")
    if total <= 0:
        raise CalcError("The total rise has to be more than 0.")
    count = math.ceil(total / MAX_RISE_IN)
    riser = q(total / count, "in")
    return {"values": {"risers": q(count), "riser": riser},
            "said": f"A {rise.to('in')} rise takes {count} risers of {riser} each (none over {MAX_RISE_IN} in)."}


def _board_feet(thickness: Quantity, width: Quantity, length: Quantity, count: Quantity) -> dict:
    """Board feet of lumber: nominal inches x inches x feet / 12, times how many (core/toolbox_calcs.py)."""
    from core.toolbox_calcs import board_feet

    try:
        found = board_feet(thickness.number("in"), width.number("in"), length.number("ft"), count.value)
    except ValueError as problem:
        raise CalcError(str(problem)) from None
    return {"values": {"board_feet": q(found["total"])}, "said": found["text"] + "."}


def _concrete_yards(length: Quantity, width: Quantity, thickness: Quantity, extra: Quantity) -> dict:
    """Concrete for a slab: length x width x thickness, plus the extra asked for, in cubic yards and 80 lb bags."""
    from core.build_calcs import BAG_80LB_CUFT

    cubic_ft = length.number("ft") * width.number("ft") * thickness.number("ft") * (1 + extra.si)
    yards = q(cubic_ft, "ft3").to("yd3")
    bags = math.ceil(cubic_ft / BAG_80LB_CUFT)
    return {"values": {"concrete": yards, "bags_80lb": q(bags)},
            "said": f"{length.to('ft')} by {width.to('ft')} at {thickness.to('in')} thick, with {extra.si * 100:g}% "
                    f"extra, is {yards} ({cubic_ft:.3g} cu ft), or {bags} bags of 80 lb mix."}


def _soap_lye(olive: Quantity, coconut: Quantity, lard: Quantity, tallow: Quantity, castor: Quantity,
              superfat: Quantity, water: Quantity) -> dict:
    """Sodium hydroxide for cold-process soap: each oil's weight times its saponification value (SAP_NAOH), less
    the superfat; water as a share of the oils."""
    oils = {"olive": olive, "coconut": coconut, "lard": lard, "tallow": tallow, "castor": castor}
    grams = {name: value.number("g") for name, value in oils.items()}
    total = sum(grams.values())
    if total <= 0:
        raise CalcError("Soap Lye needs the oils: the grams of at least one of olive, coconut, lard, tallow or castor.")
    if superfat.si >= 1:
        raise CalcError("A superfat has to be under 100%.")
    lye = q(sum(g * SAP_NAOH[name] for name, g in grams.items()) * (1 - superfat.si), "g")
    wet = q(total * water.si, "g")
    used = ", ".join(f"{g:g} g {name}" for name, g in grams.items() if g)
    return {"values": {"lye": lye, "water": wet},
            "said": f"{used} at {superfat.si * 100:g}% superfat takes {lye} of sodium hydroxide (lye), in {wet} of "
                    f"water. Wear gloves and eye protection, add lye to water (never water to lye), and work with "
                    f"air moving."}


def _alum_mordant(fibre: Quantity, rate: Quantity) -> dict:
    """Alum for mordanting fibre: a share of the dry fibre's weight."""
    alum = q(fibre.number("g") * rate.si, "g")
    return {"values": {"alum": alum},
            "said": f"{fibre.to('g')} of dry fibre at {rate.si * 100:g}% of its weight takes {alum} of alum."}


# ---- the hoodie's specialists (S4's second batch): acoustics, audio DSP, textiles and portable power

SOUND_SPEED_0C = 331.3  # metres a second in dry air at 0 degC, rising 0.606 m/s for each degree
SOUND_SPEED_PER_DEGC = 0.606
NIOSH_DBA, NIOSH_HOURS, NIOSH_EXCHANGE = 85.0, 8.0, 3.0  # NIOSH's recommended limit: 85 dBA for 8 h, 3 dB halves it


def _spl_at_distance(sensitivity: Quantity, power: Quantity, distance: Quantity) -> dict:
    """A speaker's sound pressure level at a distance: its sensitivity (dB at 1 W and 1 m), plus 10 log10 of the
    watts, less 20 log10 of the metres (the inverse square law, in the open)."""
    watts, metres = power.number("W"), distance.number("m")
    if watts <= 0 or metres <= 0:
        raise CalcError("The power and the distance both have to be more than 0.")
    spl = q(sensitivity.number("dB") + 10 * math.log10(watts) - 20 * math.log10(metres), "dB")
    return {"values": {"spl": spl},
            "said": f"A speaker of {sensitivity.number('dB'):g} dB (1 W, 1 m) given {power.to('W')} is about {spl} at "
                    f"{distance.to('m')} in the open; a room's reflections add a little."}


def _amp_power(target: Quantity, sensitivity: Quantity, distance: Quantity, headroom: Quantity) -> dict:
    """The amplifier power for a level at a distance: the inverse of SPL At Distance, plus headroom for peaks."""
    metres = distance.number("m")
    if metres <= 0:
        raise CalcError("The distance has to be more than 0.")
    needed = target.number("dB") - sensitivity.number("dB") + 20 * math.log10(metres) + headroom.number("dB")
    watts = q(10 ** (needed / 10), "W")
    return {"values": {"power": watts},
            "said": f"To reach {target.number('dB'):g} dB at {distance.to('m')} from a speaker of "
                    f"{sensitivity.number('dB'):g} dB (1 W, 1 m), with {headroom.number('dB'):g} dB of headroom for peaks, takes {watts} of amplifier "
                    f"power (every 3 dB more doubles it)."}


def _sealed_box(vas: Quantity, qts: Quantity, qtc: Quantity) -> dict:
    """A sealed box's volume for a driver: Vb = Vas / ((Qtc / Qts)^2 - 1), from its Thiele-Small figures."""
    if qts.value <= 0 or qtc.value <= qts.value:
        raise CalcError("A sealed box only raises a driver's Q, so the Qtc wanted has to be above its Qts.")
    ratio = (qtc.value / qts.value) ** 2 - 1
    box = q(vas.number("L") / ratio, "L")
    return {"values": {"volume": box, "alpha": q(ratio)},
            "said": f"A driver with Vas {vas.to('L')} and Qts {qts.value:g} reaches Qtc {qtc.value:g} in a sealed "
                    f"box of {box} inside, not counting the driver's own volume or bracing."}


def _sound_delay(distance: Quantity, air: Quantity) -> dict:
    """How long sound takes over a distance: the speed of sound in air at that temperature (331.3 m/s at 0 degC,
    plus 0.606 for each degree)."""
    from core.quantities import temperature

    celsius = temperature(air.value, air.unit, "degC")
    speed = SOUND_SPEED_0C + SOUND_SPEED_PER_DEGC * celsius
    if speed <= 0:
        raise CalcError("That's too cold for air to carry sound in this formula.")
    delay = q(distance.number("m") / speed * 1000, "ms")
    return {"values": {"delay": delay, "speed": q(speed)},
            "said": f"Sound covers {distance.to('m')} in {delay} in {celsius:g} degC air ({speed:.4g} m/s)."}


def _noise_exposure(level: Quantity) -> dict:
    """How long a day a sound level may be heard: NIOSH's 8 hours at 85 dBA, halved for every 3 dB above it."""
    hours = q(NIOSH_HOURS / 2 ** ((level.number("dB") - NIOSH_DBA) / NIOSH_EXCHANGE), "h")
    if level.number("dB") <= NIOSH_DBA:
        said = f"{level.number('dB'):g} dBA is within NIOSH's limit for a full 8 hour day."
    else:
        said = (f"At {level.number('dB'):g} dBA, NIOSH's limit is reached after {hours.to('h')} "
                f"({hours.to('min')}) a day. Turn it down: hearing lost to noise doesn't come back.")
    return {"values": {"hours": hours}, "said": said}


def _buffer_latency(buffer: Quantity, rate: Quantity) -> dict:
    """The time one audio buffer holds: its samples divided by the sample rate."""
    hertz = rate.number("Hz")
    if hertz <= 0 or buffer.value <= 0:
        raise CalcError("The buffer and the sample rate both have to be more than 0.")
    latency = q(buffer.value / hertz * 1000, "ms")
    return {"values": {"latency": latency},
            "said": f"A {buffer.value:g} sample buffer at {rate.to('kHz')} holds {latency}; input and output "
                    f"buffers add up, so a round trip is at least twice that."}


def _audio_bitrate(rate: Quantity, bits: Quantity, channels: Quantity) -> dict:
    """Uncompressed audio's data rate: sample rate x bits x channels, and what an hour of it takes."""
    per_second = rate.number("Hz") * bits.value * channels.value
    bitrate = q(per_second, "bps").to("kbps")
    hour = q(per_second * 3600, "bit").to("MB")
    return {"values": {"bitrate": bitrate, "per_hour": hour},
            "said": f"{rate.to('kHz')}, {bits.value:g} bit, {channels.value:g} channel audio is {bitrate} "
                    f"uncompressed, {hour} an hour."}


def _dynamic_range(bits: Quantity) -> dict:
    """The dynamic range of a converter's bits, for a full-scale sine: 6.02 dB a bit plus 1.76 dB."""
    if bits.value < 1:
        raise CalcError("The bit depth has to be at least 1.")
    dr = q(20 * math.log10(2) * bits.value + 1.76, "dB")
    return {"values": {"range": dr},
            "said": f"{bits.value:g} bits give at most {dr} of dynamic range; real converters and analogue parts "
                    f"give less."}


def _fft_resolution(rate: Quantity, size: Quantity) -> dict:
    """An FFT's frequency resolution and frame length: sample rate / size, and size / sample rate."""
    hertz = rate.number("Hz")
    if hertz <= 0 or size.value < 2:
        raise CalcError("The sample rate has to be more than 0 and the FFT size at least 2.")
    return {"values": {"bin": q(hertz / size.value, "Hz"), "frame": q(size.value / hertz * 1000, "ms")},
            "said": f"A {size.value:g} point FFT at {rate.to('kHz')} has bins {q(hertz / size.value, 'Hz')} apart "
                    f"and needs {q(size.value / hertz * 1000, 'ms')} of audio a frame."}


def _delay_samples(delay: Quantity, rate: Quantity) -> dict:
    """A time delay as a whole number of samples at a sample rate (the nearest one)."""
    exact = delay.number("s") * rate.number("Hz")
    samples = round(exact)
    return {"values": {"samples": q(samples), "exact": q(exact)},
            "said": f"{delay.to('ms')} at {rate.to('kHz')} is {samples} samples"
                    + (f" (exactly {exact:.4g}; the rest needs a fractional delay)." if abs(exact - samples) > 1e-9
                       else ".")}


def _fabric_yardage(count: Quantity, length: Quantity, width: Quantity, fabric: Quantity, seam: Quantity,
                    shrink: Quantity) -> dict:
    """Fabric for pieces laid in rows across its width: each piece with its seam allowance on every edge, as many
    across as fit, rows down the length, plus the shrinkage when it's washed first."""
    cut_long, cut_wide = length.number("in") + 2 * seam.number("in"), width.number("in") + 2 * seam.number("in")
    across = math.floor(fabric.number("in") / cut_wide) if cut_wide > 0 else 0
    if across < 1:
        raise CalcError(f"A piece cut {cut_wide:g} in wide doesn't fit across {fabric.to('in')} fabric: turn it or "
                        f"piece it.")
    if shrink.si >= 1:
        raise CalcError("Shrinkage has to be under 100%.")
    rows = math.ceil(count.value / across)
    inches = rows * cut_long / (1 - shrink.si)
    yards = q(inches, "in").to("yd")
    return {"values": {"yards": yards, "across": q(across), "rows": q(rows)},
            "said": f"{count.value:g} pieces cut {cut_long:g} by {cut_wide:g} in (with seam allowance) fit {across} "
                    f"across {fabric.to('in')} fabric, in {rows} rows: {yards} ({q(inches, 'in')}). Add more for "
                    f"matching a pattern or a nap."}


def _fabric_weight(gsm: Quantity, length: Quantity, width: Quantity) -> dict:
    """A piece of fabric's weight: its weight per area times its area; and the weight per area in oz per sq yd."""
    area = length.number("m") * width.number("m")
    grams = q(gsm.number("g/m2") * area, "g")
    return {"values": {"weight": grams, "oz_per_yd2": gsm.to("oz/yd2")},
            "said": f"{area:.4g} m2 of {gsm.to('g/m2')} fabric ({gsm.to('oz/yd2')}) weighs {grams}."}


def _shrink_allowance(finished: Quantity, shrink: Quantity) -> dict:
    """The length to cut so it's the length wanted after it shrinks: finished / (1 - shrinkage)."""
    if shrink.si >= 1:
        raise CalcError("Shrinkage has to be under 100%.")
    cut = q(finished.number("in") / (1 - shrink.si), "in")
    return {"values": {"cut": cut},
            "said": f"For {finished.to('in')} after {shrink.si * 100:g}% shrinkage, cut {cut}; better still, wash it "
                    f"before cutting."}


def _conductive_trace(resistance: Quantity, length: Quantity, volts: Quantity) -> dict:
    """A conductive thread or trace's resistance (per length x length), and the current and heat it takes at a
    voltage (Ohm's law, P = V^2 / R)."""
    ohms = q(resistance.number("ohm/m") * length.number("m"), "ohm")
    if ohms.si <= 0:
        raise CalcError("The thread's resistance and length both have to be more than 0.")
    amps = (volts / ohms).to("A")
    watts = (volts * amps).to("W")
    return {"values": {"resistance": ohms, "current": amps, "power": watts},
            "said": f"{length.to('m')} of thread at {resistance.to('ohm/m')} is {ohms}; across {volts.to('V')} it "
                    f"carries {amps} and turns {watts} into heat in the fabric against the body."}


def _battery_pack(cell_volts: Quantity, cell_capacity: Quantity, series: Quantity, parallel: Quantity) -> dict:
    """A pack of identical cells: the voltage adds in series, the capacity in parallel; energy is the two times."""
    s, p = int(round(series.value)), int(round(parallel.value))
    if s < 1 or p < 1:
        raise CalcError("A pack needs at least one cell in series and one in parallel.")
    volts = q(cell_volts.number("V") * s, "V")
    mah = q(cell_capacity.number("mAh") * p, "mAh")
    energy = (volts * mah).to("Wh")
    carry = " (over the 100 Wh airlines allow in a carry-on without approval)" if energy.number("Wh") > 100 else ""
    return {"values": {"volts": volts, "capacity": mah, "energy": energy},
            "said": f"{s}S{p}P of {cell_volts.to('V')}, {cell_capacity.to('mAh')} cells is {volts}, {mah}, "
                    f"{energy}{carry}. A lithium pack needs a protection board (BMS) and matched cells."}


def _charge_time(capacity: Quantity, current: Quantity, efficiency: Quantity) -> dict:
    """Roughly how long a charge takes: capacity / (charge current x efficiency); the last part, at constant
    voltage, tapers and takes longer."""
    if current.si <= 0 or efficiency.si <= 0:
        raise CalcError("The charge current and efficiency have to be more than 0.")
    hours = q(capacity.number("mAh") / (current.number("mA") * efficiency.si), "h")
    rate = current.number("mA") / capacity.number("mAh") if capacity.si > 0 else 0
    warn = f" {rate:.2g}C is a fast charge: check the cell's datasheet allows it." if rate > 1 else ""
    return {"values": {"hours": hours, "c_rate": q(rate)},
            "said": f"{capacity.to('mAh')} at {current.to('mA')} ({rate:.2g}C), {efficiency.si * 100:g}% efficient, "
                    f"takes about {hours}; the constant-voltage end adds time.{warn}"}


def _c_rate(capacity: Quantity, load: Quantity, limit: Quantity) -> dict:
    """How hard a load works a battery: its current over the capacity (the C-rate), against the cell's limit."""
    if capacity.si <= 0:
        raise CalcError("The capacity has to be more than 0.")
    rate = load.number("mA") / capacity.number("mAh")
    within = rate <= limit.value
    return {"values": {"c_rate": q(rate), "within": q(1 if within else 0)},
            "said": f"{load.to('A')} from {capacity.to('mAh')} is {rate:.3g}C, "
                    + ("within" if within else "over") + f" the cell's {limit.value:g}C."}


def _boost_current(vout: Quantity, iout: Quantity, vin: Quantity, efficiency: Quantity) -> dict:
    """The current a converter draws from its input: output power / efficiency / input voltage."""
    if efficiency.si <= 0 or vin.si <= 0:
        raise CalcError("The input voltage and efficiency have to be more than 0.")
    out = (vout * iout).to("W")
    into = q(out.si / efficiency.si, "W")
    amps = (into / vin).to("A")
    return {"values": {"input_current": amps, "input_power": into, "loss": q(into.si - out.si, "W")},
            "said": f"{vout.to('V')} at {iout.to('A')} is {out}; at {efficiency.si * 100:g}% efficiency it draws "
                    f"{into} from {vin.to('V')}, which is {amps} (and {q(into.si - out.si, 'W')} of heat)."}


CALCULATORS: tuple[Calculator, ...] = (
    Calculator("power", "electrical", "Power", "Watts from volts and amps.",
               {"volts": ("V", "the voltage", None), "amps": ("A", "the current", None)}, _power, "P = V x I"),
    Calculator("voltage_drop", "electrical", "Voltage Drop", "The voltage lost along a two-wire copper run.",
               {"volts": ("V", "the supply voltage", None), "amps": ("A", "the current", None),
                "length": ("ft", "the one-way length of the run", None), "gauge": ("", "the wire's AWG number", None)},
               _voltage_drop, "V = I x R, with copper's resistance per foot at 20 degC, out and back", True),
    Calculator("wire_gauge", "electrical", "Wire Gauge", "The smallest copper wire for a load and a run length.",
               {"volts": ("V", "the supply voltage", None), "amps": ("A", "the load's current", None),
                "length": ("ft", "the one-way length of the run", None),
                "max_drop": ("%", "the most voltage drop allowed", "3 %"),
                "continuous": ("", "1 if the load runs three hours or more, else 0", "0")},
               _wire_gauge, "the 60 degC ampacity column for copper, the small-conductor breaker limits, 125% for a "
               "continuous load, and voltage drop out and back", True),
    Calculator("circuit_load", "electrical", "Circuit Load", "What a breaker may carry, briefly and continuously.",
               {"breaker": ("A", "the breaker's rating", None), "volts": ("V", "the circuit's voltage", None)},
               _circuit_load, "a load of three hours or more is held to 80% of the breaker", True),
    Calculator("battery_runtime", "electrical", "Battery Runtime", "How long a battery runs a load.",
               {"capacity": ("Ah", "the battery's capacity", None), "volts": ("V", "the battery's voltage", None),
                "load": ("W", "the load's power", None), "usable": ("%", "how much of the battery may be used", "80 %"),
                "efficiency": ("%", "the inverter's or converter's efficiency", "90 %")},
               _battery_runtime, "energy = Ah x V; runtime = energy x usable x efficiency / load", True),
    Calculator("led_resistor", "embedded", "LED Resistor", "The series resistor for an LED.",
               {"supply": ("V", "the supply voltage", None), "forward": ("V", "the LED's forward voltage", None),
                "current": ("mA", "the LED current wanted", None)},
               _led_resistor, "R = (Vsupply - Vforward) / I, rounded up to the E12 series"),
    Calculator("voltage_divider", "embedded", "Voltage Divider", "The output of two resistors in series.",
               {"vin": ("V", "the input voltage", None), "r1": ("ohm", "the upper resistor", None),
                "r2": ("ohm", "the lower resistor, across the output", None)},
               _voltage_divider, "Vout = Vin x R2 / (R1 + R2), unloaded"),
    Calculator("battery_life", "embedded", "Battery Life With Sleep", "The life of a battery in a device that sleeps.",
               {"capacity": ("mAh", "the battery's capacity", None), "active": ("mA", "the current while awake", None),
                "sleep": ("uA", "the current while asleep", None), "awake": ("s", "how long it's awake each time", None),
                "period": ("s", "how often it wakes", None), "usable": ("%", "how much of the battery may be used", "85 %")},
               _battery_life, "average current = the time-weighted mean of awake and asleep; life = capacity / average"),
    Calculator("regulator_heat", "embedded", "Linear Regulator Heat", "A linear regulator's heat and temperature.",
               {"vin": ("V", "the input voltage", None), "vout": ("V", "the output voltage", None),
                "current": ("mA", "the load current", None),
                "theta": ("degC/W", "the package's junction-to-air thermal resistance", None),
                "ambient": ("degC", "the temperature around it", "25 degC"),
                "limit": ("degC", "the most its junction may reach", "125 degC")},
               _regulator_heat, "P = (Vin - Vout) x I; junction = ambient + P x thermal resistance", True),
    Calculator("adc_step", "embedded", "ADC Step Size", "The smallest voltage change an ADC can see.",
               {"vref": ("V", "the reference voltage", None), "bits": ("", "the converter's resolution in bits", None)},
               _adc_step, "step = Vref / 2^bits"),
    Calculator("floor_joist", "structural", "Floor Joist", "The joist size for a floor span.",
               {"span": ("ft", "the clear span", None)}, _joist,
               "MIA's span table (core/build_calcs.py): common lumber at 16 inches on centre, a 40 psf floor", True),
    Calculator("brine_salt", "crafts", "Brine Salt", "Salt for fermenting vegetables.",
               {"water": ("g", "the weight of water", None), "vegetables": ("g", "the weight of vegetables", None),
                "strength": ("%", "the salt percentage", "2 %")},
               _brine_salt, "common fermenting practice: salt as a percentage of the water and vegetables together; "
               "for canning and curing, follow a tested recipe instead"),
    Calculator("candle_wax", "crafts", "Candle Wax", "Wax and fragrance for a container candle.",
               {"volume": ("L", "the container's volume", None), "fragrance": ("%", "the fragrance load", "8 %")},
               _candle_wax, "common candle-making practice: wax at 0.86 g per mL; check the wax maker's own maximum "
               "fragrance load"),
    Calculator("stair_risers", "structural", "Stair Risers", "How many equal risers a stair needs, and how tall "
               "each is.", {"rise": ("in", "the total rise, floor to floor", None)}, _stair_risers,
               "the fewest equal risers at or under 7 3/4 in each, the common residential code limit; check yours",
               True),
    Calculator("board_feet", "structural", "Board Feet", "Board feet of lumber.",
               {"thickness": ("in", "the nominal thickness", None), "width": ("in", "the nominal width", None),
                "length": ("ft", "each board's length", None), "count": ("", "how many boards", "1")},
               _board_feet, "thickness (in) x width (in) x length (ft) / 12, times the count"),
    Calculator("concrete_yards", "structural", "Concrete For A Slab", "Concrete for a slab or pad, in cubic yards "
               "and 80 lb bags.",
               {"length": ("ft", "the slab's length", None), "width": ("ft", "the slab's width", None),
                "thickness": ("in", "the slab's thickness", None),
                "extra": ("%", "extra for waste and uneven ground", "10 %")},
               _concrete_yards, "length x width x thickness, plus the extra; 0.6 cu ft from an 80 lb bag"),
    Calculator("soap_lye", "crafts", "Soap Lye", "Sodium hydroxide (lye) and water for cold-process soap.",
               {"olive": ("g", "olive oil's weight", "0 g"), "coconut": ("g", "coconut oil's weight", "0 g"),
                "lard": ("g", "lard's weight", "0 g"), "tallow": ("g", "beef tallow's weight", "0 g"),
                "castor": ("g", "castor oil's weight", "0 g"),
                "superfat": ("%", "the oil left unsaponified", "5 %"),
                "water": ("%", "water as a share of the oils' weight", "38 %")},
               _soap_lye, "each oil's weight x its NaOH saponification value (olive 0.135, coconut 0.183, lard 0.138, "
               "tallow 0.143, castor 0.128), less the superfat", True),
    Calculator("alum_mordant", "crafts", "Alum Mordant", "Alum to mordant fibre before dyeing.",
               {"fibre": ("g", "the dry fibre's weight", None), "rate": ("%", "alum as a share of the fibre", "15 %")},
               _alum_mordant, "alum at a share of the weight of fibre (15% is common for wool); follow the dye "
               "maker's own rate"),
    Calculator("greenhouse_heat", "greenhouse", "Greenhouse Heat Loss", "Heat lost through the glazing on the "
               "coldest night, which the heater must make up.",
               {"area": ("ft2", "the glazing's total area, walls and roof", None),
                "u": ("BTU/h/ft2/degF", "the glazing's U-value, from its maker's sheet", None),
                "inside": ("degF", "the lowest temperature to keep inside", None),
                "outside": ("degF", "the coldest outside temperature to plan for", None)},
               _greenhouse_heat, "Q = U x A x (inside - outside), conduction through the glazing only", True,
               signed=("inside", "outside")),
    Calculator("vent_fan", "greenhouse", "Greenhouse Fan Size", "Exhaust fan capacity for summer cooling.",
               {"floor": ("ft2", "the floor area", None),
                "rate": ("cfm/ft2", "the airflow per square foot of floor", f"{VENT_CFM_PER_FT2} cfm/ft2")},
               _vent_fan, "8 cfm per square foot of floor below 1000 ft elevation (NGMA, ASABE EP406)"),
    Calculator("drip_irrigation", "greenhouse", "Drip Zone Water", "A drip zone's flow and the water it uses.",
               {"emitters": ("", "how many emitters", None), "rate": ("gph", "each emitter's flow", None),
                "hours": ("h", "how long it runs", "1 h")},
               _drip, "flow = emitters x each one's flow; water = flow x hours"),
    Calculator("heater_fuel", "greenhouse", "Heater Propane", "Propane a heater burns making up a heat load.",
               {"load": ("BTU/h", "the heat needed (from Greenhouse Heat Loss)", None),
                "hours": ("h", "how many hours it runs", None),
                "efficiency": ("%", "the heater's efficiency", "80 %")},
               _heater_fuel, "gallons = load x hours / (91,500 BTU per gallon x efficiency); an unvented heater "
               "needs fresh air and a CO alarm", True),
    # ---- acoustics
    Calculator("spl_at_distance", "acoustics", "SPL At Distance", "How loud a speaker is at a distance.",
               {"sensitivity": ("dB", "the speaker's sensitivity at 1 W and 1 m, from its sheet", None),
                "power": ("W", "the amplifier power into it", None),
                "distance": ("m", "how far away the listener is", None)},
               _spl_at_distance, "SPL = sensitivity + 10 log10(W) - 20 log10(m), the inverse square law in the open"),
    Calculator("amp_power", "acoustics", "Amplifier Power", "The amplifier power for a level at a distance.",
               {"target": ("dB", "the sound level wanted at the listener", None),
                "sensitivity": ("dB", "the speaker's sensitivity at 1 W and 1 m, from its sheet", None),
                "distance": ("m", "how far away the listener is", None),
                "headroom": ("dB", "extra for peaks above the level wanted", "3 dB")},
               _amp_power, "W = 10^((target - sensitivity + 20 log10(m) + headroom) / 10)"),
    Calculator("sealed_box", "acoustics", "Sealed Box Volume", "The sealed enclosure for a driver.",
               {"vas": ("L", "the driver's Vas (equivalent air volume), from its sheet", None),
                "qts": ("", "the driver's Qts, from its sheet", None),
                "qtc": ("", "the box's total Q wanted", "0.707")},
               _sealed_box, "Vb = Vas / ((Qtc / Qts)^2 - 1), Thiele-Small; 0.707 is the flattest response"),
    Calculator("sound_delay", "acoustics", "Sound Delay", "How long sound takes to travel a distance (for placing "
               "speakers, or delaying one to line up with another).",
               {"distance": ("m", "the distance", None), "air": ("degC", "the air's temperature", "20 degC")},
               _sound_delay, "speed of sound = 331.3 + 0.606 x degC metres a second, in dry air", signed=("air",)),
    Calculator("noise_exposure", "acoustics", "Safe Listening Time", "How long a day a sound level may be heard.",
               {"level": ("dB", "the A-weighted level at the ears", None)},
               _noise_exposure, "NIOSH's recommended limit: 85 dBA for 8 hours, halved for every 3 dB above"),
    # ---- audio DSP
    Calculator("buffer_latency", "audio_dsp", "Buffer Latency", "The time an audio buffer holds.",
               {"buffer": ("", "the buffer's length in samples", None), "rate": ("kHz", "the sample rate", None)},
               _buffer_latency, "latency = samples / sample rate, for one buffer"),
    Calculator("audio_bitrate", "audio_dsp", "Audio Data Rate", "Uncompressed audio's data rate and size an hour.",
               {"rate": ("kHz", "the sample rate", None), "bits": ("", "the bit depth", None),
                "channels": ("", "how many channels", "2")},
               _audio_bitrate, "bit rate = sample rate x bits x channels; 8 bits a byte"),
    Calculator("dynamic_range", "audio_dsp", "Dynamic Range", "The most dynamic range a bit depth can hold.",
               {"bits": ("", "the bit depth", None)},
               _dynamic_range, "DR = 6.02 x bits + 1.76 dB, for a full-scale sine and ideal quantisation"),
    Calculator("fft_resolution", "audio_dsp", "FFT Resolution", "An FFT's bin spacing and frame length.",
               {"rate": ("kHz", "the sample rate", None), "size": ("", "the FFT's size in samples", None)},
               _fft_resolution, "bin = sample rate / size; frame = size / sample rate"),
    Calculator("delay_samples", "audio_dsp", "Delay In Samples", "A delay as a number of samples.",
               {"delay": ("ms", "the delay", None), "rate": ("kHz", "the sample rate", None)},
               _delay_samples, "samples = delay x sample rate, to the nearest whole sample"),
    # ---- textiles
    Calculator("fabric_yardage", "textiles", "Fabric Yardage", "Fabric for a set of pattern pieces.",
               {"count": ("", "how many pieces", None), "length": ("in", "each piece's length, along the grain", None),
                "width": ("in", "each piece's width", None), "fabric": ("in", "the fabric's width off the bolt", None),
                "seam": ("in", "the seam allowance on every edge", "0.5 in"),
                "shrink": ("%", "how much it shrinks when washed first", "0 %")},
               _fabric_yardage, "pieces with seam allowance laid in rows across the width, rows x length, divided by "
               "(1 - shrinkage); pattern and nap matching need more"),
    Calculator("fabric_weight", "textiles", "Fabric Weight", "A piece of fabric's weight, and its weight per sq yd.",
               {"gsm": ("g/m2", "the fabric's weight per square metre (GSM)", None),
                "length": ("m", "the piece's length", None), "width": ("m", "the piece's width", None)},
               _fabric_weight, "weight = GSM x area; 1 oz per sq yd is 33.9 g per sq m"),
    Calculator("shrink_allowance", "textiles", "Shrinkage Allowance", "The length to cut for a length after "
               "shrinking.", {"finished": ("in", "the length wanted after washing", None),
                              "shrink": ("%", "how much it shrinks", None)},
               _shrink_allowance, "cut = finished / (1 - shrinkage)"),
    Calculator("conductive_trace", "textiles", "Conductive Thread", "A conductive thread's resistance, current and "
               "heat.", {"resistance": ("ohm/m", "the thread's resistance per length, from its maker", None),
                         "length": ("m", "the length of the run", None), "volts": ("V", "the voltage across it", None)},
               _conductive_trace, "R = resistance per length x length; I = V / R; P = V x I", True),
    # ---- portable power
    Calculator("battery_pack", "power", "Battery Pack", "A pack's voltage, capacity and energy from its cells.",
               {"cell_volts": ("V", "one cell's nominal voltage", None),
                "cell_capacity": ("mAh", "one cell's capacity", None),
                "series": ("", "cells in series", None), "parallel": ("", "cells in parallel", "1")},
               _battery_pack, "volts = cell x series; capacity = cell x parallel; Wh = V x Ah", True),
    Calculator("charge_time", "power", "Charge Time", "Roughly how long a battery takes to charge.",
               {"capacity": ("mAh", "the battery's capacity", None), "current": ("mA", "the charge current", None),
                "efficiency": ("%", "the charge's efficiency", "85 %")},
               _charge_time, "hours = capacity / (current x efficiency), before the constant-voltage taper", True),
    Calculator("c_rate", "power", "C-Rate", "How hard a load works a battery.",
               {"capacity": ("mAh", "the battery's capacity", None), "load": ("A", "the load's current", None),
                "limit": ("", "the cell's rated continuous C-rate, from its sheet", "1")},
               _c_rate, "C-rate = current / capacity (1C empties it in an hour)", True),
    Calculator("boost_current", "power", "Converter Input Current", "The current a boost or buck converter draws.",
               {"vout": ("V", "the output voltage", None), "iout": ("A", "the output current", None),
                "vin": ("V", "the input (battery) voltage", None),
                "efficiency": ("%", "the converter's efficiency, from its sheet", "90 %")},
               _boost_current, "input current = Vout x Iout / efficiency / Vin", True),
)
BY_ID = {c.id: c for c in CALCULATORS}
_POINTS = ("degC", "degF", "K")  # an input in one of these is a temperature, not a difference of one
DISCIPLINES = tuple(dict.fromkeys(c.discipline for c in CALCULATORS))


def _read(calc: Calculator, name: str, given) -> Quantity:
    """One input as a quantity in the kind of unit the calculator expects: a quantity as it is, text with a unit
    read, a bare number taken in the declared unit. CalcError naming the input when it doesn't fit. An input in degC
    or degF is a temperature (a point on a scale), so one given on another scale is converted as a point: 7 degC is
    44.6 degF, not the 12.6 a difference would be."""
    from core.quantities import temperature

    unit, what, _default = calc.inputs[name]
    try:
        if isinstance(given, Quantity):
            value = given
        elif isinstance(given, (int, float)) and not isinstance(given, bool):
            value = q(given, unit)
        else:
            value = parse(str(given))
            if value.unit == "" and unit != "":
                value = q(value.value, unit)
        if unit in _POINTS and value.unit in _POINTS and value.unit != unit:
            return q(temperature(value.value, value.unit, unit), unit)
        return value.to(unit) if unit != "%" or value.unit == "%" else q(value.value, "%")
    except UnitError as problem:
        raise CalcError(f"{name} ({what}) should be in {unit or 'a plain number'}: {problem}") from None


def calculate(calc_id: str, inputs: dict) -> dict:
    """Runs a calculator: {"calculator", "values" (name -> Quantity), "said", "basis", "caveat" ("" unless it's
    safety-critical), and "choice" when the answer is a size in words}. CalcError for a calculator MIA doesn't
    have, an input it doesn't take, a missing input (each named with what it is), or values that can't work."""
    calc = BY_ID.get(str(calc_id or ""))
    if calc is None:
        raise CalcError(f"I don't have a calculator called \"{calc_id}\".")
    inputs = dict(inputs or {})
    unknown = sorted(set(inputs) - set(calc.inputs))
    if unknown:
        raise CalcError(f"{calc.label} doesn't take {', '.join(unknown)}. It takes {', '.join(calc.inputs)}.")
    missing = [f"{name} ({what}, in {unit or 'a plain number'})" for name, (unit, what, default) in calc.inputs.items()
               if default is None and inputs.get(name) in (None, "")]
    if missing:
        raise CalcError(f"{calc.label} needs {'; '.join(missing)}.")
    values = {name: _read(calc, name, inputs[name] if inputs.get(name) not in (None, "") else default)
              for name, (_unit, _what, default) in calc.inputs.items()}
    negative = [name for name, v in values.items() if v.si < 0 and name not in calc.signed]
    if negative:
        raise CalcError(f"{', '.join(negative)} can't be negative.")
    try:
        result = calc.run(**values)
    except UnitError as problem:
        raise CalcError(str(problem)) from None
    return {"calculator": calc.id, "values": result["values"], "said": result["said"], "basis": calc.basis,
            "caveat": CAVEAT if calc.safety else "", **({"choice": result["choice"]} if "choice" in result else {})}


def catalogue(discipline: str = "") -> list[dict]:
    """The calculators as a specialist is shown them (for one discipline, or all): id, discipline, name, what it
    works out, and each input with its unit, what it is and its default."""
    return [{"id": c.id, "discipline": c.discipline, "label": c.label, "about": c.about, "safety": c.safety,
             "inputs": {n: {"unit": u, "what": w, "default": d} for n, (u, w, d) in c.inputs.items()}}
            for c in CALCULATORS if not discipline or c.discipline == discipline]
