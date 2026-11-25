"""
core.boards
=============

The boards MIA's labs are built on (docs/future/INTERACTIVE_LABS_PLAN.md; Zac, 2026-11-25: "I also have an arduino
ELEGOO MEGA R3 kit and a bunch of arduino nanos that she should be able to teach me with"). Pure data, read by the
bench (core/esp32_lab.py: building, flashing, reading), the simulator (core/esp32_sim.py: pins, rails, limits) and
the course page (web/labsim.js draws `left` and `right`).

A `Board`: its id, its name, PlatformIO's platform and board id, the serial speed its labs use, its logic voltage and
the rail that carries it, the ADC's top reading, the pins drawn down each side (as printed on it), its supply rails,
the pins that only read, the pins that carry the USB serial, and the USB chips it's found by. A board's `family` is
the pin names its course's circuits use: the Mega and the Nano share the Arduino's (D2 to D13, A0 to A7, 5V, 3V3,
VIN, GND), so one Arduino course is wired the same on both, drawn and flashed for the one he has.

Facts: the ESP32's 3.3 V logic, 12-bit ADC and input-only GPIO 34 to 39 (Espressif's ESP32 datasheet); the ATmega2560
and ATmega328P's 5 V logic and 10-bit ADC (Microchip's datasheets), the Nano's analog-only A6 and A7, and its D0 and
D1 shared with the USB serial (Arduino's Nano and Mega 2560 documentation).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Board:
    """One board the labs run on (see the module's opening)."""
    id: str
    name: str
    short: str                 # "the ESP32", "the Arduino": said in a problem
    family: str                # whose pin names its circuits use: "esp32" or "arduino"
    platform: str              # PlatformIO's platform
    pio_board: str             # PlatformIO's board id
    baud: int
    logic_rail: str            # the rail at its logic voltage: "3V3" or "5V"
    logic_volts: float
    adc_max: int
    left: tuple
    right: tuple
    supplies: tuple            # its supply rails, besides GND
    input_only: frozenset = frozenset()
    serial: frozenset = frozenset()
    usb: frozenset = frozenset()   # (vid, pid) of its USB chips; a pid of None matches any from that vid
    printed: dict = field(default_factory=dict)

    @property
    def pins(self) -> tuple:
        """Every pin drawn, left then right."""
        return self.left + self.right

    def label(self, pin: str) -> str:
        """What's printed beside a pin: D2 for the ESP32's GPIO 2, VP, TX0, GND; an Arduino's as it's named."""
        if pin in self.printed:
            return self.printed[pin]
        if pin.startswith("GPIO "):
            return "D" + pin[5:]
        return "GND" if pin == "GND 2" else pin

    def is_signal(self, pin: str) -> bool:
        """Whether a pin is one a sketch reads or drives (not a rail, reset or reference).
        The Mega's SDA and SCL header pins count, on a board that draws them."""
        return pin.startswith("GPIO ") or (pin[:1] in ("D", "A") and pin[1:].isdigit()) or (
            pin in ("SDA", "SCL") and pin in self.pins)  # the Mega's own I2C header

    @property
    def signals(self) -> tuple:
        """Its signal pins, in drawing order."""
        return tuple(p for p in FAMILY_PINS[self.family] if self.is_signal(p))

    def found_by(self, vid, pid) -> bool:
        """Whether a USB chip (vid, pid) is one this board is found by."""
        return (vid, pid) in self.usb or (vid, None) in self.usb


_ESP32_LEFT = ("EN", "GPIO 36", "GPIO 39", "GPIO 34", "GPIO 35", "GPIO 32", "GPIO 33", "GPIO 25", "GPIO 26", "GPIO 27",
               "GPIO 14", "GPIO 12", "GPIO 13", "GND", "VIN")
_ESP32_RIGHT = ("GPIO 23", "GPIO 22", "GPIO 1", "GPIO 3", "GPIO 21", "GPIO 19", "GPIO 18", "GPIO 5", "GPIO 17",
                "GPIO 16", "GPIO 4", "GPIO 2", "GPIO 15", "GND 2", "3V3")
_CP2102, _CH340, _CH9102, _ESP_USB = (0x10C4, 0xEA60), (0x1A86, 0x7523), (0x1A86, 0x55D4), (0x303A, 0x1001)
_ARDUINO_VIDS = ((0x2341, None), (0x2A03, None))  # Arduino's own USB chips (the Mega's ATmega16U2), any product
_FTDI = (0x0403, 0x6001)  # older Nanos

ESP32 = Board("esp32dev", "ESP32 dev board (30-pin DevKit)", "the ESP32", "esp32", "espressif32", "esp32dev", 115200,
              "3V3", 3.3, 4095, _ESP32_LEFT, _ESP32_RIGHT, ("3V3", "VIN"),
              input_only=frozenset({"GPIO 34", "GPIO 35", "GPIO 36", "GPIO 39"}),
              serial=frozenset({"GPIO 1", "GPIO 3"}), usb=frozenset({_CP2102, _CH340, _CH9102, _ESP_USB}),
              printed={"GPIO 36": "VP", "GPIO 39": "VN", "GPIO 1": "TX0", "GPIO 3": "RX0", "GPIO 17": "TX2",
                       "GPIO 16": "RX2"})

# The Arduino's pins, as both boards print them; the Mega's 14 to 53 and A8 to A15 aren't used by the labs or drawn.
# SDA and SCL: the Mega's own I2C header (D20, D21); on the Nano I2C is A4 and A5.
_ARDUINO = tuple(f"D{n}" for n in range(14)) + tuple(f"A{n}" for n in range(8)) + ("5V", "3V3", "VIN", "GND",
                                                                                   "GND 2", "RST", "AREF", "SDA",
                                                                                   "SCL")
MEGA = Board("mega", "Arduino Mega 2560 (ELEGOO MEGA R3)", "the Mega", "arduino", "atmelavr", "megaatmega2560", 9600,
             "5V", 5.0, 1023,
             ("RST", "3V3", "5V", "GND", "GND 2", "VIN", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7"),
             tuple(f"D{n}" for n in range(13, -1, -1)) + ("AREF", "SDA", "SCL"), ("5V", "3V3", "VIN"),
             serial=frozenset({"D0", "D1"}), usb=frozenset({*_ARDUINO_VIDS, _CH340, _FTDI}),
             printed={"D0": "D0 RX0", "D1": "D1 TX0"})
# The classic Nano's two rows, USB at the top: D13's side, then D12's.
NANO = Board("nano", "Arduino Nano (ATmega328P, old bootloader)", "the Nano", "arduino", "atmelavr", "nanoatmega328",
             9600, "5V", 5.0, 1023,
             ("D13", "3V3", "AREF", "A0", "A1", "A2", "A3", "A4", "A5", "A6", "A7", "5V", "RST", "GND", "VIN"),
             ("D12", "D11", "D10", "D9", "D8", "D7", "D6", "D5", "D4", "D3", "D2", "GND 2", "D0", "D1"),
             ("5V", "3V3", "VIN"), input_only=frozenset({"A6", "A7"}), serial=frozenset({"D0", "D1"}),
             usb=frozenset({_CH340, _FTDI, *_ARDUINO_VIDS}), printed={"D0": "RX0", "D1": "TX1"})
NANO_NEW = Board("nano_new", "Arduino Nano (ATmega328P, new bootloader)", "the Nano", "arduino", "atmelavr",
                 "nanoatmega328new", 9600, "5V", 5.0, 1023, NANO.left, NANO.right, NANO.supplies,
                 input_only=NANO.input_only, serial=NANO.serial, usb=NANO.usb, printed=NANO.printed)

BOARDS = {b.id: b for b in (ESP32, MEGA, NANO, NANO_NEW)}
FAMILY_PINS = {"esp32": _ESP32_LEFT + _ESP32_RIGHT, "arduino": _ARDUINO}
# The board each course runs on unless he says another (his kit's Mega for the Arduino course).
COURSE_BOARDS = {"esp32": ("esp32dev",), "arduino": ("mega", "nano", "nano_new")}


def board_for(course: str, board_id: str = "") -> Board:
    """The board a course runs on: the one named if the course takes it, else its first. KeyError for a course with
    no board."""
    choices = COURSE_BOARDS[course]
    return BOARDS[board_id] if board_id in choices else BOARDS[choices[0]]


def named_in(words: str, course: str) -> Optional[str]:
    """Pure logic. The board his words name for a course ("my nano", "the mega"), or None."""
    said = f" {str(words or '').lower()} "
    if course != "arduino":
        return None
    if " nano" in said:
        return "nano_new" if "new bootloader" in said else "nano"
    if " mega" in said:
        return "mega"
    return None
