/*
 * MIA Homestead — Safety MCU Firmware
 * v0.1
 *
 * Implements docs/MCU_PROTOCOL.md exactly: this is the "spinal cord"
 * that the Pi ("brain") talks to. The core property this firmware
 * exists to guarantee: if the Pi goes silent, this board falls back to
 * hard-coded safe behavior on its own, with no dependency on the Pi,
 * the network, or anything else being alive.
 *
 * Target: ESP32 (any variant with enough GPIO for your relay count).
 * Library dependency: ArduinoJson (v6.x) — install via Arduino IDE
 * Library Manager or PlatformIO before building.
 *
 * NOT COMPILED/TESTED in the environment that generated this file — no
 * ESP32 toolchain or network access was available there. Written
 * carefully against the standard Arduino/ESP32 core and ArduinoJson v6
 * API, but the first real compile should happen in Arduino IDE or
 * PlatformIO on real hardware. See firmware/safety_mcu/README.md.
 *
 * Physical link: UART (Serial) to the Pi, per MCU_PROTOCOL.md — not
 * WiFi. This is deliberate: the safety link should not depend on
 * anything that can independently drop (network, DHCP, DNS...).
 */

#include <ArduinoJson.h>

// ============ CONFIGURATION — edit per physical device ============

#define MAX_ACTUATORS 4
#define SERIAL_BAUD 115200
#define HEARTBEAT_TIMEOUT_MS 60000UL   // matches MCU_PROTOCOL.md default
#define STATUS_INTERVAL_MS 10000UL     // normal status broadcast interval
#define STATUS_INTERVAL_FALLBACK_MS 5000UL  // 2x frequency during fallback
#define ANNOUNCE_RETRY_MS 3000UL       // retry announce until paired

// Set this if this board is pre-flashed for a specific role (matches a
// role id in config/devices/roles/*.yaml on the Pi side). Leave empty
// ("") for a generic/blank board that waits for a human to assign a
// role via the Pi's device_setup_cli.py.
const char* REQUESTED_ROLE = "ph_dosing_mcu";

// ============ ACTUATOR SLOTS ============
// Physical pin assignment. Names get filled in from the pair_confirm
// message the Pi sends — this array just reserves the pins. Order
// here should match the order actuators appear in the role's YAML
// "controls" list on the Pi side.

struct ActuatorSlot {
  char name[32];
  int pin;
  char type[16];              // 'dosing_pump','circulation_pump','aerator','valve','alert_beacon'
  char safeDefaultState[8];   // 'on' or 'off'
  bool assigned;
};

ActuatorSlot actuators[MAX_ACTUATORS] = {
  {"", 25, "", "off", false},
  {"", 26, "", "off", false},
  {"", 27, "", "off", false},
  {"", 32, "", "off", false},
};

// ============ LOCAL DOSING LIMITS ============
// Mirrors MCU_LOCAL_LIMITS from MCU_PROTOCOL.md — this is deliberate
// redundancy. Even if the Pi's software has a bug and requests a
// runaway dose, THIS firmware refuses to exceed these numbers.
//
// NOTE: these are hard-coded at flash time, NOT currently synced from
// the Pi at pairing — MCU_PROTOCOL.md's pair_confirm message doesn't
// carry dosing limits yet. If you want live sync, extend pair_confirm
// to include a dosing_limits field and add the parsing here. Until
// then, treat this array as the actual source of truth and keep it
// manually in sync with the Pi's dosing_limits table.

struct DosingLimit {
  char doseType[24];
  unsigned long maxPulseMs;
  unsigned long minIntervalS;
  unsigned long lastDoseMillis;
};

DosingLimit dosingLimits[3] = {
  {"ph_up", 2000, 300, 0},
  {"ph_down", 2000, 300, 0},
  {"nutrient_concentrate", 3000, 600, 0},
};

// ============ STATE ============

String hardwareId;
bool paired = false;
String assignedRole = "";
int assignedCellId = -1;

unsigned long lastHeartbeatReceived = 0;
unsigned long lastStatusSent = 0;
unsigned long lastSeqAccepted = 0;
bool fallbackActive = false;

// ============ SETUP ============

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(500);

  hardwareId = getHardwareId();

  for (int i = 0; i < MAX_ACTUATORS; i++) {
    pinMode(actuators[i].pin, OUTPUT);
    digitalWrite(actuators[i].pin, LOW);  // start fully off, safest default
  }

  // Announce immediately, then keep retrying until paired
  sendAnnounce();
}

// ============ MAIN LOOP ============

void loop() {
  readIncomingSerial();

  unsigned long now = millis();

  if (!paired) {
    static unsigned long lastAnnounce = 0;
    if (now - lastAnnounce > ANNOUNCE_RETRY_MS) {
      sendAnnounce();
      lastAnnounce = now;
    }
    return;  // don't do anything else until paired — no control authority yet
  }

  checkHeartbeatTimeout(now);

  unsigned long statusInterval = fallbackActive ? STATUS_INTERVAL_FALLBACK_MS : STATUS_INTERVAL_MS;
  if (now - lastStatusSent > statusInterval) {
    sendStatus();
    lastStatusSent = now;
  }
}

// ============ SERIAL / PROTOCOL HANDLING ============

void readIncomingSerial() {
  if (!Serial.available()) return;

  String line = Serial.readStringUntil('\n');
  if (line.length() == 0) return;

  StaticJsonDocument<512> doc;
  DeserializationError err = deserializeJson(doc, line);
  if (err) {
    return;  // malformed message — silently ignored, not a reason to
             // change state; the heartbeat timeout is what matters
  }

  const char* type = doc["type"];
  if (type == nullptr) return;

  if (strcmp(type, "pair_confirm") == 0) {
    handlePairConfirm(doc);
  } else if (strcmp(type, "heartbeat") == 0) {
    lastHeartbeatReceived = millis();
  } else if (strcmp(type, "command") == 0) {
    lastHeartbeatReceived = millis();  // a command implies the Pi is alive
    handleCommand(doc);
  } else if (strcmp(type, "resume_control") == 0) {
    handleResumeControl();
  }
}

void handlePairConfirm(JsonDocument& doc) {
  assignedRole = String((const char*)doc["role"]);
  assignedCellId = doc["cell_id"] | -1;

  JsonArray controls = doc["controls"];
  int i = 0;
  for (JsonVariant v : controls) {
    if (i >= MAX_ACTUATORS) break;
    String name = v.as<String>();
    name.toCharArray(actuators[i].name, sizeof(actuators[i].name));
    actuators[i].assigned = true;
    i++;
  }

  paired = true;
  lastHeartbeatReceived = millis();  // start the clock fresh on pairing
  sendStatus();
}

void handleCommand(JsonDocument& doc) {
  unsigned long seq = doc["seq"] | 0;
  if (seq <= lastSeqAccepted && lastSeqAccepted != 0) {
    return;  // reject stale/replayed command per MCU_PROTOCOL.md
  }
  lastSeqAccepted = seq;

  if (fallbackActive) {
    sendAck(seq, false, "fallback_active");
    return;  // do not execute Pi commands while in fallback — only
             // resume_control (after heartbeat resumes) exits fallback
  }

  int actuatorId = doc["actuator_id"] | -1;
  const char* action = doc["action"];
  unsigned long durationMs = doc["duration_ms"] | 0;
  const char* doseType = doc["dose_type"] | "";

  int slot = findActuatorSlotById(actuatorId);
  if (slot < 0) {
    sendAck(seq, false, "unknown_actuator");
    return;
  }

  if (strcmp(action, "pulse") == 0) {
    executePulse(slot, durationMs, doseType, seq);
  } else if (strcmp(action, "on") == 0) {
    digitalWrite(actuators[slot].pin, HIGH);
    sendAck(seq, true, "");
  } else if (strcmp(action, "off") == 0) {
    digitalWrite(actuators[slot].pin, LOW);
    sendAck(seq, true, "");
  } else {
    sendAck(seq, false, "unknown_action");
  }
}

void executePulse(int slot, unsigned long requestedMs, const char* doseType, unsigned long seq) {
  DosingLimit* limit = findDosingLimit(doseType);

  if (limit != nullptr) {
    unsigned long nowS = millis() / 1000;
    unsigned long lastDoseS = limit->lastDoseMillis / 1000;
    if (limit->lastDoseMillis != 0 && (nowS - lastDoseS) < limit->minIntervalS) {
      sendAck(seq, false, "dosing_limit_exceeded");
      return;
    }
    if (requestedMs > limit->maxPulseMs) {
      requestedMs = limit->maxPulseMs;  // clamp, don't just reject —
                                          // a shorter-than-requested dose
                                          // is still safe; over-limit isn't
    }
    limit->lastDoseMillis = millis();
  }

  digitalWrite(actuators[slot].pin, HIGH);
  delay(requestedMs);  // acceptable for a short dosing pulse (<3s max);
                        // a longer-running design would use non-blocking timing
  digitalWrite(actuators[slot].pin, LOW);

  sendAck(seq, true, "");
}

void handleResumeControl() {
  // Deliberately requires BOTH heartbeat resumption AND this explicit
  // message per MCU_PROTOCOL.md — never resumes silently just because
  // a heartbeat arrived.
  if (millis() - lastHeartbeatReceived < HEARTBEAT_TIMEOUT_MS) {
    fallbackActive = false;
  }
}

// ============ FALLBACK LOGIC ============

void checkHeartbeatTimeout(unsigned long now) {
  if (fallbackActive) return;  // already in fallback, nothing new to do here

  if (now - lastHeartbeatReceived > HEARTBEAT_TIMEOUT_MS) {
    enterFallback();
  }
}

void enterFallback() {
  fallbackActive = true;

  for (int i = 0; i < MAX_ACTUATORS; i++) {
    if (!actuators[i].assigned) continue;

    bool safeOn = strcmp(actuators[i].safeDefaultState, "on") == 0;

    // Dosing pumps are pulse-only and should never be left "on" —
    // their safe default is always off regardless of config, since a
    // stuck-open dosing valve is exactly the failure mode this whole
    // architecture exists to prevent.
    if (strcmp(actuators[i].type, "dosing_pump") == 0) {
      digitalWrite(actuators[i].pin, LOW);
    } else {
      digitalWrite(actuators[i].pin, safeOn ? HIGH : LOW);
    }
  }

  sendStatus();  // immediate status push so the Pi sees fallback_active
                  // the moment it reconnects, not after the next interval
}

// ============ OUTGOING MESSAGES ============

void sendAnnounce() {
  StaticJsonDocument<256> doc;
  doc["type"] = "announce";
  doc["hardware_id"] = hardwareId;
  if (strlen(REQUESTED_ROLE) > 0) {
    doc["requested_role"] = REQUESTED_ROLE;
  }
  serializeJson(doc, Serial);
  Serial.println();
}

void sendAck(unsigned long seq, bool executed, const char* reason) {
  StaticJsonDocument<128> doc;
  doc["type"] = "ack";
  doc["seq"] = seq;
  doc["executed"] = executed;
  if (strlen(reason) > 0) {
    doc["reason"] = reason;
  }
  serializeJson(doc, Serial);
  Serial.println();
}

void sendStatus() {
  StaticJsonDocument<128> doc;
  doc["type"] = "status";
  doc["battery_mv"] = readBatteryMillivolts();  // stub — wire to real ADC if this board is battery-powered
  doc["uptime_s"] = millis() / 1000;
  doc["fallback_active"] = fallbackActive;
  serializeJson(doc, Serial);
  Serial.println();
}

// ============ HELPERS ============

String getHardwareId() {
  uint64_t mac = ESP.getEfuseMac();
  char buf[24];
  snprintf(buf, sizeof(buf), "ESP32-%012llX", mac);
  return String(buf);
}

int findActuatorSlotById(int actuatorId) {
  // NOTE: actuator_id in commands from the Pi refers to the DB row id
  // in the `actuators` table, not this array's index. A real deployment
  // needs a mapping table (sent during pairing, or a fixed convention)
  // between DB actuator_id and physical slot. Left as a TODO — for now
  // this treats actuator_id as a direct slot index for simplicity,
  // which only works if that convention is enforced Pi-side too.
  if (actuatorId >= 0 && actuatorId < MAX_ACTUATORS && actuators[actuatorId].assigned) {
    return actuatorId;
  }
  return -1;
}

DosingLimit* findDosingLimit(const char* doseType) {
  for (int i = 0; i < 3; i++) {
    if (strcmp(dosingLimits[i].doseType, doseType) == 0) {
      return &dosingLimits[i];
    }
  }
  return nullptr;
}

long readBatteryMillivolts() {
  // Stub — replace with actual ADC read if this board runs on battery.
  // Returning -1 signals "not applicable" rather than a fake reading.
  return -1;
}
