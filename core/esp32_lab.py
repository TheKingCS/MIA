"""
core.esp32_lab
================

The lab bench for Build With ESP32 (core/esp32_path.py; the standard is docs/future/INTERACTIVE_LABS_PLAN.md): MIA
builds a lab's sketch, flashes it to his board on his yes, and reads what the board says to check the lab.

- **The project** (`project`): each lab a PlatformIO project in his labs folder (`LAB_DIR/<lab>`): platformio.ini for
  the `esp32dev` board with the lab's libraries, and src/main.cpp the lab's sketch. A lab on Wi-Fi gets src/secrets.h
  with placeholders for him to fill in himself (`needs_secrets`): MIA never types a password, and won't flash until
  he has.
- **The board** (`board`): the ESP32's serial port, found as the greenhouse's provisioning finds it
  (core/greenhouse_provision.serial_ports, likely_mcu), and PlatformIO, or what's missing.
- **Flashing** (the action `esplab.flash`, approved by him: it writes to the board; another flash undoes it): builds
  and uploads with `pio run -t upload`.
- **Reading and checking** (`read_serial`, `check`): the board's serial output for a few seconds (opening the port
  restarts most dev boards, so a sketch's first lines come again), each of the lab's checks judged from it
  (core/esp32_path.judge through core/paths.verify) and kept as an attempt on his path.

Tools: `flash_lab` ("flash the blink lab": the approval card), `check_lab` ("check my lab"), `lab_board` ("is my
board plugged in?"). With no lab named, the next one on his path.
The course page (web/course.html) reads the board through `read_and_check` (each check's result and what the board
said), and `checks_of` gives a lab's checks.
Any board course (2026-11-25): Build With Arduino too, on his Mega or a Nano (core/arduino_path.py, core/boards.py);
`labs_of` gives a course's labs, `course_in` the course his words mean, and every step above takes the course and
the board.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from core.actions import ACTION_TYPES, ActionError, ActionType
from core.data_root import DATA_DIR
from core.logger import get_logger

log = get_logger(__name__)

LAB_DIR = DATA_DIR / "labs" / "esp32"
LABS_ROOT = DATA_DIR / "labs"  # each course's labs in its own folder: labs/esp32, labs/arduino
BAUD = 115200
READ_SECONDS = 8
# Labs whose markers come slower than a read of READ_SECONDS sees: a wake every 10 seconds, a browser's request.
READ_FOR = {"sleep": 25, "web": 20}
FLASH_TIMEOUT = 600
PLACEHOLDER = "type-yours-here"
SECRETS = f"""// Your Wi-Fi, typed by you. MIA never fills this in, and it stays on this computer.
#define WIFI_NAME "{PLACEHOLDER}"
#define WIFI_PASSWORD "{PLACEHOLDER}"
"""


def labs_of(course: str = "esp32") -> dict:
    """A course's labs (lesson id -> lab): Build With ESP32's or Build With Arduino's; {} for another."""
    if course == "arduino":
        from core.arduino_path import LABS
        return LABS
    if course == "esp32":
        from core.esp32_path import LABS
        return LABS
    return {}


def course_in(context, words: str = "", building: bool = False) -> str:
    """Pure logic, with his path. The board course his words mean: "arduino", "nano", "mega" or a lab only it has
    (the light, distance, servo or buzzer lab) is the Arduino course; "esp32" or one only that has, the ESP32's;
    else the one he's started, or building along in (`building`); else the ESP32's."""
    import re

    said = str(words or "").lower()
    if re.search(r"\b(arduino|nano|nanos|mega|elegoo|uno)\b", said):
        return "arduino"
    if re.search(r"\besp ?32\b", said):
        return "esp32"
    ard, esp = labs_of("arduino"), labs_of("esp32")
    for lab in ard:
        if lab not in esp and re.search(rf"\b{lab}\b", said):
            return "arduino"
    for lab in esp:
        if lab not in ard and re.search(rf"\b{lab}\b", said):
            return "esp32"
    book = getattr(context, "paths", None)
    started = [c for c in ("esp32", "arduino") if book is not None and book.path(c) is not None]
    if building and book is not None:
        latest = [(str((book.build_at(c) or {}).get("date", "")), c) for c in started if book.build_at(c)]
        if latest:
            return max(latest)[1]
    return started[0] if len(started) == 1 else "esp32"


def next_lab_reply(context, words: str) -> Optional[str]:
    """"What's my next Arduino lesson?", "next ESP32 lab?": the next step on that board course's path, in code (live
    check, 2026-11-25: the model, offered the learning tools, answered both in its own words), with how to build it
    along with MIA; None for other words, or a course not started."""
    import re

    from core import paths

    said = str(words or "").lower().replace("\u2019", "'")
    if not re.search(r"\b(arduino|nano|mega|esp ?32)\b", said) or not re.search(
            r"\b(?:what's|whats|what is|what are)\b.*\bnext\b.*\b(lessons?|labs?|steps?)\b|"
            r"\bnext (?:\w+ )?(?:lesson|lab)\b", said):
        return None
    course = course_in(context, said)
    book = getattr(context, "paths", None)
    program = paths.program_of(context, course)
    if book is None or program is None:
        return None
    if book.path(program.id) is None:
        return (f"You haven't started {program.name} yet: say \"start {'Arduino' if course == 'arduino' else 'ESP32'}\""
                " and how much time you have, or open it in the Classroom's Hands-on labs.")
    lesson = lesson_for(context, "", course=course)
    return (paths.next_step(book, program) + f" Say \"walk me through building the {lesson} lab\" to wire it with me, "
            "or open it on the course page.")


def ini(lab: dict, board=None) -> str:
    """Pure logic. A lab's platformio.ini for its board (core/boards.py; the ESP32 DevKit unless another is given):
    the platform, the board, the Arduino framework, the serial speed, its libraries."""
    from core.boards import ESP32

    board = board or ESP32
    libs = "".join(f"\n    {name}" for name in lab.get("libs", ()))
    return (f"[env:{board.pio_board}]\nplatform = {board.platform}\nboard = {board.pio_board}\nframework = arduino\n"
            f"monitor_speed = {board.baud}\n" + (f"lib_deps ={libs}\n" if libs else ""))


def project(lesson_id: str, base: Optional[Path] = None, course: str = "esp32", board_id: str = "") -> Path:
    """Writes the lab's PlatformIO project (platformio.ini for its board, src/main.cpp, and src/secrets.h with
    placeholders when the lab needs Wi-Fi and he hasn't made it yet) and returns its folder. ValueError for a lab the
    course hasn't."""
    from core.boards import board_for

    lab = labs_of(course).get(lesson_id)
    if lab is None:
        raise ValueError(f"There's no {lesson_id} lab in that course.")
    folder = Path(base or (LAB_DIR if course == "esp32" else LABS_ROOT / course)) / lesson_id
    (folder / "src").mkdir(parents=True, exist_ok=True)
    (folder / "platformio.ini").write_text(ini(lab, board_for(course, board_id)), encoding="utf-8")
    (folder / "src" / "main.cpp").write_text(lab["code"], encoding="utf-8")
    secrets = folder / "src" / "secrets.h"
    if lab.get("secrets") and not secrets.exists():
        secrets.write_text(SECRETS, encoding="utf-8")  # his to fill in; never overwritten once there
    return folder


def needs_secrets(folder: Path) -> bool:
    """Whether a lab's secrets.h still has the placeholders (he hasn't typed his Wi-Fi in yet)."""
    secrets = Path(folder) / "src" / "secrets.h"
    return secrets.exists() and PLACEHOLDER in secrets.read_text(encoding="utf-8")


def board(ports: Optional[list] = None, pio: Optional[list] = None, course: str = "esp32") -> dict:
    """{port, description, pio, missing} for the bench: the ESP32's port (or the only one), PlatformIO, and what's
    missing in words ("" when both are there). With more than one board plugged in, no port: he says which (the
    review, 2026-11-25: the greenhouse's MCU on the same PC could have been flashed by mistake). A course's boards
    are found by their USB chips (core/boards.py): the Arduino course's by Arduino's own, CH340 or FTDI."""
    from core import greenhouse_provision as gp

    from core.boards import BOARDS, COURSE_BOARDS

    ports = gp.serial_ports() if ports is None else ports
    kinds = [BOARDS[b] for b in COURSE_BOARDS.get(course, ("esp32dev",))]
    boards = [p for p in ports if any(k.found_by(p.get("vid"), p.get("pid")) for k in kinds)]
    found = (boards[0] if boards else (ports[0] if len(ports) == 1 else None)) if len(boards) <= 1 else None
    what = "ESP32" if course == "esp32" else "Arduino"
    pio = gp.platformio() if pio is None else pio
    missing = []
    if len(boards) > 1:
        missing.append(f"{len(boards)} boards are plugged in ({', '.join(p.get('device', '') for p in boards)}): "
                       "say which port, like COM5, so I never write to the wrong one")
    elif found is None:
        missing.append(f"no {what} on a USB port (plug it in with a data cable)" if not ports else
                       f"{len(ports)} serial ports and none is clearly an {what}: say which, like COM5")
    if not pio:
        missing.append("PlatformIO isn't installed on this PC (pip install platformio), so I can't build or flash")
    return {"port": (found or {}).get("device", ""), "description": (found or {}).get("description", ""),
            "pio": pio, "missing": "; ".join(missing)}


def lesson_for(context, words: str = "", course: str = "esp32") -> Optional[str]:
    """The lab his words name ("the relay lab" first, then its lesson's title or its id as a whole word: "pot" never
    in "spot"), else the next one on his path (the lab whose sketch prints the first open check's marker), else the
    first; None outside the course.
    In the course given (`course`: esp32 or arduino)."""
    from core import paths

    LABS = labs_of(course)
    PROGRAM = paths.program_of(context, course)
    import re

    said = str(words or "").lower()
    lessons = [lesson for stage in PROGRAM.stages for lesson in stage.lessons]
    lessons = [lesson for stage in PROGRAM.stages for lesson in stage.lessons]
    for lesson in lessons:  # "the relay lab" first, so "hello MIA, flash the relay lab" is the relay lab
        if re.search(rf"\b{re.escape(lesson.id)} lab\b", said):
            return lesson.id
    for lesson in lessons:
        if lesson.title.lower() in said or re.search(rf"\b{re.escape(lesson.id)}\b", said):
            return lesson.id
    book = getattr(context, "paths", None)
    if book is not None and book.path(PROGRAM.id) is not None:
        stage = paths.stage_of(book, PROGRAM)
        left = paths.open_checks(book, PROGRAM)
        for check in left:
            marker = f"MIA {check.about.split()[0]}"
            for lesson in stage.lessons:
                if marker in LABS[lesson.id]["code"]:
                    return lesson.id
        return stage.lessons[0].id
    return PROGRAM.stages[0].lessons[0].id


def flash(context, lesson_id: str, port: str = "", run: Optional[Callable] = None, pio: Optional[list] = None,
          base: Optional[Path] = None, course: str = "esp32", board_id: str = "") -> str:
    """Builds the lab and writes it to the board; what happened, in words. ActionError for what's missing.
    With no port and more than one board plugged in, it writes to none and says which are there.
    The project is built for the course's board he names (`course`, `board_id`; core/boards.py)."""
    from core import greenhouse_provision as gp

    folder = project(lesson_id, base, course, board_id)
    if needs_secrets(folder):
        raise ActionError(f"Type your Wi-Fi's name and password into {folder / 'src' / 'secrets.h'} first (yourself: "
                          "MIA never does), then flash it.")
    bench = board(pio=pio, course=course)
    port = port or bench["port"]
    if not bench["pio"]:
        raise ActionError("PlatformIO isn't installed on this PC (pip install platformio), so I can't build it.")
    if not port:
        raise ActionError("I can't tell which board to write to: " + (bench["missing"] or "plug it in") + ".")
    code, said = (run or gp._run)(list(bench["pio"]) + ["run", "-t", "upload", "-d", str(folder), "--upload-port",
                                                       port], FLASH_TIMEOUT)
    if code != 0:
        tail = " ".join(str(said or "").strip().splitlines()[-3:])[:300]
        raise ActionError(f"The build or the upload didn't work: {tail} (hold BOOT while it starts uploading, if it "
                          "can't connect).")
    return f"Flashed the {lesson_id} lab to the board on {port}. Say \"check my lab\" and I'll read what it says."


def read_serial(port: str, seconds: float = READ_SECONDS, opener: Optional[Callable] = None, baud: int = BAUD) -> str:
    """What the board prints over `seconds`, the port opened without toggling DTR and RTS, so the board keeps
    running (a lab's sketch says its marker in loop() for this; the sleep lab's wake count lives through deep sleep).
    "" when nothing came; OSError when the port can't be opened (in use by a monitor, or unplugged).
    At the board's speed (`baud`: 115200 for the ESP32's labs, 9600 for the Arduino's)."""
    if opener is None:
        import serial

        def opener(p):
            """The port at the labs' speed, opened with the reset lines held off, so a running board isn't
            restarted by the read."""
            link = serial.Serial()
            link.port, link.baudrate, link.timeout = p, baud, 0.5
            link.dtr = link.rts = False
            link.open()
            return link

    lines = []
    with opener(port) as link:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            raw = link.readline()
            if raw:
                lines.append(raw.decode("utf-8", errors="replace").rstrip())
    return "\n".join(lines)


def checks_of(lesson_id: str, course: str = "esp32") -> list:
    """The checks a lab's sketch prints the marker of, in its course: the marker followed by its value or the end of
    the string ("MIA DIST " counts; "MIA DIST_NONE" isn't DIST)."""
    import re

    from core import paths

    code = labs_of(course)[lesson_id]["code"]
    program = paths.program_of(None, course)
    return [c for s in program.stages for c in s.checks
            if re.search(rf"MIA {re.escape(c.about.split()[0])}[ \"]", code)]


def read_and_check(context, lesson_id: str, port: str = "", seconds: Optional[float] = None,
                   reader: Optional[Callable] = None, course: str = "esp32", board_id: str = "") -> dict:
    """Reads the board and judges each of the lab's checks from it (core/paths.verify, kept as attempts):
    {port, serial (what it said), results [{check, passed, said}], said (in words)}. For the voice (`check`) and the
    course page (web/course.html, server/app.py). How long: as asked, else the lab's own (READ_FOR), else
    READ_SECONDS. With more than one board plugged in and no port named, it reads none.
    On any board course: the Arduino's read at its own 9600 baud, judged against its course's checks."""
    from core import paths
    from core.boards import board_for

    PROGRAM = paths.program_of(context, course)
    seconds = float(seconds or (READ_FOR.get(lesson_id, READ_SECONDS) if course == "esp32" else READ_SECONDS))
    out = {"port": port, "serial": "", "results": [], "said": ""}
    book = getattr(context, "paths", None)
    if book is None:
        out["said"] = "Learning paths aren't on this MIA."
        return out
    if book.path(PROGRAM.id) is None:
        out["said"] = (f"Start {PROGRAM.name} first: say \"start {'ESP32' if course == 'esp32' else 'Arduino'}\", "
                       "and how much time you have.")
        return out
    bench = board(pio=[], course=course) if not port else {"port": port, "missing": ""}
    port = out["port"] = bench["port"]
    if not port:
        out["said"] = "I can't read the board: " + (bench["missing"].split("; ")[0] or "plug it in") + "."
        return out
    try:
        text = reader(port, seconds) if reader else read_serial(port, seconds, baud=board_for(course, board_id).baud)
    except OSError as problem:
        out["said"] = f"I couldn't open {port}: {problem}. Close any serial monitor that has it, then try again."
        return out
    out["serial"] = text
    if not text.strip():
        out["said"] = (f"The board on {port} said nothing in {seconds:g} seconds: is the {lesson_id} lab on it? "
                       "Flash it, then try again.")
        return out
    for c in checks_of(lesson_id, course):
        got = paths.verify(context, PROGRAM, c.id, {"serial": text})
        out["results"].append({"check": c.id, "passed": got["passed"], "said": got["said"]})
    out["said"] = " ".join(r["said"] for r in out["results"]) or f"The {lesson_id} lab has no check to read."
    if lesson_id == "web" and not all(r["passed"] for r in out["results"]):
        out["said"] += " Open http://<its address>/reading in a browser while I read: the address is the MIA WIFI line."
    return out


def check(context, lesson_id: str, port: str = "", seconds: Optional[float] = None,
          reader: Optional[Callable] = None, course: str = "esp32", board_id: str = "") -> str:
    """Reads the board and judges each of the lab's checks from it (`read_and_check`); in words.
    As long as the lab needs when no time is given (READ_FOR).
    On any board course (`course`: esp32 or arduino; `board_id`: the Arduino's Mega or Nano)."""
    return read_and_check(context, lesson_id, port, seconds, reader, course, board_id)["said"]


# ------------------------------------------------------------------ the action and the tools

def _describe(context, params) -> str:
    """What esplab.flash says: the lab, the board (its port named, found now when none was given; refused when more
    than one board is plugged in) and what it does.
    The card names the board too (his Mega, a Nano) for the Arduino course."""
    from core.boards import board_for

    lesson = str(params.get("lesson", "") or "").strip()
    course = str(params.get("course", "") or "esp32")
    if lesson not in labs_of(course):
        raise ActionError("Which lab? Like blink, button or dht.")
    kind = board_for(course, str(params.get("board", "") or ""))
    port = str(params.get("port", "") or "").strip()
    where = port
    if not port:
        bench = board(pio=[], course=course)
        if not bench["port"]:
            raise ActionError("Which board? " + (bench["missing"].split("; ")[0] or "Plug it in") + ".")
        where = bench["port"] + (f" ({bench['description']})" if bench["description"] else "")
    return (f"Build the {lesson} lab for your {kind.name} and write it to the board on {where}: it replaces what's on "
            "that board now.")


def _execute(context, params) -> str:
    """Does esplab.flash.
    On the card's course and board."""
    return flash(context, str(params.get("lesson", "")), str(params.get("port", "") or ""),
                 course=str(params.get("course", "") or "esp32"), board_id=str(params.get("board", "") or ""))


ACTIONS = {a.kind: a for a in (
    ActionType("esplab.flash", "Flash This Lab", {"lesson": "which lab (blink, hello, button...)",
                                                   "port": "the board's port, if not the one found",
                                                   "course": "esp32 or arduino (esp32 if not given)",
                                                   "board": "for the Arduino course: mega, nano or nano_new"},
               _describe, _execute),
)}
ACTION_TYPES.update(ACTIONS)


def _flash_tool(context, arguments: dict) -> str:
    """Tool flash_lab: the approval card for flashing a lab (the one named, else the next on his path).
    With no actions here it points to the course page.
    The card carries the port found now, so it names the board it writes to.
    The course and board come from his words ("flash the blink lab to my nano")."""
    actions = getattr(context, "actions", None)
    if actions is None:
        return "I can't put that to you from here: it's on the course page."
    from core.boards import named_in

    words = str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or "")
    course = course_in(context, words)
    lesson = lesson_for(context, words, course=course)
    try:
        port = str(arguments.get("port", "") or "") or board(pio=[], course=course)["port"]  # the card names it
        card = actions.propose(context, "esplab.flash", {"lesson": lesson, "port": port, "course": course,
                                                         "board": named_in(words, course) or ""})
    except ActionError as problem:
        return str(problem)
    return f"{card.summary}. It's waiting for your yes: press Approve, or say \"approve it\"."


def _check_tool(context, arguments: dict) -> str:
    """Tool check_lab: reads the board and checks the lab.
    On the course and board his words mean (course_in, boards.named_in)."""
    from core.boards import named_in

    words = str(arguments.get("lab", "") or "") + " " + str(arguments.get("question", "") or "")
    course = course_in(context, words)
    return check(context, lesson_for(context, words, course=course), str(arguments.get("port", "") or ""),
                 course=course, board_id=named_in(words, course) or "")


def _board_tool(context, arguments: dict) -> str:
    """Tool lab_board: the board and PlatformIO, or what's missing (an Arduino when his words say so)."""
    bench = board(course=course_in(context, str(arguments.get("question", "") or "")))
    if bench["missing"]:
        return "For the labs: " + bench["missing"] + "."
    return f"Your ESP32 is on {bench['port']} ({bench['description']}), and PlatformIO is ready."


def register_esp32_lab_actions(registry) -> None:
    """Registers flash_lab, check_lab and lab_board, the simulator's build_along and simulate_lab
    (core/esp32_sim.py), and "esp32" and "microcontroller" as learning words (so "what's my next ESP32 lesson?"
    brings the learning tools: the live check, 2026-11-25).
    "arduino" is a learning word too, and "is my arduino plugged in?" reaches lab_board."""
    from core.assistant_actions import AssistantAction
    from core.esp32_sim import register_sim_tools

    registry.register_domain_keywords("learning", ("esp32", "microcontroller", "breadboard", "arduino"))
    register_sim_tools(registry)
    lab = {"type": "string", "description": "which lab (blink, hello, button, pot, dht, soil, fade, relay, wifi, "
                                            "web, sleep), only if he named one"}
    words = {"type": "string", "description": "his words"}
    registry.register(AssistantAction(
        name="flash_lab", domain="learning",
        description="Flash (upload) one ESP32 lab's sketch onto his board, after his yes, only when he asks to flash "
                    "or upload: \"flash the blink lab\". His next lesson is learning_lesson, what to practise "
                    "practice_today, and starting the course start_learning: never this.",
        parameters={"type": "object", "properties": {"lab": lab, "port": {"type": "string", "description":
                                                                          "the port, only if he said"},
                                                     "question": words}, "required": []},
        handler=_flash_tool, trigger_phrases=("flash the", "flash my", "upload the", "flash it to the board",
                                             "put the lab on", "lab on my board"),
    ))
    registry.register(AssistantAction(
        name="check_lab", domain="learning",
        description="Check his lab on the real ESP32 now: reads its serial output for a few seconds and says whether "
                    "the check passed, and why. What a lab will or should print is simulate_lab, not this.",
        parameters={"type": "object", "properties": {"lab": lab, "question": words}, "required": []},
        handler=_check_tool, trigger_phrases=("check my lab", "check the lab", "did my lab pass", "did it pass",
                                             "read my board", "what's my board saying", "check my board"),
    ))
    registry.register(AssistantAction(
        name="lab_board", domain="learning",
        description="Whether his ESP32 is plugged in (and on which port) and PlatformIO is ready for the labs.",
        parameters={"type": "object", "properties": {"question": words}, "required": []}, prompt_arg="question",
        handler=_board_tool, trigger_phrases=("board plugged in", "see my board", "see my esp32", "esp32 plugged",
                                             "arduino plugged", "nano plugged", "mega plugged", "see my arduino",
                                             "which port is my", "is platformio"),
    ))
