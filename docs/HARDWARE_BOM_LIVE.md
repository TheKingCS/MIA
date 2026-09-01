# MIA Homestead — Live Hardware BOM

**Auto-generated 2026-09-01T07:09:24.368414Z from `hardware_requirements` — never hand-edit this file, it will be overwritten every startup.**

For pricing research/sourcing notes (not auto-derivable), see `docs/HARDWARE_BOM_CURRENT.md`.

```
== ACTUATOR ==
  1x 12V solenoid irrigation valve, normally closed — ~$15.00  (needed by: irrigation_scheduler)
  1x 24" shutter-mount exhaust fan, 115V — ~$159.99  (needed by: cell_a_climate)
  5x 4-channel relay module (5V, optocoupler-isolated) — ~$40.00  (needed by: device_registry)
  1x Alert beacon (light + speaker/buzzer combo) — ~$20.00  (needed by: greenhouse_self_preservation)
  1x CO2 injector / regulator valve (solenoid, food-safe) — ~$35.00  (needed by: cell_a_climate)
  6x Peristaltic dosing pump — ~$72.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Submersible aquarium air pump + airstone — ~$20.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Submersible aquarium heater, relay-controlled — ~$50.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Submersible circulation pump — ~$30.00  (needed by: cell_a_aquaponics,pilot_cell)
  1x Supplemental grow light fixture (relay-switched) — ~$40.00  (needed by: cell_a_climate)
  1x Thermostatic propane greenhouse heater, 30,000-60,000 BTU — ~$275.00  (needed by: cell_a_climate)

== MCU ==
  1x MCU (Climate Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (Fertilizer / Nutrient Dosing Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (Tank Water Heater Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (Watering Controller) — ~$20.00  (needed by: device_registry)
  1x MCU (pH Dosing Controller) — ~$20.00  (needed by: device_registry)

== OTHER ==
  1x API Freshwater Master Test Kit (or equivalent liquid ammonia/nitrite/nitrate/pH test kit) — ~$38.99  (needed by: biofilter_model)

== POWER ==
  1x 12V DC power supply (2-3A) — ~$12.00  (needed by: device_registry)
  1x Battery bank (LiFePO4 recommended)  (needed by: greenhouse_power)
  1x Solar charge controller (Modbus/RS485 telemetry) — ~$140.00  (needed by: greenhouse_power)

== SENSOR ==
  2x Atlas Scientific Dissolved Oxygen kit (circuit + probe) — ~$709.98  (needed by: cell_a_aquaponics,pilot_cell)
  2x Atlas Scientific EC kit (EC-KIT-1.0 or equivalent — circuit + probe) — ~$460.00  (needed by: cell_a_aquaponics,pilot_cell)
  2x Atlas Scientific pH kit (KIT-101P or equivalent — circuit + probe) — ~$350.00  (needed by: cell_a_aquaponics,pilot_cell)
  1x CO2 sensor (NDIR, e.g. MH-Z19) — ~$25.00  (needed by: cell_a_climate)
  1x DHT22 / AM2302 air temp + humidity sensor — ~$15.00  (needed by: cell_a_climate)
  2x DS18B20 waterproof temp probe — ~$16.00  (needed by: cell_a_aquaponics,pilot_cell)
  1x Inline water flow sensor (hall-effect, e.g. YF-S201 class) — ~$10.00  (needed by: circulation_monitor)
  1x Lux/light sensor (e.g. BH1750 I2C) — ~$6.00  (needed by: cell_a_climate)
  1x PIR motion sensor — ~$5.00  (needed by: greenhouse_self_preservation)

Estimated total: ~$2644.96
```
