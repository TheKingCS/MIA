"""Slicing for his printer (core/slicing.py): the printer read from Bambu Studio's settings, its stock profiles
found, the print time and grams read from the G-code's header, a slice run through Bambu's command line (a stand-in
here: never the real program in a test), and plain words when Bambu or a profile isn't there.
Bambu's printer names map to their profiles, another nozzle is refused, and print times add up."""

from pathlib import Path

from core import slicing

HEADER = """; HEADER_BLOCK_START
; model printing time: 40m 22s; total estimated time: 40m 23s
; total filament length [mm] : 8968.75
; total filament weight [g] : 0.00
"""


def test_the_printer_and_its_profiles_are_found(tmp_path):
    assert slicing.printer('{"presets": {"machine": "Bambu Lab P1P 0.4 nozzle"}}') == "Bambu Lab P1P 0.4 nozzle"
    root = tmp_path / "BBL"
    for sub, name in (("machine", "Bambu Lab P1P 0.4 nozzle"), ("process", "0.20mm Standard @BBL P1P"),
                      ("filament", "Bambu PLA Basic @BBL X1C")):
        (root / sub).mkdir(parents=True, exist_ok=True)
        (root / sub / f"{name}.json").write_text("{}")
    found = slicing.profiles("Bambu Lab P1P 0.4 nozzle", root)
    assert found["model"] == "P1P" and found["filament"].name == "Bambu PLA Basic @BBL X1C.json"
    assert slicing.profiles("Prusa MK4", root) is None


def test_the_time_and_grams_are_read_from_the_gcode():
    assert slicing.read_gcode_header(HEADER) == {"time": "40m 23s", "length_mm": 8968.75, "grams": 27}


def test_a_slice_through_bambus_command_line_part_by_part(tmp_path, monkeypatch):
    exe = tmp_path / "Bambu Studio" / "bambu-studio.exe"
    root = exe.parent / "resources" / "profiles" / "BBL"
    for sub, name in (("machine", "Bambu Lab P1P 0.4 nozzle"), ("process", "0.20mm Standard @BBL P1P"),
                      ("filament", "Bambu PLA Basic @BBL P1P")):
        (root / sub).mkdir(parents=True, exist_ok=True)
        (root / sub / f"{name}.json").write_text("{}")
    conf = tmp_path / "BambuStudio.conf"
    conf.write_text('{"presets": {"machine": "Bambu Lab P1P 0.4 nozzle"}}')
    monkeypatch.setattr(slicing, "_exe", lambda: exe)
    monkeypatch.setattr(slicing, "_settings_file", lambda: conf)
    part = tmp_path / "box.stl"
    part.write_bytes(b"x")
    ran = []

    def fake(args, cwd):
        """Bambu's stand-in: writes the G-code it would."""
        ran.append(args)
        out = Path(args[args.index("--outputdir") + 1])
        out.mkdir(parents=True)
        (out / "plate_1.gcode").write_text(HEADER)
        return 0

    said = slicing.slice_files([part], "box", run=fake)
    assert "Sliced for your Bambu Lab P1P 0.4 nozzle" in said and "about 40m to print" in said and "about 27 g" in said
    assert ran[0][1:3] == ["--slice", "0"] and ran[0][-1] == "box.stl"


def test_without_bambu_it_says_so(monkeypatch, tmp_path):
    monkeypatch.setattr(slicing, "_exe", lambda: None)
    assert "Bambu Studio isn't installed" in slicing.slice_files([tmp_path / "a.stl"], "a")


def test_review_bambus_names_map_to_their_profiles_and_another_nozzle_is_refused(tmp_path):
    root = tmp_path / "BBL"
    for sub, name in (("machine", "Bambu Lab X1 Carbon 0.4 nozzle"), ("process", "0.20mm Standard @BBL X1C"),
                      ("filament", "Bambu PLA Basic @BBL X1C"), ("machine", "Bambu Lab P1S 0.4 nozzle"),
                      ("process", "0.20mm Standard @BBL P1P")):
        (root / sub).mkdir(parents=True, exist_ok=True)
        (root / sub / f"{name}.json").write_text("{}")
    assert slicing.profiles("Bambu Lab X1 Carbon 0.4 nozzle", root)["model"] == "X1C"
    assert slicing.profiles("Bambu Lab P1S 0.4 nozzle", root)["model"] == "P1P"
    assert slicing.profiles("Bambu Lab X1 Carbon 0.6 nozzle", root) is None
    assert slicing.to_seconds("1h 2m 3s") == 3723 and slicing.said_time(3440) == "57m"
