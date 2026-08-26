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
    amount_ml REAL NOT NULL,
    reading_before REAL,
    reading_after REAL,                 -- filled in on next confirmed reading
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
    timestamp TEXT DEFAULT (datetime('now')),
    severity TEXT NOT NULL,             -- 'info','warning','critical'
    source TEXT,                        -- cell/sensor/actuator ref, free text
    message TEXT NOT NULL,
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
