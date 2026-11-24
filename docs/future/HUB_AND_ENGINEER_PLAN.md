# MIA as the hub and the engineer

*Zac, 2026-11-24: "Think of MIA as the Jarvis that connects to my wifi enabled tools, my workshop, my greenhouse, my
sensors, my devices, me and is capable of organizing and proposing and automating efficient use of the life around
me. She will be a part of the smart greenhouse, a part of the smart workshop, a part of the property management, one
intelligence integrated with my homestead, my work, my life. I want MIA to be able to help me design the devices too,
be able to act as my software engineer, hardware design, 3d printing assistant, PCB printer, etc. This will be an
eventual business route: selling smart ag tech and smart homestead tech and built out smart structures like
greenhouses, coops, feeders, well pumps, power stations, buildings, garages etc."*

Two halves: MIA connected to everything around him (the hub), and MIA designing the things that get connected (the
engineer). Both start from what's built (mapped 2026-11-24) and keep the rules already decided.

## The rules that stay

- **Every change to a device is an action on the one contract** (DEC-0213, DEC-0248). Authority comes only from him:
  a tier in the app's manifest, a grant he gave, or his yes on the card. Nothing she reads, from a device, a web page
  or a datasheet, can grant her anything (DEC-0249).
- **Physical safety lives in hardware** (DEC-0254). A controller and its safety MCU enforce their own limits and may
  refuse. MIA directs and the device confirms (DEC-0185, DEC-0246).
- **Local first.** She talks to his devices on his own network (as the cameras, sensors and port scanner already do),
  never through someone else's cloud unless he says so for one device (DEC-0207).
- **Code only through the lab** (DEC-0058, DEC-0225): a separate worktree, tests before and after, his approval to
  merge. Electrical and structural designs are drafts for a qualified person to check (Q-57).

## Part 1: the hub (devices around him)

**What's there.**
- Sensors post readings over HTTP, each with its own key (`core/sensors.py`).
- Cameras on his network give still frames (`core/security_cams.py`).
- Phones and glasses are paired (`core/home_link.py`, `core/linked_devices.py`).
- The greenhouse node is read and provisioned (`core/greenhouse_link.py`, `core/greenhouse_provision.py`).
- USB and serial boards are detected (`core/device_framework.py`).
- `scan_ports` works only on his own network.
- A workshop machine interface exists, with only a stub laser (`core/workshop_machine.py`).

**Not there.** Discovery (mDNS, SSDP, ARP, BLE), MQTT, Home Assistant, ESPHome or Tasmota, and Modbus.

**The steps, in order:**

1. **Know what's on the network (read-only).** The device fabric's first layer (DEC-0128, proposed): discover with mDNS,
   SSDP and ARP, then name each device by make and model. This gives "what's on my network?" with nothing changed.
2. **Hear what devices say.** An MQTT listener and ESPHome/Tasmota (the open, local protocols most DIY ag hardware
   speaks) feed the data logger as sensors do. Each device is added once, by him.
3. **Speak to them, gated.** Switching a plug, setting a pump schedule or starting a print becomes an action kind,
   tiered per device, with every command confirmed by the device's read-back. The greenhouse's command interface (the
   smart-ag plan's phase B) is the first and most careful case.
4. **The smart workshop.** The machine interface gets real drivers. The 3D printer comes first, through
   OctoPrint/Moonraker/Klipper's local API (status, start, pause, the camera). Then the laser and CNC (GRBL), and the
   tools' hours and upkeep join Maintenance.
5. **Organise and propose.** With the above in place, the unified layer's ripples and the communication gate propose
   efficient use: run the well pump on solar hours, print overnight on cheap power, top up the cistern before a dry
   week. Each runs only as he set it (his grant or his yes).

## Part 2: the engineer (designing the devices)

**What's there.**
- About 40 engineering calculators (`core/eng_calcs.py`), the electrical and embedded ones with a check-with-a-pro
  caveat.
- A bench that measures a model's engineering (`core/eng_bench.py`).
- Specialists: maker, embedded, electrical, power and engineering.
- The lab where code is written and tested (`core/dev_lab.py`, `core/mia_coder.py`).
- PlatformIO firmware builds (the greenhouse MCU).
- The parts database (`core/component_manager.py`).

**Not there.** CAD, slicing, PCB tools, circuit simulation and product BOMs.

**The steps, in order:**

1. **Firmware.** MIA writes, builds and flashes ESP32 firmware for a device through PlatformIO (already proven on the
   greenhouse MCU), in the lab, with his approval to flash.
2. **3D printing.** *First piece built 2026-11-24 (`core/print_parts.py`: enclosures and spacers as STL files from
   his sizes, made in code with no CAD program; holes and slicing are next).* Parametric parts in OpenSCAD or CadQuery: a sensor enclosure, a feeder part, a pump bracket. The
   model writes the script, code renders the STL and checks its size, and a slicer (PrusaSlicer or OrcaSlicer, run
   offline) makes the G-code with time and filament. "Print it" sends it to the printer as an action.
3. **PCBs.** KiCad's command line checks a schematic's rules and exports Gerbers, a BOM priced against his parts
   database, and the order pack for a board house. Ordering waits for his press. The model drafts and KiCad checks;
   nothing reaches a fab unchecked.
4. **Structures.** The plans shelf already builds greenhouses, coops and sheds at his size (`core/build_calcs.py`). The
   smart versions add the device kit: which sensors, controller and wiring, from the design steps above.

## Part 3: the business route (later; his say)

Each product he designs is a Library plan plus a device kit plus firmware. The workshop's quotes, orders, real hourly
and pricing already exist, so a product's cost, price and margin come from them. What he'd sell (kits, built
structures, installs) and where are his decisions, as are certifications for electrical products sold to others.

## Decisions for Zac (WAITING_ON 0zq to 0zs)

- **The device fabric** (DEC-0128, proposed): may MIA discover what's on his network (read-only, his network only)?
  Recommended: yes, read-only first.
- **His devices and printer.** Which 3D printer, smart plugs, and which ESP32 or Tasmota devices he has or will buy.
  Recommended: printers with a local API (Klipper/Moonraker, OctoPrint, or Bambu in LAN mode), and devices that speak
  MQTT or ESPHome locally.
- **The order.** Recommended: discovery and MQTT listening first (they read only), the 3D printer second, firmware and
  OpenSCAD parts third, PCBs after. The alternative is to start with design (CAD and firmware) before connecting
  anything.
