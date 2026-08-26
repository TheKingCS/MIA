# MIA Homestead — Sustaining Features Brainstorm

Config backup/rollback answers "can it undo a bad change." The
categories below are the other ways a system like this earns the right
to be trusted unattended for long stretches. Not all of these are
worth building now — flagged with rough effort and what problem each
one actually solves, so you can pick.

## 1. Predictive consumable forecasting
**Problem it solves:** the to-order queue reacts to low stock; it
doesn't warn you a week ahead that you're trending toward it.
**What it'd do:** look at `inventory_transactions` consumption rate
over the last N days, project forward, and flag "at current usage,
pH-up runs out in 6 days" — before it crosses the reorder threshold,
not at it. Cheap to build — it's a linear projection over data
already being collected.
**Effort:** small.

## 2. Sensor drift detection (not just failure detection)
**Problem it solves:** the system currently catches sensors that go
stale or return implausible values — it doesn't catch a probe that's
slowly drifting while still returning "plausible" numbers, which is
the actual common failure mode for pH probes specifically (they drift
for weeks before failing outright).
**What it'd do:** compare a probe's readings against expected behavior
— e.g., pH should correct back toward target after a dose; if dosing
events stop producing the expected reading_after change over time,
that's drift, not a control problem. Ties directly into
`dosing_events.reading_after`, which already exists but isn't being
used for this.
**Effort:** medium — needs a real statistical baseline from actual
operation before it's trustworthy, so this is a pilot-hardware-data
feature, not a build-now one.

## 3. Anomaly detection via rate-of-change, not just thresholds
**Problem it solves:** current dosing logic reacts to a value being
out of range. It doesn't react to a value changing unusually FAST even
while still in range — which is often the earlier, more useful signal
(a slow pH crash and a sudden pH crash have very different causes).
**What it'd do:** track rate-of-change per sensor type, alert on an
unusual rate even inside the normal band. This is a genuinely "gets
smarter over time" feature if the baseline rate is learned from your
own system's history rather than hard-coded.
**Effort:** medium.

## 4. Seasonal/environmental awareness
**Problem it solves:** targets are currently static (or
experiment-adjusted) regardless of season — but a greenhouse's thermal
and light environment genuinely shifts across the year, and what's
"correct" for water temp or dosing frequency in July isn't the same as
January.
**What it'd do:** could be as simple as logging month-over-month
baselines and flagging when a reading is unusual FOR THE SEASON rather
than unusual in absolute terms; more ambitious would tie target
adjustments to it. Given you're not building the greenhouse yet, this
is naturally a later-phase feature — flagging it now so `species_profiles`
and `target_overrides` schemas don't need rework when it's time.
**Effort:** large, and genuinely gated on having a full seasonal cycle
of real data first.

## 5. "Confidence" on every reading and decision
**Problem it solves:** right now a sensor reading is either used or
discarded (stale/out-of-range) — there's no middle ground for "this
reading is probably fine but the sensor is overdue for calibration, so
weight it a little less."
**What it'd do:** a lightweight confidence score per reading, informed
by `sensors.calibration_due` proximity and recent drift patterns (see
#2). Dosing decisions could factor confidence in, not just raw value.
**Effort:** medium — depends on #2 existing first to be worth much.

## 6. Multi-cell correlation for diagnosis
**Problem it solves:** the diagnostic engine currently reasons about
one alert in isolation. Once you have 2+ cells (pilot + full scale,
per `PILOT_VS_SCALE.md`), a fault that shows up on BOTH cells
simultaneously is almost certainly a shared-infrastructure problem
(power, Pi itself, network) — not two coincidental probe failures.
**What it'd do:** cross-reference simultaneous alerts across cells
before diagnosing each independently; "both cells lost pH readings at
the same time" is a much stronger, more specific diagnosis than two
separate "pH sensor stale" alerts.
**Effort:** small once there are 2+ cells to correlate — not useful
before then.

## 7. Dead-man's-switch escalation ladder
**Problem it solves:** `human_checkins` and the 72h dead-man's-switch
concept already exist in the schema/spec but the actual escalation
logic (who gets contacted, in what order, after how long) isn't built.
**What it'd do:** a real implementation — after N hours unacknowledged,
notify primary; after more, notify secondary; tie into
`self_preservation.py`'s beacon if someone's physically present but
hasn't engaged with the system remotely.
**Effort:** small — mostly wiring existing pieces together.

## 8. Firmware update safety, mirroring config rollback
**Problem it solves:** `backup_manager.py` handles config rollback;
it explicitly does NOT touch code. Once the Safety MCU firmware is
real and gets updated over time, a bad firmware push is a much scarier
failure mode than a bad config value — and OTA firmware updates are
exactly the kind of thing that benefits from the same "watch, then
roll back if it goes wrong" pattern.
**What it'd do:** version-tag firmware builds, keep the previous
known-good binary on the MCU (or recoverable from the Pi), and apply
the same critical-alert-spike-triggers-rollback logic to firmware
pushes specifically. This is meaningfully harder than config rollback
since it involves re-flashing a physical device, not just files/DB rows.
**Effort:** large, and gated on the MCU firmware actually being
deployed and iterated on first.

## 9. Explain-yourself mode for every autonomous action
**Problem it solves:** dosing events now have a rationale
(`dosing_events.rationale`), but that's currently the only place this
pattern lives. Extending "why did you do that" to load-shedding,
maintenance task auto-creation, and inventory reorder proposals would
make the whole system's autonomous behavior uniformly explainable, not
just dosing.
**What it'd do:** mostly a consistency pass — add a `rationale` field
anywhere an automated action happens and doesn't already have one.
**Effort:** small, mechanical, high value for trust.

## 10. Periodic self-report ("state of the greenhouse")
**Problem it solves:** right now getting a full picture means asking
several separate questions. A once-daily or once-weekly generated
summary — yields, dosing pattern, any anomalies, hardware needs,
pending approvals — read by you rather than pulled by you, closes the
loop on genuinely not having to check in constantly.
**What it'd do:** a scheduled job that compiles the equivalent of
asking the assistant six different questions into one digest, sent via
the existing notification path. Almost entirely a matter of composing
existing data sources — the hard infrastructure work is already done.
**Effort:** small.

## Recommendation on where to start

If you want the highest value for the least effort right now: **#9
(explain-yourself consistency), #10 (periodic self-report), and #7
(dead-man's-switch escalation)** are all small, mechanical extensions
of things already built — no new architecture, just filling in gaps
the same way this session caught the dosing_events and hardware
requirement gaps. **#1 (consumable forecasting)** is similarly cheap
and directly useful once real consumption data exists.

**#2, #3, #5** (drift/anomaly/confidence) are the ones that actually
make the system "get smarter" in the way the experiment system does —
but they need real operational data to be worth building well, which
argues for building them once the pilot is running, not before.
