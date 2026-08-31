-- MIA Homestead Node — Schema v0.1
-- SQLite. Designed to run locally on the greenhouse Pi, sync summaries to
-- MIA Home. Every table assumes this node may run for weeks with no human
-- interaction — nothing here should require manual cleanup to keep working.

PRAGMA foreign_keys = ON;

-- ============ TOPOLOGY ============

CREATE TABLE cells (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,                 -- e.g. "Cell A"
    description TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE tanks (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    name TEXT NOT NULL,
    capacity_gallons REAL,
    species TEXT,                       -- e.g. "tilapia"
    stocked_date TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE grow_beds (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    name TEXT NOT NULL,
    sqft REAL,
    media_type TEXT,                    -- e.g. "expanded clay", "DWC"
    created_at TEXT DEFAULT (datetime('now'))
);

-- ============ SENSORS & READINGS ============

CREATE TABLE sensors (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    tank_id INTEGER REFERENCES tanks(id),      -- nullable, e.g. air sensors
    type TEXT NOT NULL,                        -- 'ph','ec','do','temp_water',
                                                -- 'temp_air','humidity','level',
                                                -- 'flow','light','co2'
    unit TEXT,
    location_note TEXT,
    install_date TEXT,
    calibration_due TEXT,
    active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY,
    sensor_id INTEGER NOT NULL REFERENCES sensors(id),
    timestamp TEXT DEFAULT (datetime('now')),
    value REAL,
    is_stale INTEGER DEFAULT 0,
    is_out_of_range INTEGER DEFAULT 0
);
CREATE INDEX idx_readings_sensor_time ON sensor_readings(sensor_id, timestamp);

-- ============ ACTUATORS ============

CREATE TABLE actuators (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    type TEXT NOT NULL,                 -- 'dosing_pump','circulation_pump',
                                         -- 'aerator','valve','heater','fan'
    name TEXT NOT NULL,
    safe_default_state TEXT NOT NULL,   -- 'off','on' — what MCU falls back to
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE actuator_events (
    id INTEGER PRIMARY KEY,
    actuator_id INTEGER NOT NULL REFERENCES actuators(id),
    timestamp TEXT DEFAULT (datetime('now')),
    action TEXT NOT NULL,               -- 'on','off','pulse'
    duration_seconds REAL,
    triggered_by TEXT NOT NULL          -- 'auto_control','manual_override',
                                         -- 'safety_fallback','schedule'
);

-- ============ DOSING ============

CREATE TABLE dosing_limits (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    dose_type TEXT NOT NULL,            -- 'ph_up','ph_down','nutrient_a', etc
    max_per_dose_ml REAL NOT NULL,
    max_per_day_ml REAL NOT NULL,
    min_interval_minutes INTEGER NOT NULL
);

CREATE TABLE dosing_events (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    timestamp TEXT DEFAULT (datetime('now')),
    dose_type TEXT NOT NULL,
    amount_ml REAL,                     -- nullable: MCU pulse duration determines actual
                                         -- volume; Pi-side software logs an estimate, not a
                                         -- flow-metered exact figure, until real flow
                                         -- metering hardware exists
    reading_before REAL,
    reading_after REAL,                 -- filled in on next confirmed reading
    rationale TEXT,                     -- human-readable "why" — e.g. "pH 6.3 below
                                         -- target range 6.6-7.2, correcting toward target"
    triggered_by TEXT NOT NULL
);

-- ============ WATER QUALITY BASELINE (well water etc) ============

CREATE TABLE water_source_tests (
    id INTEGER PRIMARY KEY,
    source TEXT NOT NULL,               -- 'well','municipal','rain'
    test_date TEXT DEFAULT (datetime('now')),
    ph REAL,
    hardness_ppm REAL,
    iron_ppm REAL,
    chlorine_ppm REAL,
    notes TEXT
);

-- ============ POWER ============

CREATE TABLE power_telemetry (
    id INTEGER PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    source TEXT NOT NULL,               -- 'solar','battery','generator','grid'
    watts REAL,
    battery_soc_percent REAL,
    notes TEXT
);
CREATE INDEX idx_power_time ON power_telemetry(timestamp);

-- ============ YIELD TRACKING ============

CREATE TABLE yield_events (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    timestamp TEXT DEFAULT (datetime('now')),
    yield_type TEXT NOT NULL,           -- 'harvest_produce','harvest_fish'
    item TEXT NOT NULL,                 -- e.g. 'lettuce','tilapia'
    quantity REAL,
    unit TEXT,                          -- 'lb','count','oz'
    notes TEXT
);

-- ============ ALERTS ============

CREATE TABLE alerts (
    id INTEGER PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),  -- when this condition FIRST fired — never
                                         -- updated on repeat, so backup_manager's
                                         -- "critical alerts since applied_at" spike
                                         -- check keeps meaning "genuinely new since
                                         -- the change", not "still-ongoing pre-existing
                                         -- issue re-counted"
    severity TEXT NOT NULL,             -- 'info','warning','critical'
    source TEXT,                        -- cell/sensor/actuator ref, free text
    message TEXT NOT NULL,
    occurrence_count INTEGER DEFAULT 1, -- bumped, not re-inserted, each time the same
                                         -- (source, message) fires again while still
                                         -- unresolved — see contract._raise_alert()
    last_seen TEXT DEFAULT (datetime('now')),  -- most recent occurrence; use this for
                                         -- "what's relevant right now" ordering,
                                         -- timestamp for "when did this start"
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT,
    resolved INTEGER DEFAULT 0,
    resolved_at TEXT
);
CREATE INDEX idx_alerts_unresolved ON alerts(resolved, severity);

-- ============ INVENTORY ============

CREATE TABLE inventory_items (
    id INTEGER PRIMARY KEY,
    sku TEXT UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,             -- 'sensor','spare_part','chemical',
                                         -- 'consumable','equipment'
    unit TEXT,                          -- 'each','ml','L','g'
    quantity_on_hand REAL DEFAULT 0,
    reorder_threshold REAL DEFAULT 0,
    reorder_quantity REAL DEFAULT 0,
    unit_cost REAL,
    supplier TEXT,
    supplier_url TEXT,
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE inventory_transactions (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    timestamp TEXT DEFAULT (datetime('now')),
    change_qty REAL NOT NULL,           -- negative = consumed, positive = restocked
    reason TEXT NOT NULL,               -- 'dosing_consumption','restock',
                                         -- 'manual_adjustment','used_in_repair'
    reference TEXT                      -- free text or id, e.g. 'dosing_event:42'
);

CREATE TABLE inventory_orders (
    id INTEGER PRIMARY KEY,
    item_id INTEGER NOT NULL REFERENCES inventory_items(id),
    quantity REAL NOT NULL,
    ordered_at TEXT DEFAULT (datetime('now')),
    expected_arrival TEXT,
    received_at TEXT,
    status TEXT DEFAULT 'ordered',      -- 'ordered','received','cancelled'
    cost REAL,
    notes TEXT
);

-- ============ REVENUE & EXPENSES ============

CREATE TABLE revenue_transactions (
    id INTEGER PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    cell_id INTEGER REFERENCES cells(id),
    yield_event_id INTEGER REFERENCES yield_events(id),
    item TEXT NOT NULL,
    quantity REAL,
    unit TEXT,
    unit_price REAL,
    total_amount REAL NOT NULL,
    channel TEXT,                       -- 'farmers_market','csa','direct','online'
    notes TEXT
);

CREATE TABLE expense_transactions (
    id INTEGER PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    category TEXT NOT NULL,             -- 'feed','chemicals','parts','utilities','other'
    amount REAL NOT NULL,
    vendor TEXT,
    notes TEXT
);

-- ============ MAINTENANCE ============

CREATE TABLE maintenance_tasks (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    task_type TEXT NOT NULL,            -- 'repair','replacement','calibration',
                                         -- 'inspection','other'
    priority TEXT DEFAULT 'medium',     -- 'low','medium','high','critical'
    status TEXT DEFAULT 'open',         -- 'open','in_progress','done','cancelled'
    related_asset_type TEXT,            -- 'sensor','actuator','structure','other'
    related_asset_id INTEGER,
    assigned_to TEXT,
    created_by TEXT DEFAULT 'human',    -- 'human','system','assistant'
    created_at TEXT DEFAULT (datetime('now')),
    due_date TEXT,
    completed_at TEXT
);
CREATE INDEX idx_maintenance_open ON maintenance_tasks(status, priority);

CREATE TABLE maintenance_schedules (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    task_type TEXT NOT NULL,
    related_asset_type TEXT,
    related_asset_id INTEGER,
    interval_days INTEGER NOT NULL,
    last_generated_at TEXT,
    next_due_at TEXT NOT NULL,
    auto_create INTEGER DEFAULT 1
);

-- ============ SELF-PRESERVATION / HELP REQUESTS ============

CREATE TABLE help_requests (
    id INTEGER PRIMARY KEY,
    created_at TEXT DEFAULT (datetime('now')),
    cell_id INTEGER REFERENCES cells(id),
    trigger_summary TEXT NOT NULL,       -- what's critical, machine-readable
    message TEXT NOT NULL,               -- what the greenhouse actually says
    acknowledged INTEGER DEFAULT 0,
    acknowledged_at TEXT,
    resolved INTEGER DEFAULT 0,
    resolved_at TEXT,
    last_nudge_at TEXT
);

-- ============ DEVICE REGISTRY (plug-and-play MCUs) ============

CREATE TABLE device_registrations (
    id INTEGER PRIMARY KEY,
    hardware_id TEXT UNIQUE NOT NULL,    -- MCU's own serial/chip id, not human-assigned
    role TEXT,                            -- matches a role id in config/devices/roles/*.yaml
    cell_id INTEGER REFERENCES cells(id),
    status TEXT DEFAULT 'unpaired',       -- 'unpaired','paired','needs_attention'
    first_seen TEXT DEFAULT (datetime('now')),
    last_seen TEXT DEFAULT (datetime('now')),
    paired_at TEXT
);

-- ============ SPECIES KNOWLEDGE BASE ============
-- Seeded with baseline horticultural/aquaculture data, refined over
-- time by the experiment system below. This is the "what does this
-- organism actually want" reference — separate from what a cell is
-- CURRENTLY targeting (that's target_overrides, further down).

CREATE TABLE species_profiles (
    id INTEGER PRIMARY KEY,
    common_name TEXT NOT NULL,
    organism_type TEXT NOT NULL,        -- 'plant' or 'fish'
    scientific_name TEXT,
    ph_min REAL, ph_max REAL,
    ec_min REAL, ec_max REAL,           -- uS/cm
    temp_water_min REAL, temp_water_max REAL,  -- F
    temp_air_min REAL, temp_air_max REAL,
    days_to_maturity INTEGER,
    notes TEXT,
    source TEXT DEFAULT 'baseline',     -- 'baseline' or 'experiment_derived'
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ============ WHAT'S PLANTED WHERE ============

CREATE TABLE bed_plantings (
    id INTEGER PRIMARY KEY,
    grow_bed_name TEXT NOT NULL,        -- matches grow_beds.name
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    species_id INTEGER NOT NULL REFERENCES species_profiles(id),
    variety TEXT,
    quantity_planted INTEGER,           -- how many plants/starts went in
    expected_yield_amount REAL,         -- what a normal harvest of this many should produce
    expected_yield_unit TEXT,
    planted_date TEXT DEFAULT (datetime('now')),
    expected_harvest_date TEXT,
    status TEXT DEFAULT 'active',       -- 'active','harvested','failed'
    notes TEXT
);
CREATE INDEX idx_bed_plantings_active ON bed_plantings(cell_id, status);

-- ============ ACTIVE TARGET OVERRIDES ============
-- What a cell's control loop is ACTUALLY targeting right now, as
-- opposed to its config-file defaults. Read live every control cycle
-- by AquaponicsCell — this is what makes experiments possible without
-- restarting the process, and what makes "the AI adjusts its own
-- targets over time" a real, auditable data trail instead of a
-- silent code change.

CREATE TABLE target_overrides (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    param_name TEXT NOT NULL,           -- 'ph_target_min','ph_target_max','ec_target_min','ec_target_max'
    value REAL NOT NULL,
    set_by TEXT NOT NULL,               -- 'experiment','manual'
    reference_id INTEGER,               -- experiment id, if set_by='experiment'
    set_at TEXT DEFAULT (datetime('now')),
    active INTEGER DEFAULT 1,
    UNIQUE(cell_id, param_name, active)
);

-- ============ EXPERIMENTS ============
-- Never auto-applies to the control loop without going through
-- start_experiment() -> a target_overrides row -> and even the
-- CONCLUSION (adopt this permanently) requires human approval via the
-- same queue pattern as inventory ordering. Changing dosing targets is
-- safety-relevant; it doesn't get to happen silently.

CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    hypothesis TEXT NOT NULL,
    variable_changed TEXT NOT NULL,     -- matches a target_overrides param_name
    baseline_value REAL NOT NULL,
    test_value REAL NOT NULL,
    status TEXT DEFAULT 'proposed',     -- 'proposed','approved','running','completed','aborted'
    proposed_at TEXT DEFAULT (datetime('now')),
    started_at TEXT,
    planned_end_date TEXT,
    completed_at TEXT,
    result_summary TEXT,
    suggested_action TEXT,              -- 'adopt','revert','inconclusive'
    created_by TEXT DEFAULT 'human'     -- 'human','assistant'
);

-- ============ PARAMETER CHANGE APPROVAL QUEUE ============
-- Where a completed experiment's "adopt this permanently" recommendation
-- waits for a human decision, same pattern as inventory_orders.

CREATE TABLE parameter_change_proposals (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    param_name TEXT NOT NULL,
    current_value REAL NOT NULL,
    proposed_value REAL NOT NULL,
    rationale TEXT NOT NULL,
    status TEXT DEFAULT 'proposed',     -- 'proposed','approved','denied'
    proposed_at TEXT DEFAULT (datetime('now')),
    decided_at TEXT
);

-- ============ INFRASTRUCTURE KNOWLEDGE ============
-- Wiring lives in config/devices/roles/*.yaml (relay_channel,
-- wiring_rationale per control) — no separate table needed, it's read
-- live from those files by infrastructure_registry.py. Plumbing gets
-- its own table since it's synced from config/infrastructure/plumbing.yaml
-- and queried more often (diagnostics cross-reference it per alert).

CREATE TABLE plumbing_map (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    segment_name TEXT NOT NULL,
    from_component TEXT NOT NULL,
    to_component TEXT NOT NULL,
    pipe_diameter_in REAL,
    flow_direction TEXT,
    driven_by_actuator TEXT,
    rationale TEXT,
    notes TEXT,
    UNIQUE(cell_id, segment_name)
);

-- ============ WATER USAGE TRACKING ============

CREATE TABLE water_usage_events (
    id INTEGER PRIMARY KEY,
    cell_id INTEGER NOT NULL REFERENCES cells(id),
    grow_bed_name TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    amount_gallons REAL NOT NULL,
    reason TEXT NOT NULL,               -- e.g. 'scheduled_watering','moisture_triggered','manual_topoff'
    triggered_by TEXT DEFAULT 'auto_control'
);

-- ============ HARDWARE NEEDS REGISTRY ============
-- Populated at startup from every module's describe_hardware_requirements().
-- This is the running BOM — see contracts/capability.py and
-- core/hardware_registry.py. Never reconstructed after the fact.

CREATE TABLE hardware_requirements (
    id INTEGER PRIMARY KEY,
    module_id TEXT NOT NULL,
    item TEXT NOT NULL,
    category TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    purpose TEXT NOT NULL,
    est_unit_cost REAL,
    notes TEXT,
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(module_id, item)
);

-- ============ BACKUPS & UPDATE TRACKING ============

CREATE TABLE backups (
    id INTEGER PRIMARY KEY,
    path TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    label TEXT,
    reason TEXT,                        -- 'manual','pre_update','scheduled'
    git_commit TEXT,
    db_size_bytes INTEGER,
    restored_at TEXT                    -- set if this backup was ever restored FROM
);

CREATE TABLE system_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at TEXT DEFAULT (datetime('now'))
);

-- ============ AUTOMATED ACTION LOG ============
-- Uniform "why did you do that" for non-dosing automated actions —
-- dosing already has rationale via dosing_events; this covers
-- load-shedding, beacon triggers, and anything else automated that
-- doesn't already have its own rationale field.

CREATE TABLE automated_action_log (
    id INTEGER PRIMARY KEY,
    module_id TEXT NOT NULL,
    action TEXT NOT NULL,
    rationale TEXT NOT NULL,
    timestamp TEXT DEFAULT (datetime('now'))
);

-- ============ DEAD-MAN'S-SWITCH STATE ============

CREATE TABLE deadmans_switch_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- single row, singleton config/state
    escalation_level INTEGER DEFAULT 0,     -- 0=none, 1=primary notified, 2=secondary notified
    last_escalated_at TEXT
);
INSERT INTO deadmans_switch_state (id, escalation_level) VALUES (1, 0);

-- ============ PERIODIC SELF-REPORTS ============

CREATE TABLE daily_reports (
    id INTEGER PRIMARY KEY,
    generated_at TEXT DEFAULT (datetime('now')),
    content TEXT NOT NULL
);

-- ============ CONFIG BACKUP & ROLLBACK ============

CREATE TABLE config_snapshots (
    id INTEGER PRIMARY KEY,
    label TEXT NOT NULL,
    reason TEXT,
    git_commit TEXT,
    snapshot_dir TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    is_auto_pre_update INTEGER DEFAULT 0
);

CREATE TABLE update_watches (
    id INTEGER PRIMARY KEY,
    pre_update_snapshot_id INTEGER NOT NULL REFERENCES config_snapshots(id),
    applied_at TEXT DEFAULT (datetime('now')),
    validation_window_minutes INTEGER DEFAULT 30,
    critical_alert_baseline INTEGER DEFAULT 0,
    critical_alert_threshold INTEGER DEFAULT 2,
    status TEXT DEFAULT 'watching',   -- 'watching','confirmed_good','auto_rolled_back'
    resolved_at TEXT,
    resolution_note TEXT
);

-- ============ CODE DEPLOY BACKUP & ROLLBACK ============
-- Same propose/watch/auto-revert shape as config_snapshots/update_watches
-- above, applied to CODE (git commits) instead of config files — see
-- core/deploy_manager.py. A separate table pair rather than reusing the
-- config ones: config_snapshots' pre_update_snapshot_id/snapshot_dir
-- shape is about restoring files from a directory copy, which doesn't
-- fit "check out a different git commit" cleanly, and this project's
-- own convention (core/finance_manager.py vs core/homestead_manager.py)
-- is a sibling table/module per domain rather than forcing one shape to
-- cover two.

CREATE TABLE code_deploys (
    id INTEGER PRIMARY KEY,
    git_commit TEXT NOT NULL,
    note TEXT,
    marked_good_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE code_update_watches (
    id INTEGER PRIMARY KEY,
    rollback_git_commit TEXT NOT NULL,   -- the last-known-good commit to revert TO
    applied_at TEXT DEFAULT (datetime('now')),
    validation_window_minutes INTEGER DEFAULT 30,
    critical_alert_baseline INTEGER DEFAULT 0,
    critical_alert_threshold INTEGER DEFAULT 2,
    status TEXT DEFAULT 'watching',   -- 'watching','confirmed_good','auto_rolled_back'
    resolved_at TEXT,
    resolution_note TEXT
);

-- ============ SELF-UNDERSTANDING CHANGELOG ============
-- Every time a module's declared capability or hardware needs differ
-- from what was stored last time, that's logged here — a real,
-- queryable history of how the system's self-understanding has
-- changed as the code itself changed. Populated automatically by
-- capability_registry.py and hardware_registry.py on every registration.

CREATE TABLE system_changelog (
    id INTEGER PRIMARY KEY,
    module_id TEXT NOT NULL,
    change_type TEXT NOT NULL,   -- 'first_registered','capability_changed','hardware_changed'
    field_name TEXT,
    old_value TEXT,
    new_value TEXT,
    detected_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_changelog_detected ON system_changelog(detected_at);

-- ============ CAPABILITY REGISTRY ============
-- Populated at startup from every module's describe_capabilities().
-- This is the assistant's actual source of self-knowledge — see
-- contracts/capability.py and core/capability_registry.py.

CREATE TABLE system_capabilities (
    module_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    purpose TEXT NOT NULL,
    data_produced TEXT,          -- JSON array
    actions_possible TEXT,       -- JSON array
    limits_and_safety TEXT,
    example_questions TEXT,      -- JSON array
    verification_evidence TEXT,  -- JSON array — what actually proves this works
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE system_heartbeat (
    id INTEGER PRIMARY KEY,
    component TEXT NOT NULL,            -- 'pi_main_loop','safety_mcu','dashboard_sync'
    last_seen TEXT DEFAULT (datetime('now'))
);

CREATE TABLE human_checkins (
    id INTEGER PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    method TEXT                         -- 'dashboard_view','alert_ack','manual_ping'
);
