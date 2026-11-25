# Interactive labs: the standard for teaching in MIA

*Zac, 2026-11-25: "I just found this program called esp-labs-web.vercel.app. It is an interactive environment made
for learning how to build with esp32's. I would love something like this for MIA and this could be used as a
standard for other teaching areas." (The site itself was paused when checked, so this is built from what he
described, on MIA's own learning paths.)*

## What a lab is

A **lab** is a lesson you do with your hands, that MIA checks from evidence, never from the model's say-so. Every
teaching area in MIA uses the same seven parts, on the learning paths she already has (core/paths.py: stages,
lessons, checks, practice log, weekly homework missions, stats):

| Part | What it is | ESP32 | Guitar | Carpentry |
|---|---|---|---|---|
| **Goal** | one thing you'll be able to do after | blink an LED | play Em to G | cut to 1/16 in |
| **Parts** | what's on the bench | board, cable, LED | guitar, tuner | saw, square, tape |
| **Setup** | the wiring, the hold, the layout | pin to pin | chord shapes | the cut line |
| **Do it** | the steps, in order | flash the sketch | play the change | make the cut |
| **See it** | what you watch while you do it | the serial monitor | MIA listening | the mark and the kerf |
| **Check** | MIA verifies from evidence | the board's own `MIA` lines | the recording's notes | a measurement or photo |
| **Try this** | a change that teaches the why | delay 100 | a slower tempo | a different blade |

A check is passed **by evidence** (the path's verifiers: what the board printed, what MIA heard, a number from his
records, a measurement he gives), and each pass is an attempt on his path, XP to its skill, and the next stage when
the stage's checks are done. Safety lines live in the lessons, written in code, never left to the model.

## The first: Build With ESP32 (built 2026-11-25)

`core/esp32_path.py`, a learning path of six stages: First light (blink, serial), Inputs (a button, a pot), Sensors
(DHT22, soil moisture), Outputs (PWM, a relay, low voltage only), Connected (Wi-Fi, a little web server), A real node
(deep sleep). Each lab has its parts, its wiring pin to pin, its libraries and an Arduino sketch for PlatformIO's
`esp32dev`; every sketch prints `MIA <MARKER> <value>` lines, and the check (`board_says`) passes from what the board
itself said: a marker seen, a value at least a mark, readings spread apart (a pot turned end to end, soil dry then
wet), or a value in a range (a room's temperature). Wi-Fi details are his to type into the sketch's own secrets file,
never MIA's.

## The steps after

1. **The lab bench, in code**: *built 2026-11-25 (core/esp32_lab.py).* A lab is a PlatformIO project in his labs
   folder (its libraries, its sketch, a Wi-Fi secrets file with placeholders only he fills in); "flash the blink lab"
   is an approval card (`esplab.flash`: it writes to the board), "check my lab" reads the board's serial port for a
   few seconds and judges the lab's checks from what it said, and "is my ESP32 plugged in?" says the port and whether
   PlatformIO is installed. On this PC PlatformIO isn't installed yet (`pip install platformio`, his call).
2. **The lab page**: *built 2026-11-25 (web/course.html, core/lab_page.py; Classroom > Hands-on labs).* The
   course map (stages done, current and later, each lab, each check passed or not), the lab chosen (why, steps,
   what to watch for, parts, wiring, the sketch and platformio.ini to copy), Start This Course (`path.start`), Flash
   This Lab (`esplab.flash`, approved), and the serial monitor: Read The Board reads it for a few seconds
   (POST /api/labs/{course}/read) and checks the lab from what it said. `page()` is course-neutral: another area
   gives its labs in `_labs()` and its own "see it" panel (the guitar's ear, a photo) in place of the bench.
3. **Simulated, with no board** (his say: it needs an online simulator or a local one to be chosen): a lab run in a
   simulator when the board isn't on the desk.
4. **The other areas on the same frame**: guitar (already verified by ear), carpentry and woodworking (a
   measurement, a photo), gardening (his own logged readings), bushcraft and first aid (a said check, a photo).
5. **His own labs**: the greenhouse node's firmware as the capstone, and labs drafted for a new interest
   (core/paths.draft) in the same seven parts.
