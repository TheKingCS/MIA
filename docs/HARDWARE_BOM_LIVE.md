# MIA Homestead — Live Hardware BOM

**Auto-generated 2026-08-31T15:38:21.604032Z from `hardware_requirements` — never hand-edit this file, it will be overwritten every startup.**

For pricing research/sourcing notes (not auto-derivable), see `docs/HARDWARE_BOM_CURRENT.md`.

```
== ACTUATOR ==
  3x 4-channel relay module (5V, optocoupler-isolated) — ~$24.00  (needed by: device_registry)
  1x Alert beacon (light + speaker/buzzer combo) — ~$20.00  (needed by: greenhouse_self_preservation)
  6x Peristaltic dosing pump — ~$72.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Submersible aquarium air pump + airstone — ~$20.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Submersible circulation pump — ~$30.00  (needed by: cell_a_aquaponics,pilot_cell)

== MCU ==
  1x MCU (Fertilizer / Nutrient Dosing Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (Watering Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (pH Dosing Controller) — ~$20.00  (needed by: device_registry)

== POWER ==
  1x 12V DC power supply (2-3A) — ~$12.00  (needed by: device_registry)
  1x Battery bank (LiFePO4 recommended)  (needed by: greenhouse_power)
  1x Solar charge controller (Modbus/RS485 telemetry) — ~$140.00  (needed by: greenhouse_power)

== SENSOR ==
  2x Atlas Scientific EC kit (EC-KIT-1.0 or equivalent — circuit + probe) — ~$460.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Atlas Scientific pH kit (KIT-101P or equivalent — circuit + probe) — ~$350.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x DS18B20 waterproof temp probe — ~$16.00  (needed by: cell_a_aquaponics,pilot_cell)
  1x PIR motion sensor — ~$5.00  (needed by: greenhouse_self_preservation)

Estimated total: ~$1209.00
```
