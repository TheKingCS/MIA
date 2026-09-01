"""
MIA Homestead — Greenhouse Assistant
v0.2

The conversational layer: lets Zac ask the greenhouse natural-language
questions and get answers grounded in real data via tool use. This is
NOT a control interface — it cannot bypass dosing limits or the safety
layer. It reads state and explains it; the module_registry + safety MCU
own all actual actuation.

As of docs/OFFLINE_ASSISTANT_PLAN.md step 6, `GreenhouseAssistant` (the
default, what you get from `python assistant/greenhouse_assistant.py`) is
LOCAL-MODEL-BACKED via Ollama — no API key, no internet dependency,
matching this project's self-sufficiency principle the same way the
two-tier Pi/MCU safety architecture does one layer down: any reliance on
an outside service for the assistant to think would defeat the actual
point of the system being self-contained. Requires Ollama running locally
(`systemctl --user status ollama`) with a tool-capable model pulled
(default `llama3.2:latest`).

`AnthropicGreenhouseAssistant` (cloud, needs `anthropic` python SDK +
ANTHROPIC_API_KEY) still exists, kept deliberately for re-running the
model bake-off (see the plan doc) and for cases where cloud is an
explicit, opted-into choice rather than a default dependency — not
removed, just no longer what you get without asking for it.
"""

import json
import logging
import sqlite3
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# anthropic is deliberately NOT imported at module level — GreenhouseAssistant
# (the default, local-model class) must be importable and usable with zero
# cloud dependency, including this one. Imported lazily inside
# AnthropicGreenhouseAssistant.__init__ instead, the only place it's needed.

from core.capability_registry import CapabilityRegistry
from core.hardware_registry import HardwareRegistry

logger = logging.getLogger("mia_homestead.assistant")

ANTHROPIC_MODEL = "claude-sonnet-5"

OLLAMA_MODEL = "llama3.2:latest"
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_REQUEST_TIMEOUT_SECONDS = 120  # generous: a cold model load is much slower than a warm one

PERSONALITY_PATH = Path(__file__).parent / "PERSONALITY.md"


TOOLS = [
    {
        "name": "get_current_status",
        "description": (
            "Get the latest sensor readings (pH, EC, temp, DO, water "
            "level, etc) for a given cell, or all cells if none specified."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_sensor_trends",
        "description": (
            "Check whether any sensor is drifting away from its own recent baseline — "
            "an early-warning signal for something still technically within target range "
            "but trending toward trouble, distinct from get_current_status's snapshot or "
            "get_open_alerts's already-out-of-range conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_sensor_confidence",
        "description": (
            "Get a high/medium/low trust level per sensor, combining calibration-due proximity "
            "and current drift status — distinct from get_sensor_trends (drift only) or "
            "get_current_status (raw readings), this answers 'how much should I trust this "
            "sensor right now,' not just what it currently reads."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_leak_status",
        "description": (
            "Get the current water-level drop rate for every cell (or one cell), and whether it "
            "crosses the fast-leak threshold — distinct from get_sensor_trends' slow-drift "
            "signal, this catches a sudden leak within one control cycle."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_circulation_status",
        "description": (
            "Get the current flow reading and commanded pump state for every cell with a flow "
            "sensor configured — distinct from get_leak_status, this catches a pump that's "
            "commanded on but not actually moving water (seized/clogged), not water loss."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_open_alerts",
        "description": "Get all unresolved alerts, optionally filtered by minimum severity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "min_severity": {
                    "type": "string",
                    "enum": ["info", "warning", "critical"],
                },
            },
        },
    },
    {
        "name": "get_dosing_history",
        "description": "Get recent dosing events for a cell, within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_yield_summary",
        "description": "Get harvest/yield events for a cell within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 30},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_power_status",
        "description": "Get the latest power telemetry — solar/battery/generator watts and battery SOC.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_climate_status",
        "description": (
            "Get the latest air temp/humidity/light/CO2 readings and current heater/fan/grow "
            "light/CO2 injector state for a cell (whichever of the optional sensors are "
            "actually configured), plus the temp/humidity target range they're controlled against."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer", "description": "Optional cell ID"},
            },
        },
    },
    {
        "name": "get_deploy_status",
        "description": (
            "Get the last known-good code commit and any active post-deploy watch — whether "
            "a recent code update is still being monitored for an auto-rollback trigger."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_power_forecast",
        "description": (
            "Project whether/when battery SOC will hit the load-shed threshold at the "
            "current drain rate — an early warning distinct from get_power_status's "
            "current-moment snapshot."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_inventory_status",
        "description": "Get current stock levels for all tracked inventory items (sensors, chemicals, spare parts).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_low_stock_items",
        "description": "Get inventory items at or below their reorder threshold.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_open_maintenance_tasks",
        "description": "Get open/in-progress maintenance tasks, optionally filtered by priority.",
        "input_schema": {
            "type": "object",
            "properties": {
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
            },
        },
    },
    {
        "name": "create_maintenance_task",
        "description": (
            "Create a maintenance task — e.g. 'swap the MCU', 'fix a leak in Cell A', "
            "'order a replacement pH probe'. Use this whenever the user asks you to "
            "log, assign, or track a repair/replacement/inspection."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "task_type": {"type": "string", "enum": ["repair", "replacement", "calibration", "inspection", "other"]},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
                "description": {"type": "string"},
                "assigned_to": {"type": "string"},
                "due_date": {"type": "string", "description": "ISO date, optional"},
            },
            "required": ["title", "task_type"],
        },
    },
    {
        "name": "get_revenue_summary",
        "description": "Get revenue transactions within a lookback window in days.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "record_revenue",
        "description": "Log a real sale — use when the user tells you they sold something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "item": {"type": "string"},
                "quantity": {"type": "number"},
                "unit": {"type": "string"},
                "unit_price": {"type": "number"},
                "cell_id": {"type": "integer"},
                "channel": {"type": "string", "description": "e.g. 'farmers_market','csa','direct','online'"},
                "notes": {"type": "string"},
            },
            "required": ["item", "quantity", "unit", "unit_price"],
        },
    },
    {
        "name": "get_cost_summary",
        "description": "Get real consumable cost (system-wide, not per-cell) for a lookback window — what was actually spent on inventory, from real unit costs.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "get_profitability_summary",
        "description": "Get a combined revenue-minus-cost profitability picture for a lookback window — the real margin, not just revenue or cost alone.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 30}},
        },
    },
    {
        "name": "get_to_order_list",
        "description": "Get items awaiting approve/deny decision in the reorder queue — things the system flagged as low stock.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_order",
        "description": "Approve a pending order in the to-order queue by its order_id.",
        "input_schema": {
            "type": "object",
            "properties": {"order_id": {"type": "integer"}},
            "required": ["order_id"],
        },
    },
    {
        "name": "deny_order",
        "description": "Deny/dismiss a pending order in the to-order queue by its order_id.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer"},
                "reason": {"type": "string"},
            },
            "required": ["order_id"],
        },
    },
    {
        "name": "get_system_capabilities",
        "description": (
            "Get full detail on what a specific part of the system can do — "
            "actions it can take, limits, safety behavior. Use this whenever "
            "you're unsure what a module is capable of, or the user asks "
            "'what can you do' / 'can you handle X'. Omit module_id to get "
            "everything."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"module_id": {"type": "string"}},
        },
    },
    {
        "name": "get_self_change_history",
        "description": (
            "Get the real history of how your own capabilities/hardware needs have "
            "changed as the underlying code was developed. Use when asked 'how have "
            "you changed', 'what's new about you', or similar self-development questions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "get_active_help_requests",
        "description": "Get any active 'help requested' beacon triggers — critical issues where a human presence was detected near the greenhouse.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "acknowledge_help_request",
        "description": "Acknowledge an active help request so the beacon stops nudging — use when the user says they're on it / helping now.",
        "input_schema": {
            "type": "object",
            "properties": {"request_id": {"type": "integer"}},
            "required": ["request_id"],
        },
    },
    {
        "name": "get_unpaired_devices",
        "description": "Get devices that are plugged in but haven't been assigned a role yet.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_device_setup_instructions",
        "description": "Get plain-language setup instructions for a device role (e.g. 'watering_mcu') — what to plug in, which port, where to mount it.",
        "input_schema": {
            "type": "object",
            "properties": {"role": {"type": "string"}},
            "required": ["role"],
        },
    },
    {
        "name": "pair_device",
        "description": "Assign a role to a device by its hardware_id — use when the user tells you what a newly plugged-in device is for.",
        "input_schema": {
            "type": "object",
            "properties": {
                "hardware_id": {"type": "string"},
                "role": {"type": "string"},
            },
            "required": ["hardware_id", "role"],
        },
    },
    {
        "name": "get_wiring_info",
        "description": "Get how a specific actuator is wired — which MCU, port, relay channel, and why.",
        "input_schema": {
            "type": "object",
            "properties": {"actuator_name": {"type": "string"}},
            "required": ["actuator_name"],
        },
    },
    {
        "name": "get_plumbing_info",
        "description": "Get plumbing segments for a cell or a specific actuator, including pipe sizes and why routed that way.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "actuator_name": {"type": "string"},
            },
        },
    },
    {
        "name": "diagnose_alert",
        "description": "Get a specific, wiring-aware diagnosis for an alert — which physical component to check, not generic troubleshooting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "alert_id": {"type": "integer"},
                "create_task": {"type": "boolean", "default": False},
            },
            "required": ["alert_id"],
        },
    },
    {
        "name": "get_expected_vs_actual_yield",
        "description": "Compare expected vs actual yield for a specific planting.",
        "input_schema": {
            "type": "object",
            "properties": {"planting_id": {"type": "integer"}},
            "required": ["planting_id"],
        },
    },
    {
        "name": "get_water_usage",
        "description": "Get water usage history for a cell, with the reason behind each use.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_dosing_rationale",
        "description": "Get recent dosing events for a cell WITH the reasoning behind each dose, not just the amount.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "days": {"type": "integer", "default": 7},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_bed_plantings",
        "description": "Get what's currently planted in each bed, optionally filtered by cell.",
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
        },
    },
    {
        "name": "record_planting",
        "description": "Record a new planting in a grow bed — use when the user tells you what they planted.",
        "input_schema": {
            "type": "object",
            "properties": {
                "grow_bed_name": {"type": "string"},
                "cell_id": {"type": "integer"},
                "species_name": {"type": "string", "description": "e.g. 'lettuce', 'tilapia'"},
                "variety": {"type": "string"},
            },
            "required": ["grow_bed_name", "cell_id", "species_name"],
        },
    },
    {
        "name": "plan_planting",
        "description": "Stage a FUTURE planting that hasn't happened yet — use when the user is planning ahead, not describing something already planted. Use record_planting instead if it's already in the ground.",
        "input_schema": {
            "type": "object",
            "properties": {
                "grow_bed_name": {"type": "string"},
                "cell_id": {"type": "integer"},
                "species_name": {"type": "string", "description": "e.g. 'lettuce', 'tilapia'"},
                "target_plant_date": {"type": "string", "description": "When it's intended to go in, e.g. '2026-09-15'"},
                "variety": {"type": "string"},
            },
            "required": ["grow_bed_name", "cell_id", "species_name"],
        },
    },
    {
        "name": "convert_planting_to_active",
        "description": "Mark a previously-planned planting as actually planted now — use when the user says a planned planting has actually gone in.",
        "input_schema": {
            "type": "object",
            "properties": {
                "planting_id": {"type": "integer"},
                "quantity_planted": {"type": "integer", "description": "Correct the real count here if it ended up different from what was planned"},
            },
            "required": ["planting_id"],
        },
    },
    {
        "name": "get_planned_plantings",
        "description": "Get plantings that have been staged for the future but haven't actually happened yet, optionally filtered by cell.",
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
        },
    },
    {
        "name": "mark_planting_harvested",
        "description": "Mark a planting as harvested — use when the user says they harvested something.",
        "input_schema": {
            "type": "object",
            "properties": {"planting_id": {"type": "integer"}},
            "required": ["planting_id"],
        },
    },
    {
        "name": "mark_planting_failed",
        "description": "Mark a planting as failed — use when the user says a crop died or didn't make it.",
        "input_schema": {
            "type": "object",
            "properties": {
                "planting_id": {"type": "integer"},
                "notes": {"type": "string"},
            },
            "required": ["planting_id"],
        },
    },
    {
        "name": "record_water_usage",
        "description": "Log water usage with a reason — use when the user tells you they watered something, or to record a manual watering.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "amount_gallons": {"type": "number"},
                "reason": {"type": "string"},
                "grow_bed_name": {"type": "string"},
            },
            "required": ["cell_id", "amount_gallons", "reason"],
        },
    },
    {
        "name": "record_water_quality_test",
        "description": (
            "Log a real ammonia/nitrite/nitrate water test result (from an actual test kit "
            "reading) for a cell — use when the user tells you they ran a water test. At least "
            "one of ammonia_ppm/nitrite_ppm/nitrate_ppm is required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "ammonia_ppm": {"type": "number"},
                "nitrite_ppm": {"type": "number"},
                "nitrate_ppm": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_biofilter_cycle_status",
        "description": (
            "Get a cell's nitrogen-cycle status (ammonia/nitrite/nitrate phase, or confirmed "
            "cycled) from its real logged water tests, and whether it's safe to stock livestock "
            "there right now."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
            "required": ["cell_id"],
        },
    },
    {
        "name": "record_feeding",
        "description": "Log a real feeding event for a cell's fish — use when the user tells you they fed the fish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "amount": {"type": "number"},
                "unit": {"type": "string", "description": "Defaults to 'oz'"},
                "food_type": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["cell_id", "amount"],
        },
    },
    {
        "name": "record_fish_mortality",
        "description": "Log real fish mortality for a cell — use when the user tells you fish died.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "count": {"type": "integer"},
                "cause": {"type": "string", "description": "Suspected cause, if known"},
                "notes": {"type": "string"},
            },
            "required": ["cell_id", "count"],
        },
    },
    {
        "name": "record_fish_health_observation",
        "description": "Log a fish health/behavior observation for a cell that isn't a mortality event — use when the user describes how the fish are doing or acting.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "description": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["cell_id", "description"],
        },
    },
    {
        "name": "get_fish_health_summary",
        "description": "Get a cell's fish picture: recent feeding history and trend, mortality history, and health observations — everything fish-related in one place.",
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_pest_disease_info",
        "description": "Look up known pest/disease symptoms and guidance by name (e.g. 'aphids', 'ich') — use when the user asks what a symptom means or how to treat something.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "organism_type": {"type": "string", "description": "Optional: 'plant' or 'fish', to list everything known for that type instead of one lookup"},
            },
        },
    },
    {
        "name": "record_pest_disease_observation",
        "description": "Log a real pest/disease observation for a cell — use when the user describes seeing a pest, disease symptom, or something concerning on a plant or fish.",
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "description": {"type": "string"},
                "category": {"type": "string", "enum": ["pest", "disease", "other"]},
                "severity": {"type": "string", "enum": ["minor", "moderate", "severe"]},
                "action_taken": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["cell_id", "description"],
        },
    },
    {
        "name": "get_pest_disease_history",
        "description": "Get logged pest/disease observation history for a cell.",
        "input_schema": {
            "type": "object",
            "properties": {"cell_id": {"type": "integer"}},
            "required": ["cell_id"],
        },
    },
    {
        "name": "get_weather_status",
        "description": "Get the most recent weather forecast check (frost risk, forecast low/high, and any species-range violation) — returns null if no location is configured or the last check found nothing on file yet.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "add_species",
        "description": "Add a new species to the knowledge base — use when the user wants to track a plant or fish species that isn't already known.",
        "input_schema": {
            "type": "object",
            "properties": {
                "common_name": {"type": "string"},
                "organism_type": {"type": "string", "enum": ["plant", "fish"]},
                "scientific_name": {"type": "string"},
                "ph_min": {"type": "number"}, "ph_max": {"type": "number"},
                "ec_min": {"type": "number"}, "ec_max": {"type": "number"},
                "notes": {"type": "string"},
            },
            "required": ["common_name", "organism_type"],
        },
    },
    {
        "name": "update_maintenance_task_status",
        "description": "Change a maintenance task's status — use when the user says a repair is done, in progress, or should be cancelled.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "status": {"type": "string", "enum": ["open", "in_progress", "done", "cancelled"]},
            },
            "required": ["task_id", "status"],
        },
    },
    {
        "name": "assign_maintenance_task",
        "description": "Assign a maintenance task to someone — use when the user tells you who should handle a task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "integer"},
                "assigned_to": {"type": "string"},
            },
            "required": ["task_id", "assigned_to"],
        },
    },
    {
        "name": "deny_parameter_change",
        "description": "Deny a suggested permanent target change from a completed experiment.",
        "input_schema": {
            "type": "object",
            "properties": {"proposal_id": {"type": "integer"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "complete_experiment_now",
        "description": "End a running experiment early and get its result summary — use when the user wants to stop an experiment before its planned end date.",
        "input_schema": {
            "type": "object",
            "properties": {"experiment_id": {"type": "integer"}},
            "required": ["experiment_id"],
        },
    },
    {
        "name": "get_deadmans_switch_status",
        "description": "Check how long it's been since a human checked in, and whether the dead-man's-switch has escalated.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_species_profile",
        "description": "Get the ideal pH/EC/temperature range for a species by name.",
        "input_schema": {
            "type": "object",
            "properties": {"species_name": {"type": "string"}},
            "required": ["species_name"],
        },
    },
    {
        "name": "list_species",
        "description": "List all species in the knowledge base.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "propose_experiment",
        "description": (
            "Propose a controlled experiment — changing one target variable on a cell for a "
            "duration to see if it improves yield. Use when the user wants to test/tune conditions."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "cell_id": {"type": "integer"},
                "hypothesis": {"type": "string"},
                "variable_changed": {"type": "string", "enum": ["ph_target_min", "ph_target_max", "ec_target_min", "ec_target_max"]},
                "baseline_value": {"type": "number"},
                "test_value": {"type": "number"},
                "duration_days": {"type": "integer", "default": 14},
            },
            "required": ["cell_id", "hypothesis", "variable_changed", "baseline_value", "test_value"],
        },
    },
    {
        "name": "start_experiment",
        "description": "Start a proposed experiment — this actually changes the cell's live dosing target. Only call after explicit user approval.",
        "input_schema": {
            "type": "object",
            "properties": {"experiment_id": {"type": "integer"}},
            "required": ["experiment_id"],
        },
    },
    {
        "name": "get_active_experiments",
        "description": "Get experiments currently proposed or running.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_pending_parameter_changes",
        "description": "Get evidence-based target changes awaiting approval from completed experiments.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_parameter_change",
        "description": "Approve a suggested permanent target change from a completed experiment.",
        "input_schema": {
            "type": "object",
            "properties": {"proposal_id": {"type": "integer"}},
            "required": ["proposal_id"],
        },
    },
    {
        "name": "create_config_snapshot",
        "description": "Create a backup snapshot of current configuration before making a change.",
        "input_schema": {
            "type": "object",
            "properties": {"label": {"type": "string"}, "reason": {"type": "string"}},
            "required": ["label"],
        },
    },
    {
        "name": "list_config_snapshots",
        "description": "List available configuration backup snapshots.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "restore_config_snapshot",
        "description": "Restore configuration from a snapshot — reverts config files and control parameters, not history. Use only after explicit user confirmation.",
        "input_schema": {
            "type": "object",
            "properties": {"snapshot_id": {"type": "integer"}},
            "required": ["snapshot_id"],
        },
    },
    {
        "name": "get_verification_coverage",
        "description": "Get how many capabilities are actually proven vs just described — an honest maturity check.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "run_self_diagnostics",
        "description": (
            "Actually run the full self-diagnostic suite right now (the same 7 checks "
            "core/self_audit.py runs from the terminal, including the real scenario "
            "regression suite) and report whether everything currently passes. Slower than "
            "the other self_knowledge tools (runs real checks, not a cached fact) but gives "
            "a genuine, current answer instead of a static description."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_recent_automated_actions",
        "description": "Get recent automated actions with their rationale (load-shedding, beacon triggers, etc) — the 'why did you do that' log for non-dosing actions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "module_id": {"type": "string"},
                "days": {"type": "integer", "default": 7},
            },
        },
    },
    {
        "name": "get_activity_journal",
        "description": (
            "Get a unified chronological journal across dosing, alerts, experiments, "
            "maintenance, and yield — broader than get_recent_automated_actions, which only "
            "covers general automated actions, not dosing/alerts/experiments/maintenance/yield."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "default": 7},
            },
        },
    },
    {
        "name": "get_control_loop_status",
        "description": "Is the control loop actually running right now (heartbeat), and what was the most recent thing it did.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_upcoming_activity",
        "description": (
            "What's genuinely scheduled or planned next — a real upcoming maintenance task, "
            "an experiment's planned end date, an active deploy watch resolving, the next "
            "periodic report. Never invents a plan the system doesn't actually have."
        ),
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_greenhouse_report",
        "description": "Get a compiled state-of-the-greenhouse report — yields, dosing, alerts, pending approvals, maintenance, experiments — instead of asking several separate questions.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 7}},
        },
    },
    {
        "name": "send_greenhouse_report",
        "description": (
            "Generate the state-of-the-greenhouse report AND actually send it "
            "via the notification path, not just display it here — use this "
            "when the user asks you to send/email/deliver the report, as "
            "opposed to get_greenhouse_report which only shows it in chat."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 7}},
        },
    },
    {
        "name": "get_consumable_forecast",
        "description": "Get a projection of when an inventory item will hit its reorder threshold based on real consumption rate.",
        "input_schema": {
            "type": "object",
            "properties": {"item_id": {"type": "integer"}},
            "required": ["item_id"],
        },
    },
    {
        "name": "record_human_checkin",
        "description": "Record that a human has checked in/interacted with the system — resets the dead-man's-switch escalation. Call this naturally whenever the user is actively conversing.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_irrigation_status",
        "description": "Get every configured scheduled-irrigation grow bed, its interval, and when it last actually watered.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_hardware_needs_list",
        "description": "Get the running hardware shopping list — every physical component every module/service has declared it needs, aggregated with estimated cost.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_last_human_checkin",
        "description": "Get when a human last acknowledged an alert or viewed the dashboard.",
        "input_schema": {"type": "object", "properties": {}},
    },
]

# ---------- Tool domains (see docs/OFFLINE_ASSISTANT_PLAN.md) ----------
#
# Groups every tool above by subject area so a future local model isn't
# handed all of TOOLS on every single message — MIA Homestead's registry is
# already past the tool count where the sibling M.I.A. project measured
# real cross-schema tool-calling failures on a small local model. This is
# step 1 of that plan (tagging) only: a pure data mapping, kept separate
# from the TOOLS list itself so it can never perturb the Anthropic tool
# schema those dicts are validated against. Not wired into ask() yet —
# every message still gets the full tool list until step 2 (the gating
# classifier) lands.
#
# core/self_audit.py enforces that this mapping never silently drifts out
# of sync with TOOLS as tools are added/renamed/removed.

ALWAYS_ON_DOMAINS = {"status", "self_knowledge"}
# Cheap and broadly relevant regardless of what's asked — candidates for
# always-on attachment once gating is wired in, rather than gated like
# everything else.

TOOL_DOMAINS: dict[str, str] = {
    # status — routine state checks, cheap, broadly relevant
    "get_current_status": "status",
    "get_sensor_trends": "status",
    "get_sensor_confidence": "status",
    "get_leak_status": "status",
    "get_circulation_status": "status",
    "get_open_alerts": "status",
    "get_power_status": "status",
    "get_power_forecast": "status",
    "get_climate_status": "status",
    "get_deploy_status": "status",
    "get_deadmans_switch_status": "status",
    "get_greenhouse_report": "status",
    "send_greenhouse_report": "status",
    "record_human_checkin": "status",
    "get_last_human_checkin": "status",
    # dosing — pH/EC dosing history and rationale
    "get_dosing_history": "dosing",
    "get_dosing_rationale": "dosing",
    # yield_planting — what's planted, harvested, watered, and how it did
    "get_yield_summary": "yield_planting",
    "get_expected_vs_actual_yield": "yield_planting",
    "get_water_usage": "yield_planting",
    "get_bed_plantings": "yield_planting",
    "record_planting": "yield_planting",
    "plan_planting": "yield_planting",
    "convert_planting_to_active": "yield_planting",
    "get_planned_plantings": "yield_planting",
    "mark_planting_harvested": "yield_planting",
    "mark_planting_failed": "yield_planting",
    "record_water_usage": "yield_planting",
    "get_irrigation_status": "yield_planting",
    "record_water_quality_test": "water_quality",
    "get_biofilter_cycle_status": "water_quality",
    "record_feeding": "fish_health",
    "record_fish_mortality": "fish_health",
    "record_fish_health_observation": "fish_health",
    "get_fish_health_summary": "fish_health",
    "get_pest_disease_info": "pest_disease",
    "record_pest_disease_observation": "pest_disease",
    "get_pest_disease_history": "pest_disease",
    "get_weather_status": "weather",
    # species — the "what does this organism want" knowledge base
    "get_species_profile": "species",
    "list_species": "species",
    "add_species": "species",
    # experiments — the aquaponics-scientist propose/run/evaluate lifecycle
    "propose_experiment": "experiments",
    "start_experiment": "experiments",
    "get_active_experiments": "experiments",
    "complete_experiment_now": "experiments",
    "get_pending_parameter_changes": "experiments",
    "approve_parameter_change": "experiments",
    "deny_parameter_change": "experiments",
    # inventory — stock, low-stock, to-order queue, consumption forecasting
    "get_inventory_status": "inventory",
    "get_low_stock_items": "inventory",
    "get_to_order_list": "inventory",
    "approve_order": "inventory",
    "deny_order": "inventory",
    "get_consumable_forecast": "inventory",
    # maintenance — repair/replacement/calibration tasks
    "get_open_maintenance_tasks": "maintenance",
    "create_maintenance_task": "maintenance",
    "update_maintenance_task_status": "maintenance",
    "assign_maintenance_task": "maintenance",
    # infrastructure — wiring/plumbing knowledge and alert diagnosis
    "get_wiring_info": "infrastructure",
    "get_plumbing_info": "infrastructure",
    "diagnose_alert": "infrastructure",
    # devices — plug-and-play MCU pairing
    "get_unpaired_devices": "devices",
    "get_device_setup_instructions": "devices",
    "pair_device": "devices",
    # help_requests — self-preservation beacon lifecycle
    "get_active_help_requests": "help_requests",
    "acknowledge_help_request": "help_requests",
    # backups — config snapshot/restore
    "create_config_snapshot": "backups",
    "list_config_snapshots": "backups",
    "restore_config_snapshot": "backups",
    # revenue — sales/financial tracking
    "get_revenue_summary": "revenue",
    "record_revenue": "revenue",
    "get_cost_summary": "revenue",
    "get_profitability_summary": "revenue",
    # self_knowledge — what the system can do, how it's changed, proof coverage
    "get_system_capabilities": "self_knowledge",
    "get_self_change_history": "self_knowledge",
    "get_verification_coverage": "self_knowledge",
    "run_self_diagnostics": "self_knowledge",
    "get_recent_automated_actions": "self_knowledge",
    "get_activity_journal": "self_knowledge",
    "get_control_loop_status": "self_knowledge",
    "get_upcoming_activity": "self_knowledge",
    "get_hardware_needs_list": "self_knowledge",
}

# ---------- Domain gating classifier (step 2 of docs/OFFLINE_ASSISTANT_PLAN.md) ----------
#
# A cheap, deterministic keyword classifier — NOT a model call — deciding
# which non-always-on domains a message plausibly touches, so a future
# local model isn't handed all 54 tools on every turn (see the plan doc for
# why that matters on a small model specifically). Deliberately simple
# substring matching, not NLP: false positives (an extra domain attached)
# just mean a few extra tools in the request; false negatives are the real
# risk, which is why both functions below fail OPEN rather than closed —
# an ambiguous or unmatched message gets the FULL tool list, never a
# silently incomplete one. This is not a safety mechanism; it's a
# tool-count budget. The actual safety net for a model mis-firing a
# destructive call is step 3 (bundled destructive-call protection),
# a separate, unrelated mechanism.

DOMAIN_TRIGGER_KEYWORDS: dict[str, list[str]] = {
    "dosing": ["dos", "ph up", "ph down", "ph-up", "ph-down", "nutrient", "correction", "pump"],
    "water_quality": [
        "ammonia", "nitrite", "nitrate", "biofilter", "nitrogen cycle", "cycled",
        "cycling", "test kit", "water test", "stock fish", "stocking",
    ],
    "fish_health": [
        "fish", "feed", "feeding", "fed", "mortality", "died", "dead fish",
        "sick", "lethargic", "behavior", "swimming",
    ],
    "pest_disease": [
        "pest", "disease", "aphid", "aphids", "mildew", "mold", "fungus",
        "rot", "ich", "white spot", "columnaris", "bug", "bugs", "insect",
        "infestation", "infection", "symptom", "symptoms",
    ],
    "weather": [
        "weather", "frost", "forecast", "freeze", "freezing", "heat wave",
        "cold snap", "outside temperature", "outdoor",
    ],
    "yield_planting": [
        "yield", "harvest", "planted", "planting", "grow bed", "watered",
        "watering", "gallons", "crop", "produce", "expected vs actual",
    ],
    "species": [
        "species", "ideal range", "tolerance", "compatible", "compatibility",
        # Baseline species names as a static fallback for when no `db` is
        # passed to relevant_domains() (e.g. a unit test exercising pure
        # keyword matching). When `db` IS passed — every real call site
        # does — relevant_domains() also queries species_profiles.common_name
        # live, so a species added later via add_species gates its own name
        # automatically. This closes a gap flagged (found via live-model
        # testing, docs/OFFLINE_ASSISTANT_PLAN.md step 5) but deliberately
        # deferred at the time: "the real fix is querying species_profiles
        # at gating time instead of a static list."
        "lettuce", "basil", "tilapia",
    ],
    "experiments": [
        "experiment", "hypothesis", "propose", "test value", "baseline",
        "adopt", "parameter change",
    ],
    "inventory": [
        "stock", "inventory", "low on", "reorder", "order", "chemical",
        "supply", "supplies", "running out", "buy", "purchase",
    ],
    "maintenance": ["maintenance", "repair", "task", "broken", "calibrat", "assign", "leak"],
    "infrastructure": [
        "wiring", "wired", "plumbing", "pipe", "relay", "port", "mcu",
        "diagnose", "diagnosis", "wire", "pump",
    ],
    "devices": ["device", "pair", "paired", "unpaired", "plugged in", "controller"],
    "backups": ["snapshot", "backup", "restore", "rollback", "roll back", "revert"],
    "help_requests": ["help request", "asking for help", "beacon", "need help", "presence"],
    "revenue": [
        "revenue", "sales", "sold", "income", "earned", "market",
        "cost", "costs", "profit", "profitability", "margin", "expenses", "spent",
    ],
}
# status and self_knowledge are ALWAYS_ON_DOMAINS — attached unconditionally,
# so they're deliberately absent from this dict; no trigger keywords needed.


def relevant_domains(message: str, db: "sqlite3.Connection | None" = None) -> set[str]:
    """Domains a message's keywords plausibly touch, always including
    ALWAYS_ON_DOMAINS. A message can and often will match more than
    one — e.g. 'why does that pump run so much' touches both dosing
    and infrastructure, and should surface tools from both.

    `db`, when given, additionally matches live `species_profiles.common_name`
    values against the message — a species added later via `add_species`
    gates its own name with no code change needed, closing the "static list
    goes stale" gap `DOMAIN_TRIGGER_KEYWORDS["species"]`'s own comment
    documents. Falls back to the static baseline names when `db` is None
    (e.g. a pure unit test with no database)."""
    text = message.lower()
    matched = {
        domain for domain, keywords in DOMAIN_TRIGGER_KEYWORDS.items()
        if any(kw in text for kw in keywords)
    }
    if db is not None:
        try:
            names = [row[0] for row in db.execute("SELECT common_name FROM species_profiles").fetchall()]
        except sqlite3.OperationalError:
            names = []  # table not created yet (e.g. a fresh, unseeded DB) — fail open, not crash
        if any(name.lower() in text for name in names):
            matched.add("species")
    return matched | ALWAYS_ON_DOMAINS


def tools_for_domains(domains: set[str]) -> list[dict]:
    """Filters TOOLS down to the given domains. If nothing beyond the
    always-on domains matched, falls back to JUST the always-on domains'
    tools — NOT the full list. This was originally "attach everything" on
    the theory that an ambiguous message shouldn't risk hiding a real
    capability, but real testing against llama3.2:3b (2026-08-26,
    docs/OFFLINE_ASSISTANT_PLAN.md step 4) falsified that: the full
    55-tool list combined with the full system prompt made this model
    stop calling tools entirely and just narrate about its own schema —
    a worse failure than a bounded miss. qwen2.5:7b handled the identical
    payload fine, so this is a real llama3.2:3b capacity limit at this
    tool count, not a bad payload — see the plan doc for the full
    comparison. Any tool missing from TOOL_DOMAINS (shouldn't happen —
    self_audit.py enforces full coverage) is still included defensively."""
    if domains <= ALWAYS_ON_DOMAINS:
        return [t for t in TOOLS if TOOL_DOMAINS.get(t["name"]) in ALWAYS_ON_DOMAINS]
    return [
        t for t in TOOLS
        if TOOL_DOMAINS.get(t["name"]) in domains or t["name"] not in TOOL_DOMAINS
    ]


# ---------- Bundled destructive-call protection (step 3 of docs/OFFLINE_ASSISTANT_PLAN.md) ----------
#
# Not hypothetical: the sibling M.I.A. project found, while benchmarking a
# local model, that it would sometimes return a legitimate read-only tool
# call bundled with a spurious DESTRUCTIVE one the user never asked for —
# something the cloud model this assistant currently uses has never done.
# This app was never designed for multi-intent-per-message, so nothing
# stops that today. core/self_audit.py enforces this set can't drift from
# a real tool name (typo or a stale entry after a rename).

DESTRUCTIVE_TOOLS: set[str] = {
    "approve_order",              # commits to a real purchase decision
    "deny_order",                 # dismisses a proposed reorder
    "restore_config_snapshot",    # overwrites current config/control params
    "start_experiment",           # changes a cell's LIVE dosing target immediately
    "approve_parameter_change",   # permanently changes a cell's dosing target
    "deny_parameter_change",      # dismisses an evidence-based target change
    "acknowledge_help_request",   # suppresses the self-preservation beacon's nudging
    "pair_device",                # assigns real hardware role, creates live actuators
    "mark_planting_failed",       # irreversible record correction, no "unfail" tool
}


def split_safe_tool_calls(tool_use_blocks: list) -> tuple[list, list]:
    """Decides which tool_use blocks from one model response are safe to
    execute. A single call always executes even if destructive — that's
    the normal case of a direct request ('approve order 4'). A reply
    bundling 2+ calls where ANY of them is destructive skips every
    destructive one and executes only the safe ones, rather than trusting
    that the model meant to bundle a consequential action in with an
    unrelated read. Returns (safe_blocks, skipped_blocks)."""
    if len(tool_use_blocks) <= 1:
        return tool_use_blocks, []
    safe = [b for b in tool_use_blocks if b.name not in DESTRUCTIVE_TOOLS]
    skipped = [b for b in tool_use_blocks if b.name in DESTRUCTIVE_TOOLS]
    return safe, skipped


# ---------- Ollama protocol helpers (local backend, step 4/6) ----------

def _anthropic_tool_to_ollama(tool: dict) -> dict:
    """Anthropic's {name, description, input_schema} -> Ollama/OpenAI-style
    {type: function, function: {name, description, parameters}}. Same
    JSON Schema either way — only the envelope differs."""
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


@dataclass
class _OllamaToolCall:
    """Minimal adapter so split_safe_tool_calls() (which only touches
    .name) works identically regardless of backend — deliberately not a
    full reimplementation of Anthropic's tool_use block shape."""
    name: str
    input: dict
    raw: dict


def _parse_ollama_tool_calls(raw_tool_calls: list[dict]) -> list[_OllamaToolCall]:
    parsed = []
    for tc in raw_tool_calls:
        fn = tc.get("function", {})
        name = fn.get("name", "")
        args = fn.get("arguments", {})
        # Some Ollama versions return arguments as a JSON string rather
        # than an already-parsed dict — handle both rather than assume.
        if isinstance(args, str):
            try:
                args = json.loads(args) if args else {}
            except json.JSONDecodeError:
                logger.warning("Could not parse tool call arguments as JSON: %r", args)
                args = {}
        parsed.append(_OllamaToolCall(name=name, input=args, raw=tc))
    return parsed


class _BaseGreenhouseAssistant:
    """Shared state and every tool handler (_tool_*), _dispatch_tool, and
    _system_prompt — no model client, no ask() implementation. Backend
    subclasses (GreenhouseAssistant for the default local model,
    AnthropicGreenhouseAssistant for the explicit cloud opt-in) provide
    only those two backend-specific pieces. See
    docs/OFFLINE_ASSISTANT_PLAN.md step 6 for why this split exists —
    duplicating 55 tool handlers across two classes would be exactly the
    kind of drift-prone duplication this project's whole capability-
    registry philosophy exists to avoid."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.personality = PERSONALITY_PATH.read_text()
        self.history: list[dict] = []

    # ---------- System prompt ----------

    def _system_prompt(self) -> str:
        live_capabilities = CapabilityRegistry.render_compact(self.db)
        return (
            "You are the conversational voice of a homestead greenhouse "
            "aquaponics system called MIA Homestead. You answer questions "
            "about your own state using the tools provided — every factual "
            "claim must come from a tool call, never from assumption or "
            "prior turns if fresher data might exist. If a tool call "
            "returns no data (an empty list, a null value, zero rows), "
            "say that plainly — 'no data yet' or equivalent — and NEVER "
            "state a specific number, reading, or event as if it were "
            "real when the tool told you nothing exists. This includes "
            "the example exchanges in the personality spec below: those "
            "numbers (pH 6.9, EC 740, battery 68%, etc.) are STYLE "
            "reference for a hypothetical scenario, never real data — "
            "do not state them as fact unless a tool call you just made "
            "in THIS conversation actually returned them. Follow this "
            "personality and behavior spec exactly:\n\n" + self.personality +
            "\n\n---\n\n"
            "The following is a LIVE, auto-generated list of every module "
            "currently registered in this system — it was built directly "
            "from the code at startup, not written by hand, so it's always "
            "current even as modules get added later. Use this to know what "
            "exists; call get_system_capabilities for full detail (actions "
            "possible, limits, safety behavior) on anything specific:\n\n" +
            live_capabilities
        )

    # ---------- Tool dispatch ----------

    def _dispatch_tool(self, name: str, tool_input: dict) -> dict:
        try:
            handler = getattr(self, f"_tool_{name}")
            return self._annotate_if_empty(handler(**tool_input))
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return {"error": str(e)}

    @staticmethod
    def _annotate_if_empty(result: dict) -> dict:
        """If a tool result carries no usable data — either every
        list-valued field is empty, or the call itself errored — inject
        an explicit in-band 'no data' note directly in the tool result
        the model is about to reason from, not just a system-prompt-level
        instruction far away from the actual decision point.

        Found necessary the hard way (docs/OFFLINE_ASSISTANT_PLAN.md step
        5): a system-prompt-only anti-fabrication instruction was NOT
        reliable against llama3.2:3b — it fabricated specific numbers
        copied near-verbatim from PERSONALITY.md's own example exchanges
        when a tool call correctly returned empty data, and this
        reproduced on more than one tool (get_current_status,
        get_dosing_rationale), which ruled out patching individual
        handlers one at a time as a real strategy for 55 tools. This is
        the single, centralized fix instead — applies uniformly to every
        tool's result, at the one place all of them pass through
        already.

        Real second reproduction found 2026-08-31, live-model-check re-run
        while verifying an unrelated change: the ORIGINAL version of this
        function explicitly skipped annotating error results
        (`"error" in result: return result`) on the theory an error was
        self-evidently 'no data' to the model. It wasn't — asked "why
        does that pump run so much" with no real alert to diagnose, the
        model called diagnose_alert with a hallucinated alert_id, got
        back a correctly-honest {"error": "no alert null"}, and then
        answered anyway with specific wiring facts (relay channel,
        mounting location) fabricated near-verbatim from PERSONALITY.md's
        example text — the exact same failure mode as the empty-list
        case, through a path this function used to explicitly exempt.
        Errors now get the same explicit grounding note as empty lists."""
        if not isinstance(result, dict) or "note" in result:
            return result
        if "error" in result:
            result = dict(result)
            result["note"] = (
                "This tool call did NOT return usable data (see the error above). Tell the "
                "user plainly that you don't have this information — do NOT invent any "
                "specific number, reading, wiring detail, or event, including anything "
                "resembling the example exchanges in your personality spec."
            )
            return result
        list_fields = {k: v for k, v in result.items() if isinstance(v, list)}
        if not list_fields or any(list_fields.values()):
            return result  # nothing list-shaped, or at least one has real content
        result = dict(result)
        result["note"] = (
            "No data exists yet for this — every list field above is empty. Tell the "
            "user plainly there's nothing to report, and do NOT invent any specific "
            "number, reading, or event, including anything resembling the example "
            "exchanges in your personality spec."
        )
        return result

    def _tool_get_current_status(self, cell_id: int | None = None) -> dict:
        query = """
            SELECT s.cell_id, s.type, sr.value, sr.timestamp, sr.is_stale
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id)
        """
        params = ()
        if cell_id is not None:
            query += " AND s.cell_id = ?"
            params = (cell_id,)
        rows = self.db.execute(query, params).fetchall()
        # Empty-result anti-fabrication annotation is applied centrally by
        # _dispatch_tool()'s _annotate_if_empty() — no per-tool special
        # case needed here anymore, see that method's docstring for why.
        return {"readings": [dict(r) for r in rows]}

    def _tool_get_sensor_trends(self, cell_id: int | None = None) -> dict:
        from core.trend_analyzer import TrendAnalyzer
        return {"drift_findings": TrendAnalyzer(self.db).get_drift_status(cell_id)}

    def _tool_get_sensor_confidence(self, cell_id: int | None = None) -> dict:
        from core.sensor_confidence import SensorConfidence
        return {"confidence": SensorConfidence(self.db).get_all_confidence(cell_id)}

    def _tool_get_leak_status(self, cell_id: int | None = None) -> dict:
        from core.leak_detector import LeakDetector
        return {"level_readings": LeakDetector(self.db).get_leak_status(cell_id)}

    def _tool_get_circulation_status(self, cell_id: int | None = None) -> dict:
        from core.circulation_monitor import CirculationMonitor
        return {"circulation": CirculationMonitor(self.db).get_circulation_status(cell_id)}

    def _tool_get_open_alerts(self, min_severity: str | None = None) -> dict:
        order = {"info": 0, "warning": 1, "critical": 2}
        query = "SELECT * FROM alerts WHERE resolved = 0 ORDER BY last_seen DESC LIMIT 20"
        rows = [dict(r) for r in self.db.execute(query).fetchall()]
        if min_severity:
            rows = [r for r in rows if order.get(r["severity"], 0) >= order[min_severity]]
        return {"alerts": rows}

    def _tool_get_dosing_history(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            """
            SELECT * FROM dosing_events
            WHERE cell_id = ? AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"dosing_events": [dict(r) for r in rows]}

    def _tool_get_yield_summary(self, cell_id: int, days: int = 30) -> dict:
        rows = self.db.execute(
            """
            SELECT * FROM yield_events
            WHERE cell_id = ? AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            """,
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"yield_events": [dict(r) for r in rows]}

    def _tool_get_power_status(self) -> dict:
        row = self.db.execute(
            "SELECT * FROM power_telemetry ORDER BY timestamp DESC LIMIT 5"
        ).fetchall()
        return {"recent_power_telemetry": [dict(r) for r in row]}

    def _tool_get_climate_status(self, cell_id: int | None = None) -> dict:
        query = """
            SELECT s.cell_id, s.type, sr.value, sr.timestamp, sr.is_stale
            FROM sensor_readings sr
            JOIN sensors s ON s.id = sr.sensor_id
            WHERE s.type IN ('temp_air', 'humidity', 'light', 'co2')
            AND sr.id IN (SELECT MAX(id) FROM sensor_readings GROUP BY sensor_id)
        """
        params = ()
        if cell_id is not None:
            query += " AND s.cell_id = ?"
            params = (cell_id,)
        readings = [dict(r) for r in self.db.execute(query, params).fetchall()]

        actuator_query = """
            SELECT a.cell_id, a.type, a.name, ae.action, ae.timestamp
            FROM actuators a
            LEFT JOIN actuator_events ae ON ae.id = (
                SELECT id FROM actuator_events WHERE actuator_id = a.id ORDER BY id DESC LIMIT 1
            )
            WHERE a.type IN ('heater', 'fan', 'grow_light', 'co2_valve')
        """
        actuator_params = ()
        if cell_id is not None:
            actuator_query += " AND a.cell_id = ?"
            actuator_params = (cell_id,)
        actuator_state = [dict(r) for r in self.db.execute(actuator_query, actuator_params).fetchall()]

        targets_query = "SELECT cell_id, param_name, value FROM target_overrides WHERE active = 1 AND param_name IN ('temp_min', 'temp_max', 'humidity_max')"
        targets_params = ()
        if cell_id is not None:
            targets_query += " AND cell_id = ?"
            targets_params = (cell_id,)
        target_overrides = [dict(r) for r in self.db.execute(targets_query, targets_params).fetchall()]

        return {
            "readings": readings,
            "actuator_state": actuator_state,
            "active_target_overrides": target_overrides,
        }

    def _tool_get_deploy_status(self) -> dict:
        from core.deploy_manager import DeployManager
        return DeployManager(self.db).get_status()

    def _tool_get_power_forecast(self) -> dict:
        """PowerMonitor.forecast_soc_depletion() needs the array's real
        configured threshold — reads config/modules.yaml directly for
        every modules.power_monitor.PowerMonitor entry (there's exactly
        one, greenhouse_power, today; written to handle more than one
        without changes since config/modules.yaml's own comments already
        anticipate a second array for the house) rather than
        constructing a whole ModuleRegistry (which opens its own
        separate DB connection) just to read one config value."""
        import yaml
        from modules.power_monitor import PowerMonitor

        config_path = Path(__file__).resolve().parent.parent / "config" / "modules.yaml"
        raw = yaml.safe_load(config_path.read_text())
        forecasts = []
        for entry in raw.get("modules", []):
            if entry.get("class") != "modules.power_monitor.PowerMonitor" or not entry.get("enabled", True):
                continue
            params = entry.get("params", {})
            monitor = PowerMonitor(
                module_id=entry["id"], cell_id=entry["cell_id"], db_conn=self.db,
                array_name=params.get("array_name", entry["id"]),
                battery_capacity_wh=params.get("battery_capacity_wh", 0),
                low_soc_threshold_pct=params.get("low_soc_threshold_pct", 20),
            )
            forecast = monitor.forecast_soc_depletion()
            forecasts.append({"module_id": entry["id"], "array_name": params.get("array_name", entry["id"]),
                               "forecast": forecast})
        return {"forecasts": forecasts}

    def _tool_get_last_human_checkin(self) -> dict:
        row = self.db.execute(
            "SELECT * FROM human_checkins ORDER BY timestamp DESC LIMIT 1"
        ).fetchone()
        return {"last_checkin": dict(row) if row else None}

    def _tool_get_system_capabilities(self, module_id: str | None = None) -> dict:
        return {"capabilities": CapabilityRegistry.render_full(self.db, module_id=module_id)}

    def _tool_get_self_change_history(self, module_id: str | None = None, limit: int = 20) -> dict:
        return {"changes": CapabilityRegistry.get_change_history(self.db, module_id=module_id, limit=limit)}

    def _tool_create_config_snapshot(self, label: str, reason: str | None = None) -> dict:
        from core.backup_manager import BackupManager
        mgr = BackupManager(self.db)
        snapshot_id = mgr.create_snapshot(label, reason=reason)
        return {"snapshot_id": snapshot_id, "label": label}

    def _tool_list_config_snapshots(self) -> dict:
        rows = self.db.execute(
            "SELECT id, label, reason, created_at, is_auto_pre_update FROM config_snapshots ORDER BY created_at DESC"
        ).fetchall()
        return {"snapshots": [dict(r) for r in rows]}

    def _tool_restore_config_snapshot(self, snapshot_id: int) -> dict:
        from core.backup_manager import BackupManager
        mgr = BackupManager(self.db)
        return mgr.restore_snapshot(snapshot_id)

    def _tool_get_verification_coverage(self) -> dict:
        return CapabilityRegistry.get_verification_coverage(self.db)

    def _tool_run_self_diagnostics(self) -> dict:
        from core.self_audit import run_full_diagnostics
        return run_full_diagnostics(print_output=False)

    def _tool_get_recent_automated_actions(self, module_id: str | None = None, days: int = 7) -> dict:
        from core.action_log import get_recent_actions
        return {"actions": get_recent_actions(self.db, module_id=module_id, days=days)}

    def _tool_get_activity_journal(self, days: int = 7) -> dict:
        from core.activity_journal import ActivityJournal
        return {"journal": ActivityJournal(self.db).get_journal(days=days)}

    def _tool_get_control_loop_status(self) -> dict:
        from core.activity_journal import ActivityJournal
        return ActivityJournal(self.db).get_current_status()

    def _tool_get_upcoming_activity(self) -> dict:
        from core.activity_journal import ActivityJournal
        return {"upcoming": ActivityJournal(self.db).get_whats_next()}

    def _tool_get_greenhouse_report(self, days: int = 7) -> dict:
        from core.report_generator import ReportGenerator
        gen = ReportGenerator(self.db)
        return {"report": gen.generate_report(days=days)}

    def _tool_send_greenhouse_report(self, days: int = 7) -> dict:
        from core.report_generator import ReportGenerator
        gen = ReportGenerator(self.db)
        report_id = gen.generate_and_send(days=days)
        return {
            "report_id": report_id,
            "actually_emailed": bool(gen.notifier),
            "note": (
                "Saved and dispatched via the configured notifier." if gen.notifier else
                "Saved to daily_reports, but no notifier is configured on this assistant "
                "session — nothing was actually emailed. Tell the user this honestly rather "
                "than implying delivery happened."
            ),
        }

    def _tool_get_consumable_forecast(self, item_id: int) -> dict:
        from core.inventory import InventoryManager
        inv = InventoryManager(self.db)
        forecast = inv.forecast_depletion(item_id)
        return {"forecast": forecast}

    def _tool_record_human_checkin(self) -> dict:
        from core.deadmans_switch import DeadMansSwitchMonitor
        mgr = DeadMansSwitchMonitor(self.db)
        mgr.record_checkin(method="assistant_conversation")
        return {"checked_in": True}

    def _tool_get_hardware_needs_list(self) -> dict:
        return {
            "bom_summary": HardwareRegistry.render_bom(self.db, group_by_module=False),
            "items": HardwareRegistry.get_all(self.db),
        }

    def _tool_get_wiring_info(self, actuator_name: str) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        infra = InfrastructureRegistry(self.db)
        wiring = infra.get_wiring_for_actuator(actuator_name)
        return {"wiring": wiring}

    def _tool_get_plumbing_info(self, cell_id: int | None = None, actuator_name: str | None = None) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        infra = InfrastructureRegistry(self.db)
        if actuator_name:
            return {"plumbing": infra.get_plumbing_for_actuator(actuator_name)}
        if cell_id is not None:
            return {"plumbing": infra.get_plumbing_for_cell(cell_id)}
        return {"error": "provide cell_id or actuator_name"}

    def _tool_diagnose_alert(self, alert_id: int, create_task: bool = False) -> dict:
        from core.infrastructure_registry import InfrastructureRegistry
        from core.diagnostics import DiagnosticEngine
        from core.maintenance import MaintenanceManager
        infra = InfrastructureRegistry(self.db)
        maintenance = MaintenanceManager(self.db)
        engine = DiagnosticEngine(self.db, infra, maintenance=maintenance)
        return engine.diagnose_alert(alert_id, create_task=create_task)

    def _tool_get_expected_vs_actual_yield(self, planting_id: int) -> dict:
        from core.species_registry import SpeciesRegistry
        from core.bed_planting import BedPlantingManager
        species = SpeciesRegistry(self.db)
        bp = BedPlantingManager(self.db, species)
        return bp.get_expected_vs_actual(planting_id)

    def _tool_get_water_usage(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            "SELECT * FROM water_usage_events WHERE cell_id = ? AND timestamp >= datetime('now', ?) "
            "ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"water_usage": [dict(r) for r in rows]}

    def _tool_get_dosing_rationale(self, cell_id: int, days: int = 7) -> dict:
        rows = self.db.execute(
            "SELECT dose_type, timestamp, reading_before, rationale, triggered_by FROM dosing_events "
            "WHERE cell_id = ? AND timestamp >= datetime('now', ?) ORDER BY timestamp DESC",
            (cell_id, f"-{days} days"),
        ).fetchall()
        return {"dosing_events": [dict(r) for r in rows]}

    def _tool_get_bed_plantings(self, cell_id: int | None = None) -> dict:
        q = """
            SELECT bp.*, sp.common_name, sp.ph_min, sp.ph_max, sp.ec_min, sp.ec_max
            FROM bed_plantings bp JOIN species_profiles sp ON sp.id = bp.species_id
            WHERE bp.status = 'active'
        """
        params = ()
        if cell_id is not None:
            q += " AND bp.cell_id = ?"
            params = (cell_id,)
        rows = self.db.execute(q, params).fetchall()
        return {"plantings": [dict(r) for r in rows]}

    def _resolve_species_id(self, species_name: str) -> int | None:
        row = self.db.execute(
            "SELECT id FROM species_profiles WHERE common_name LIKE ?", (f"%{species_name}%",)
        ).fetchone()
        return row[0] if row else None

    def _bed_planting_manager(self):
        from core.bed_planting import BedPlantingManager
        from core.species_registry import SpeciesRegistry
        return BedPlantingManager(self.db, SpeciesRegistry(self.db))

    def _tool_record_planting(self, grow_bed_name: str, cell_id: int, species_name: str, variety: str | None = None) -> dict:
        species_id = self._resolve_species_id(species_name)
        if species_id is None:
            return {"error": f"No species profile found matching '{species_name}'. Use list_species to see options."}
        planting_id = self._bed_planting_manager().plant(grow_bed_name, cell_id, species_id, variety=variety)
        return {"planting_id": planting_id, "grow_bed_name": grow_bed_name, "species": species_name}

    def _tool_plan_planting(self, grow_bed_name: str, cell_id: int, species_name: str,
                              target_plant_date: str | None = None, variety: str | None = None) -> dict:
        species_id = self._resolve_species_id(species_name)
        if species_id is None:
            return {"error": f"No species profile found matching '{species_name}'. Use list_species to see options."}
        planting_id = self._bed_planting_manager().plan(
            grow_bed_name, cell_id, species_id, target_plant_date=target_plant_date, variety=variety,
        )
        return {"planting_id": planting_id, "grow_bed_name": grow_bed_name, "species": species_name,
                "status": "planned", "target_plant_date": target_plant_date}

    def _tool_convert_planting_to_active(self, planting_id: int, quantity_planted: int | None = None) -> dict:
        try:
            return self._bed_planting_manager().convert_to_active(planting_id, quantity_planted=quantity_planted)
        except ValueError as e:
            return {"error": str(e)}

    def _tool_get_planned_plantings(self, cell_id: int | None = None) -> dict:
        return {"planned_plantings": self._bed_planting_manager().get_planned_plantings(cell_id)}

    def _tool_mark_planting_harvested(self, planting_id: int) -> dict:
        self.db.execute("UPDATE bed_plantings SET status = 'harvested' WHERE id = ?", (planting_id,))
        self.db.commit()
        return {"planting_id": planting_id, "status": "harvested"}

    def _tool_mark_planting_failed(self, planting_id: int, notes: str | None = None) -> dict:
        self.db.execute("UPDATE bed_plantings SET status = 'failed', notes = ? WHERE id = ?", (notes, planting_id))
        self.db.commit()
        return {"planting_id": planting_id, "status": "failed"}

    def _tool_record_water_usage(self, cell_id: int, amount_gallons: float, reason: str,
                                   grow_bed_name: str | None = None) -> dict:
        cur = self.db.execute(
            "INSERT INTO water_usage_events (cell_id, grow_bed_name, amount_gallons, reason, triggered_by) "
            "VALUES (?, ?, ?, ?, 'manual_override')",
            (cell_id, grow_bed_name, amount_gallons, reason),
        )
        self.db.commit()
        return {"event_id": cur.lastrowid, "amount_gallons": amount_gallons, "reason": reason}

    def _tool_record_water_quality_test(self, cell_id: int, ammonia_ppm: float | None = None,
                                          nitrite_ppm: float | None = None, nitrate_ppm: float | None = None,
                                          notes: str | None = None) -> dict:
        from core.biofilter_model import BiofilterModel
        test_id = BiofilterModel(self.db).record_test(
            cell_id, ammonia_ppm=ammonia_ppm, nitrite_ppm=nitrite_ppm, nitrate_ppm=nitrate_ppm,
            tested_by="human via assistant", notes=notes,
        )
        return {"test_id": test_id, "cell_id": cell_id}

    def _tool_get_biofilter_cycle_status(self, cell_id: int) -> dict:
        from core.biofilter_model import BiofilterModel
        bm = BiofilterModel(self.db)
        return {
            "cycle_status": bm.get_cycle_status(cell_id),
            "livestock_readiness": bm.check_livestock_readiness(cell_id),
        }

    def _tool_get_irrigation_status(self) -> dict:
        from core.irrigation import IrrigationScheduler
        sched = IrrigationScheduler.from_config("config/irrigation_schedules.yaml", self.db)
        return {"schedules": sched.get_status()}

    def _tool_record_feeding(self, cell_id: int, amount: float, unit: str = "oz",
                               food_type: str | None = None, notes: str | None = None) -> dict:
        from core.fish_health import FishHealth
        event_id = FishHealth(self.db).record_feeding(cell_id, amount, unit=unit, food_type=food_type, notes=notes)
        return {"event_id": event_id, "cell_id": cell_id, "amount": amount, "unit": unit}

    def _tool_record_fish_mortality(self, cell_id: int, count: int, cause: str | None = None,
                                      notes: str | None = None) -> dict:
        from core.fish_health import FishHealth
        event_id = FishHealth(self.db).record_mortality(cell_id, count, cause=cause, notes=notes)
        return {"event_id": event_id, "cell_id": cell_id, "count": count}

    def _tool_record_fish_health_observation(self, cell_id: int, description: str,
                                               notes: str | None = None) -> dict:
        from core.fish_health import FishHealth
        event_id = FishHealth(self.db).record_health_observation(cell_id, description, notes=notes)
        return {"event_id": event_id, "cell_id": cell_id}

    def _tool_get_fish_health_summary(self, cell_id: int) -> dict:
        from core.fish_health import FishHealth
        fh = FishHealth(self.db)
        return {
            "feeding_history": fh.get_feeding_history(cell_id),
            "feeding_trend": fh.get_feeding_trend(cell_id),
            "mortality_history": fh.get_mortality_history(cell_id),
            "health_observations": fh.get_health_events(cell_id),
        }

    def _tool_get_pest_disease_info(self, name: str | None = None, organism_type: str | None = None) -> dict:
        from core.pest_disease import PestDisease
        pd = PestDisease(self.db)
        if name:
            return {"match": pd.find_knowledge_by_name(name)}
        return {"knowledge": pd.list_knowledge(organism_type)}

    def _tool_record_pest_disease_observation(self, cell_id: int, description: str,
                                                category: str = "other", severity: str | None = None,
                                                action_taken: str | None = None, notes: str | None = None) -> dict:
        from core.pest_disease import PestDisease
        obs_id = PestDisease(self.db).record_observation(
            cell_id, description, category=category, severity=severity,
            action_taken=action_taken, notes=notes,
        )
        return {"observation_id": obs_id, "cell_id": cell_id}

    def _tool_get_pest_disease_history(self, cell_id: int) -> dict:
        from core.pest_disease import PestDisease
        return {"observations": PestDisease(self.db).get_observation_history(cell_id)}

    def _tool_get_weather_status(self) -> dict:
        from core.weather_awareness import WeatherAwareness
        return {"last_check": WeatherAwareness(self.db).get_last_check()}

    def _tool_add_species(self, common_name: str, organism_type: str, scientific_name: str | None = None,
                            ph_min: float | None = None, ph_max: float | None = None,
                            ec_min: float | None = None, ec_max: float | None = None,
                            notes: str | None = None) -> dict:
        cur = self.db.execute(
            "INSERT INTO species_profiles (common_name, organism_type, scientific_name, "
            "ph_min, ph_max, ec_min, ec_max, notes, source) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'baseline')",
            (common_name, organism_type, scientific_name, ph_min, ph_max, ec_min, ec_max, notes),
        )
        self.db.commit()
        return {"species_id": cur.lastrowid, "common_name": common_name}

    def _tool_update_maintenance_task_status(self, task_id: int, status: str) -> dict:
        completed_at = "datetime('now')" if status == "done" else "NULL"
        self.db.execute(
            f"UPDATE maintenance_tasks SET status = ?, completed_at = {completed_at} WHERE id = ?",
            (status, task_id),
        )
        self.db.commit()
        return {"task_id": task_id, "status": status}

    def _tool_assign_maintenance_task(self, task_id: int, assigned_to: str) -> dict:
        self.db.execute("UPDATE maintenance_tasks SET assigned_to = ? WHERE id = ?", (assigned_to, task_id))
        self.db.commit()
        return {"task_id": task_id, "assigned_to": assigned_to}

    def _tool_deny_parameter_change(self, proposal_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.deny_parameter_change(proposal_id)
        return {"proposal_id": proposal_id, "status": "denied"}

    def _tool_complete_experiment_now(self, experiment_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        return mgr.complete_experiment(experiment_id)

    def _tool_get_deadmans_switch_status(self) -> dict:
        from core.deadmans_switch import DeadMansSwitchMonitor
        mgr = DeadMansSwitchMonitor(self.db)
        return mgr.get_status()

    def _tool_get_species_profile(self, species_name: str) -> dict:
        row = self.db.execute(
            "SELECT * FROM species_profiles WHERE common_name LIKE ?", (f"%{species_name}%",)
        ).fetchone()
        return {"profile": dict(row) if row else None}

    def _tool_list_species(self) -> dict:
        rows = self.db.execute("SELECT common_name, organism_type, ph_min, ph_max, ec_min, ec_max FROM species_profiles").fetchall()
        return {"species": [dict(r) for r in rows]}

    def _tool_propose_experiment(self, cell_id: int, hypothesis: str, variable_changed: str,
                                   baseline_value: float, test_value: float, duration_days: int = 14) -> dict:
        from datetime import datetime, timedelta
        planned_end = (datetime.utcnow() + timedelta(days=duration_days)).isoformat()
        cur = self.db.execute(
            "INSERT INTO experiments (cell_id, hypothesis, variable_changed, baseline_value, "
            "test_value, planned_end_date, created_by) VALUES (?, ?, ?, ?, ?, ?, 'assistant')",
            (cell_id, hypothesis, variable_changed, baseline_value, test_value, planned_end),
        )
        self.db.commit()
        return {"experiment_id": cur.lastrowid, "status": "proposed", "planned_end_date": planned_end}

    def _tool_start_experiment(self, experiment_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.start_experiment(experiment_id)
        return {"experiment_id": experiment_id, "status": "running"}

    def _tool_get_active_experiments(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM experiments WHERE status IN ('proposed', 'approved', 'running')"
        ).fetchall()
        return {"experiments": [dict(r) for r in rows]}

    def _tool_get_pending_parameter_changes(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM parameter_change_proposals WHERE status = 'proposed'"
        ).fetchall()
        return {"proposals": [dict(r) for r in rows]}

    def _tool_approve_parameter_change(self, proposal_id: int) -> dict:
        from core.experiment_manager import ExperimentManager
        mgr = ExperimentManager(self.db)
        mgr.approve_parameter_change(proposal_id)
        return {"proposal_id": proposal_id, "status": "approved"}

    def _tool_get_active_help_requests(self) -> dict:
        rows = self.db.execute(
            "SELECT * FROM help_requests WHERE resolved = 0 ORDER BY created_at DESC"
        ).fetchall()
        return {"help_requests": [dict(r) for r in rows]}

    def _tool_acknowledge_help_request(self, request_id: int) -> dict:
        self.db.execute(
            "UPDATE help_requests SET acknowledged = 1, acknowledged_at = datetime('now') WHERE id = ?",
            (request_id,),
        )
        self.db.commit()
        return {"request_id": request_id, "acknowledged": True}

    def _tool_get_unpaired_devices(self) -> dict:
        rows = self.db.execute(
            "SELECT hardware_id, role, first_seen FROM device_registrations WHERE status = 'needs_attention'"
        ).fetchall()
        return {"unpaired_devices": [dict(r) for r in rows]}

    def _tool_get_device_setup_instructions(self, role: str) -> dict:
        from core.device_registry import DeviceRegistry
        registry = DeviceRegistry(self.db)
        return {"instructions": registry.get_setup_instructions(role)}

    def _tool_pair_device(self, hardware_id: str, role: str) -> dict:
        from core.device_registry import DeviceRegistry
        registry = DeviceRegistry(self.db)
        return registry.pair_device(hardware_id, role)

    def _tool_get_to_order_list(self) -> dict:
        # Delegates to InventoryManager rather than a separate hand-copied
        # query — this tool used to reimplement its own SQL that had quietly
        # drifted from core/inventory.py's real version and was missing
        # supplier_url entirely, so a human asking the assistant "what needs
        # ordering" could never get a sourcing link even when one was
        # recorded (found 2026-08-31 while working the "enrich order
        # proposals with real sourcing info" punch-list item). Delegating
        # means the two can't drift apart again.
        from core.inventory import InventoryManager
        return {"pending_orders": InventoryManager(self.db).get_to_order_list()}

    def _tool_approve_order(self, order_id: int) -> dict:
        self.db.execute(
            "UPDATE inventory_orders SET status = 'approved' WHERE id = ? AND status = 'proposed'",
            (order_id,),
        )
        self.db.commit()
        return {"order_id": order_id, "status": "approved"}

    def _tool_deny_order(self, order_id: int, reason: str | None = None) -> dict:
        notes_suffix = f" | denied: {reason}" if reason else " | denied"
        self.db.execute(
            "UPDATE inventory_orders SET status = 'denied', "
            "notes = COALESCE(notes, '') || ? WHERE id = ? AND status = 'proposed'",
            (notes_suffix, order_id),
        )
        self.db.commit()
        return {"order_id": order_id, "status": "denied"}

    def _tool_get_inventory_status(self) -> dict:
        rows = self.db.execute(
            "SELECT name, category, quantity_on_hand, unit, reorder_threshold FROM inventory_items"
        ).fetchall()
        return {"inventory": [dict(r) for r in rows]}

    def _tool_get_low_stock_items(self) -> dict:
        rows = self.db.execute(
            "SELECT name, category, quantity_on_hand, reorder_threshold, unit, supplier "
            "FROM inventory_items WHERE quantity_on_hand <= reorder_threshold"
        ).fetchall()
        return {"low_stock": [dict(r) for r in rows]}

    def _tool_get_open_maintenance_tasks(self, priority: str | None = None) -> dict:
        q = "SELECT * FROM maintenance_tasks WHERE status IN ('open', 'in_progress')"
        params = ()
        if priority:
            q += " AND priority = ?"
            params = (priority,)
        rows = self.db.execute(q, params).fetchall()
        return {"tasks": [dict(r) for r in rows]}

    def _tool_create_maintenance_task(
        self, title: str, task_type: str, priority: str = "medium",
        description: str | None = None, assigned_to: str | None = None,
        due_date: str | None = None,
    ) -> dict:
        cur = self.db.execute(
            """
            INSERT INTO maintenance_tasks
            (title, description, task_type, priority, assigned_to, due_date, created_by)
            VALUES (?, ?, ?, ?, ?, ?, 'assistant')
            """,
            (title, description, task_type, priority, assigned_to, due_date),
        )
        self.db.commit()
        return {"created_task_id": cur.lastrowid, "title": title, "priority": priority}

    def _tool_get_revenue_summary(self, days: int = 30) -> dict:
        from core.finance_tracker import FinanceTracker
        return FinanceTracker(self.db).get_revenue_summary(days)

    def _tool_record_revenue(self, item: str, quantity: float, unit: str, unit_price: float,
                               cell_id: int | None = None, channel: str | None = None,
                               notes: str | None = None) -> dict:
        from core.finance_tracker import FinanceTracker
        txn_id = FinanceTracker(self.db).record_revenue(
            item, quantity, unit, unit_price, cell_id=cell_id, channel=channel, notes=notes,
        )
        return {"transaction_id": txn_id, "item": item, "total_amount": quantity * unit_price}

    def _tool_get_cost_summary(self, days: int = 30) -> dict:
        from core.finance_tracker import FinanceTracker
        return FinanceTracker(self.db).get_cost_summary(days)

    def _tool_get_profitability_summary(self, days: int = 30) -> dict:
        from core.finance_tracker import FinanceTracker
        return FinanceTracker(self.db).get_profitability_summary(days)


class AnthropicGreenhouseAssistant(_BaseGreenhouseAssistant):
    """Cloud-backed variant using the Anthropic API. Kept deliberately —
    for re-running the model bake-off against `GreenhouseAssistant`'s
    local model, and for anyone who explicitly wants cloud — but this is
    NOT the default and should not become the path of least resistance;
    see the module docstring and docs/OFFLINE_ASSISTANT_PLAN.md."""

    def __init__(self, db_path: str, api_key: str | None = None):
        super().__init__(db_path)
        import anthropic  # lazy — see the module docstring for why
        self.client = anthropic.Anthropic(api_key=api_key)

    def ask(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})

        # Gated once per user turn, from the message that started it — not
        # re-evaluated per tool-calling round-trip within this turn, so a
        # multi-step reasoning chain doesn't lose access to a tool it
        # legitimately needed just because a later intermediate step's
        # wording drifted off the original keywords.
        domains = relevant_domains(message, self.db)
        active_tools = tools_for_domains(domains)
        if len(active_tools) < len(TOOLS):
            logger.debug(
                "Gated tools for this turn: %d/%d (domains: %s)",
                len(active_tools), len(TOOLS), sorted(domains),
            )

        while True:
            response = self.client.messages.create(
                model=ANTHROPIC_MODEL,
                max_tokens=1024,
                system=self._system_prompt(),
                tools=active_tools,
                messages=self.history,
            )

            if response.stop_reason != "tool_use":
                final_text = "".join(
                    block.text for block in response.content
                    if block.type == "text"
                )
                self.history.append({"role": "assistant", "content": response.content})
                return final_text

            # Handle tool calls, feed results back, loop again
            self.history.append({"role": "assistant", "content": response.content})
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
            safe_blocks, skipped_blocks = split_safe_tool_calls(tool_use_blocks)

            if skipped_blocks:
                logger.warning(
                    "Skipped %d destructive tool call(s) bundled with %d other call(s) "
                    "in one reply: %s",
                    len(skipped_blocks), len(safe_blocks), [b.name for b in skipped_blocks],
                )

            tool_results = []
            for block in safe_blocks:
                result = self._dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(result, default=str),
                })
            for block in skipped_blocks:
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps({
                        "skipped": True,
                        "reason": (
                            f"'{block.name}' is a destructive action and was bundled with "
                            "other tool calls in the same reply, so it was NOT executed as "
                            "a safety precaution. Tell the user this plainly and ask them to "
                            "request it again on its own if they still want it done."
                        ),
                    }),
                })
            self.history.append({"role": "user", "content": tool_results})


class GreenhouseAssistant(_BaseGreenhouseAssistant):
    """The default assistant — local-model-backed via Ollama, no cloud
    API, no API key, no internet dependency. This is what
    `python assistant/greenhouse_assistant.py` gives you, and what every
    other part of this codebase should construct unless there's a
    specific, explicit reason to reach for AnthropicGreenhouseAssistant
    instead. See the module docstring and docs/OFFLINE_ASSISTANT_PLAN.md."""

    def __init__(self, db_path: str, model: str = OLLAMA_MODEL, host: str = OLLAMA_HOST):
        super().__init__(db_path)
        self.model = model
        self.host = host

    def ask_with_cloud_escalation(self, question: str, api_key: str | None = None) -> str:
        """Explicit, human-triggered opt-in to route ONE question to
        AnthropicGreenhouseAssistant instead of the local default —
        resolves docs/OFFLINE_ASSISTANT_PLAN.md's own flagged, previously
        undecided open question. Local stays the unconditional default
        for everything else; this is never automatic and never called
        by the local model's own reasoning — only a human explicitly
        asking for it (see the REPL's /cloud prefix below) reaches this
        method at all.

        A fresh, short conversation for just this one question (no
        shared history with the ongoing local session — merging two
        different backends' conversation state is a real correctness
        trap, not a shortcut worth taking for a rarely-used escape
        hatch) but the SAME db, so the cloud model answers from real,
        current data via its own tool calls, not stale context.

        Fails honestly, never silently: if the cloud path genuinely
        isn't reachable (no API key, no network, a real API error),
        says so plainly rather than quietly answering locally and
        letting the user believe they got a cloud answer they didn't."""
        import os
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return (
                "Cloud escalation requires ANTHROPIC_API_KEY to be set, and it isn't right now — "
                "this question was NOT answered by the cloud model. Set the key and try again, "
                "or ask without cloud escalation to use the local model."
            )
        try:
            cloud = AnthropicGreenhouseAssistant(db_path=self.db_path, api_key=key)
            return cloud.ask(question)
        except Exception as e:
            logger.warning("Cloud escalation failed: %s", e)
            return f"Cloud escalation failed ({e}) — this question was NOT answered by the cloud model."

    def ask(self, message: str) -> str:
        self.history.append({"role": "user", "content": message})

        active_tools = tools_for_domains(relevant_domains(message, self.db))
        ollama_tools = [_anthropic_tool_to_ollama(t) for t in active_tools]

        while True:
            response = self._call_ollama(ollama_tools)
            msg = response.get("message", {})
            raw_tool_calls = msg.get("tool_calls") or []

            if not raw_tool_calls:
                text = msg.get("content", "")
                self.history.append({"role": "assistant", "content": text})
                return text

            self.history.append({
                "role": "assistant",
                "content": msg.get("content", ""),
                "tool_calls": raw_tool_calls,
            })

            tool_calls = _parse_ollama_tool_calls(raw_tool_calls)
            safe_calls, skipped_calls = split_safe_tool_calls(tool_calls)

            if skipped_calls:
                logger.warning(
                    "Skipped %d destructive tool call(s) bundled with %d other call(s) "
                    "in one reply: %s",
                    len(skipped_calls), len(safe_calls), [c.name for c in skipped_calls],
                )

            for call in safe_calls:
                result = self._dispatch_tool(call.name, call.input)
                self.history.append({"role": "tool", "content": json.dumps(result, default=str)})
            for call in skipped_calls:
                self.history.append({
                    "role": "tool",
                    "content": json.dumps({
                        "skipped": True,
                        "reason": (
                            f"'{call.name}' is a destructive action and was bundled with "
                            "other tool calls in the same reply, so it was NOT executed as "
                            "a safety precaution. Tell the user this plainly and ask them to "
                            "request it again on its own if they still want it done."
                        ),
                    }),
                })

    def _call_ollama(self, tools: list[dict]) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": self._system_prompt()}] + self.history,
            "tools": tools,
            "stream": False,
            "options": {"temperature": 0},  # determinism — see docs/OFFLINE_ASSISTANT_PLAN.md
            "keep_alive": -1,               # never idle-unload mid-conversation
        }
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=OLLAMA_REQUEST_TIMEOUT_SECONDS) as resp:
                return json.loads(resp.read())
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"Could not reach Ollama at {self.host} — is it running? "
                f"(systemctl --user status ollama). Original error: {e}"
            ) from e


if __name__ == "__main__":
    import sys

    db_path = sys.argv[1] if len(sys.argv) > 1 else "mia_homestead.db"

    if "--cloud" in sys.argv:
        import os
        assistant = AnthropicGreenhouseAssistant(
            db_path=db_path,
            api_key=os.environ.get("ANTHROPIC_API_KEY"),
        )
        print("MIA Homestead assistant ready (cloud: Anthropic). Ctrl+C to exit.")
    else:
        assistant = GreenhouseAssistant(db_path=db_path)
        print(f"MIA Homestead assistant ready (local model: {OLLAMA_MODEL}, no cloud API). "
              f"Prefix a question with /cloud to explicitly send just that one question to the "
              f"cloud model instead (requires ANTHROPIC_API_KEY). Ctrl+C to exit.")

    while True:
        try:
            q = input("\nyou: ")
            if q.startswith("/cloud ") and isinstance(assistant, GreenhouseAssistant):
                print(f"\ngreenhouse (cloud escalation): {assistant.ask_with_cloud_escalation(q[len('/cloud '):])}")
            else:
                print(f"\ngreenhouse: {assistant.ask(q)}")
        except KeyboardInterrupt:
            break
