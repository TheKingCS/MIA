"""
core.web_field_kit
====================

The Field Kit's web screen (DEC-0113 canvas Field Kit, DEC-0125: the Field
Kit had no phone screen). Three tabs, to look at from anywhere; doing things
to the computer stays on the PC:

- **Devices**: the external storage and USB serial boards plugged into the
  computer MIA runs on (core/device_framework.py), with their size, where
  they're mounted and what board they are. Ejecting and flashing stay on the
  PC, beside the device.
- **Network**: the checks that need nothing but the words typed: what kind
  of hash a value is (core/hash_identifier.py) and a subnet worked out from
  its CIDR (core/subnet_calculator.py), answered by check(). The port scan
  runs on the PC (it holds a connection open to each port).
- **Scripts**: the script library (core/script_library_manager.py) by
  category, each one's content to read and copy. Running a script stays on
  the PC, where its output can be watched and stopped.
"""

from __future__ import annotations

from core.logger import get_logger

log = get_logger(__name__)

MAX_SCRIPT_CHARS = 20000  # a script longer than this is cut, with a note, on the web


def _devices(context) -> dict:
    """The devices plugged in now: storage (name, size, mounted where, file system, transport) and serial boards
    (port, what board, description); available False when this MIA can't look."""
    framework = getattr(context, "devices", None)
    if framework is None:
        return {"available": False, "storage": [], "serial": []}
    try:
        storage = framework.list_block_devices()
        serial = framework.list_serial_devices()
    except Exception:
        log.exception("Field Kit: device listing failed")
        return {"available": False, "storage": [], "serial": []}
    return {"available": True,
            "storage": [{"name": d.display_name, "disk": d.name, "size": d.size, "mounted": d.mountpoint or "",
                         "fstype": d.fstype or "", "via": (d.tran or "").upper()} for d in storage],
            "serial": [{"name": d.display_name, "port": d.device, "board": d.identified_as or "",
                        "description": d.description} for d in serial]}


def _scripts(context) -> list:
    """The script library, by category then name: each with its interpreter, how many lines, and its content."""
    library = getattr(context, "scripts", None)
    if library is None:
        return []
    try:
        scripts = library.all_scripts()
    except Exception:
        log.exception("Field Kit: script library read failed")
        return []
    out = []
    for s in sorted(scripts, key=lambda s: ((s.category or "~").lower(), s.name.lower())):
        content = s.content or ""
        out.append({"id": s.script_id, "name": s.name, "interpreter": s.interpreter, "category": s.category or "Other",
                    "lines": len(content.splitlines()), "content": content[:MAX_SCRIPT_CHARS],
                    "cut": len(content) > MAX_SCRIPT_CHARS, "updated": (s.updated_at or s.created_at or "")[:10]})
    return out


def check(tool: str, value: str) -> dict:
    """Pure logic. One network check on what was typed: "hash" (the kinds it may be) or "subnet" (the subnet worked
    out). {answer, lines (label, value) pairs} or {error} in plain words; never raises."""
    from core.hash_identifier import identify_hash
    from core.subnet_calculator import calculate_subnet

    value = (value or "").strip()
    if not value:
        return {"error": "Type something to check."}
    if tool == "hash":
        kinds = identify_hash(value)
        if not kinds:
            return {"error": "That doesn't look like a hash MIA knows."}
        return {"answer": kinds[0] if len(kinds) == 1 else f"One of {len(kinds)} kinds",
                "lines": [["Could be", k] for k in kinds]}
    if tool == "subnet":
        try:
            s = calculate_subnet(value)
        except ValueError:
            return {"error": "Give an IPv4 network like 192.168.1.0/24."}
        return {"answer": f"{s.usable_host_count:,} usable hosts",
                "lines": [["Network", f"{s.network_address}/{s.prefix_length}"], ["Netmask", s.netmask],
                          ["Broadcast", s.broadcast_address],
                          ["First usable", s.first_usable or "none"], ["Last usable", s.last_usable or "none"],
                          ["Addresses", f"{s.total_addresses:,}"]]}
    return {"error": "There's no check by that name."}


def field_kit_page(context) -> dict:
    """The Field Kit screen's data: the devices plugged in, the network checks offered, and the script library."""
    scripts = _scripts(context)
    return {"available": True, "devices": _devices(context), "scripts": scripts,
            "categories": sorted({s["category"] for s in scripts}),
            "checks": [{"id": "hash", "name": "What Hash Is This?", "placeholder": "Paste a hash",
                        "about": "Tells a hash's kind from its prefix or length."},
                       {"id": "subnet", "name": "Subnet", "placeholder": "192.168.1.0/24",
                        "about": "The network, netmask, broadcast and usable range of a CIDR."}],
            "on_pc": ["Ejecting or flashing a drive", "Running a script", "The port scan", "Password strength"]}
