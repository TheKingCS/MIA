"""The Field Kit on the web (DEC-0125, the design canvas's Field Kit, DEC-0113: core/web_field_kit.py): what's plugged
into the computer, a hash's kind and a subnet worked out in core, and the script library to read and copy; doing
things to the computer stays on the PC."""

from __future__ import annotations

from types import SimpleNamespace as N

from core.web_field_kit import MAX_SCRIPT_CHARS, check, field_kit_page


def script(sid, name, category, content):
    """A saved script, as the library keeps it."""
    return N(script_id=sid, name=name, interpreter="shell", category=category, content=content,
             created_at="2026-10-01T10:00:00", updated_at="")


def test_a_hash_and_a_subnet_are_checked_in_plain_words():
    assert check("hash", "5f4dcc3b5aa765d61d8327deb882cf99") == {"answer": "One of 2 kinds",
                                                                 "lines": [["Could be", "MD5"], ["Could be", "NTLM"]]}
    assert check("hash", "$2b$12$abcdef")["answer"] == "bcrypt"
    assert check("hash", "hello") == {"error": "That doesn't look like a hash MIA knows."}
    s = check("subnet", "192.168.1.0/24")
    assert s["answer"] == "254 usable hosts" and ["Broadcast", "192.168.1.255"] in s["lines"]
    assert check("subnet", "not a network")["error"] and check("subnet", " ") == {"error": "Type something to check."}
    assert check("ports", "x") == {"error": "There's no check by that name."}


def test_the_page_lists_devices_and_scripts_by_category():
    devices = N(list_block_devices=lambda: [N(display_name="Stick (8G)", name="sdb", size="8G", mountpoint=None,
                                              fstype="vfat", tran="usb")],
                list_serial_devices=lambda: [N(display_name="ESP32 (/dev/ttyUSB0)", device="/dev/ttyUSB0",
                                               identified_as="ESP32", description="CP2102")])
    library = N(all_scripts=lambda: [script("b", "Zip logs", "", "tar czf logs.tgz logs\n"),
                                     script("a", "Back up", "Backups", "x" * (MAX_SCRIPT_CHARS + 5))])
    page = field_kit_page(N(devices=devices, scripts=library))
    assert page["devices"]["storage"][0] == {"name": "Stick (8G)", "disk": "sdb", "size": "8G", "mounted": "",
                                             "fstype": "vfat", "via": "USB"}
    assert page["devices"]["serial"][0]["board"] == "ESP32"
    assert [(s["name"], s["category"]) for s in page["scripts"]] == [("Back up", "Backups"), ("Zip logs", "Other")]
    assert page["scripts"][0]["cut"] and len(page["scripts"][0]["content"]) == MAX_SCRIPT_CHARS
    assert page["categories"] == ["Backups", "Other"] and {c["id"] for c in page["checks"]} == {"hash", "subnet"}


def test_without_a_device_framework_or_scripts_it_still_draws():
    page = field_kit_page(N())
    assert page["devices"] == {"available": False, "storage": [], "serial": []} and page["scripts"] == []
    broken = N(devices=N(list_block_devices=lambda: 1 / 0, list_serial_devices=lambda: []))
    assert field_kit_page(broken)["devices"]["available"] is False
