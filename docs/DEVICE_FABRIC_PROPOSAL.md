# MIA across your technology: Field Kit grows up (DEC-0128, proposed)

*claude, 2026-11-08, from Zac's ask: MIA should "intuitively be able to
communicate with other technologies… recognize them… install herself, and
operate on my device," and have real "cyber security" / ability to "access
and manipulate / merge with other technologies." Sharpened after the
Echo Show turned out to be unconvertible: the lesson is that reliable interop
comes from **protocols and credentials you hold, not exploits.***

**The proposal in one line:** grow the Connected Device Framework from the
devices plugged into MIA to every device on your network — she **perceives**
them (what's there), **identifies** them (what they are and what they can do,
including what's wrong with them), **speaks** to them (the right protocol for
each), and **extends onto** them (installs and runs herself) — with a security
role that is defensive by default and offensive only against your own,
authorized targets, behind the same person-only gate as her browser.

## Why not "exploits"

Zac said "perform common exploits." The Echo is the counter-example: locked,
signed, no exploit, dead end. Exploits are device-specific, break on every
firmware update, and are the thing that *stopped* us. Everything Zac actually
wants — recognize, talk to, install onto, operate — is done better by speaking
a device's own protocols with credentials he holds. So MIA gets a **fabric**,
not an exploit kit. Real offensive capability still exists (below), but as a
gated tool for *his* gear, not the main road.

## What already exists (don't rebuild)

| Piece | State | Where |
|---|---|---|
| Connected Device Framework — detect/identify USB + serial/MCU | built (11.1) | `core/device_framework.py` |
| Device Manager + per-device actions | partial (11.2) | `modules/field_kit/` |
| Flashing safety rails (confirm before any write) | built (11.3a) | 11.3a design; `BlockDevice.is_external` |
| Actual OS write + auto-install MIA | **not built** (11.3b) | — |
| Useful scripts library | built (11.4) | Field Kit |
| Security/network toolkit — TCP port scan, subnet calc | built (11.5) | `core/port_scanner.py`, `core/subnet_calculator.py` |
| Smart Home — lights/cameras/locks, local-protocol only | **not built** (13) | — |
| Wi-Fi / Bluetooth discovery | **planned extension of 11.1**, not built | the roadmap already says so |

The roadmap (milestone 17) already names "flash OS + auto-install MIA" and
"security/network recon + active toolkit." This proposal is the plan for the
unbuilt rows, as one coherent subsystem.

## The four layers

All of it hangs off the existing `context.devices` (the Connected Device
Framework), extended — not a parallel system.

### 1. Perceive — discovery
Find what's on *your* networks, passively first:
- **mDNS / DNS-SD** (`zeroconf`): Chromecasts, AirPlay, printers, HomeKit, Pis.
- **SSDP / UPnP** (`async-upnp-client` or a small SSDP probe): smart TVs, DLNA, routers.
- **Bluetooth / BLE** (`bleak`): speakers, trackers, sensors, the glasses.
- **ARP sweep of the local subnet** (stdlib + the existing subnet calculator):
  everything with an IP, with MAC → vendor via an OUI table.
- Optional **TCP service probe** (the existing port scanner) for a device that
  answers nothing above.

Output: a **device inventory** store — each device a thing with a `kind:id`
ref (ties into `core/links.py` and `core/life_events.py`), carrying identity,
make/model guess, protocols spoken, capabilities, open ports, first/last seen.
Household-scoped (the home's tech), on `atomic_write_text` + `_load` so it's
undoable and, if it holds anything sensitive, sealable (DEC-0126).

### 2. Identify — recognition
Match each device to a **capability profile**: "Chromecast → I can cast",
"Hue bridge → lights", "Pi running MIA → peer", "SSH host, key in the vault →
shell", "the glasses → her display". Sources: OUI vendor, mDNS TXT records,
UPnP device descriptions, service banners. And **what's wrong with it** — known
CVEs for the identified make/model/firmware, default/weak credentials, stale
firmware — reusing the OSV/vuln-lookup pattern already built for
`core/dependency_audit.py`.

### 3. Speak — adapters
One adapter per protocol (`core/fabric/adapters/*`), each declaring what it can
do; MIA picks the right one for an intent ("show this on the kitchen screen" →
Cast adapter; "turn off the lights" → Home Assistant/Hue). Starts with the ones
that need no new hardware: Cast, DLNA, Home Assistant/MQTT, SSH to Zac's own
hosts. This is the "intuitively communicate with other technologies" part, done
through each device's real interface. Smart Home (milestone 13) becomes the
first big consumer.

### 4. Extend — self-deployment
MIA packages and installs **herself** onto Zac's devices:
- **The Pi**: push over SSH + the existing `deploy/install_kiosk.sh` systemd
  user service. (Already mostly built — this wires it to discovery.)
- **A screen**: cast her web UI / panel mode (the kiosk view) to a Cast or
  DLNA display — the realistic answer for the Echo-shaped goal.
- **Flash + provision** (11.3b): write an OS image to an attached disk and
  auto-install MIA, behind the flashing safety rails already designed.
- **The phone**: the Android build, linked as today.

"Install herself and operate on my device" = this provisioning flow.

## The security role

Two speeds, one hard line between them.

**Defensive — always on, no gate.** MIA audits *your* network the way she
already audits her own dependencies: inventory + open ports + default/weak
creds on your own devices + stale firmware + known CVEs → findings through the
communication gate, like any other thing she tells you. This is the natural
extension of the weekly dependency check from her own packages to your home.
Unambiguously good; built first.

**Offensive / authorized testing — gated, scoped, logged.** Credential
testing, exploit attempts, and the "active toolkit" run **only** against
targets on an explicit owner-authorized list (your own devices; the local
subnet is the default discovery scope, nothing beyond your networks is ever a
target for anything intrusive). Every intrusive action is sorted in code by a
`core/fabric_safety.classify()` — modelled exactly on `core/browser_safety.py`
— into read/scan (fine) vs. control vs. intrusive-test; anything intrusive
becomes a `fabric.commit` action **approved by a person, never the model**
(the browser-commit rule), and is written to the security log. No mass
scanning, no third-party targets, no DoS, no detection-evasion — those aren't
gated, they're out of scope. Because the whole point is *Zac's own tech*, this
line costs him nothing.

## Guardrails (reused, not new)

- **The gate**: `fabric_safety.classify()` ⟶ `fabric.commit`, person-only, same
  shape as `browser_safety` / `browser.commit`.
- **Scope**: an owner-authorized target list; discovery defaults to the local
  subnet; nothing intrusive leaves it.
- **Logged**: every scan and commit to `core/security_log.py`.
- **Undoable + sealed**: the inventory on `atomic_write_text` + `_load`, sealed
  if sensitive (DEC-0126).
- **Through the gate**: unprompted findings via `context.communication.offer`.
- **Local-first**: no cloud; an Alexa-skill-style cloud bridge stays out
  (against the whole design, and Zac said so for the Echo).
- **A loop**: an improvement loop (DEC-0094) so her recognition/actions get
  rated and better over time.

## First build (needs no new decision)

The read-only, defensive half is safe to build before any gate design is
settled, and it's the foundation everything else sits on:

1. **Network discovery** added to the Connected Device Framework (mDNS + SSDP +
   ARP sweep first; BLE next), writing the device inventory store.
2. **Identification** — OUI/mDNS/UPnP → make/model + capability profile.
3. **Defensive audit** — open ports + known CVEs for identified devices →
   through the comms gate.
4. A **Field Kit web screen** showing the inventory and findings.

Then, on Zac's approval of the gate design: the adapters (speak), self-deploy
(extend), and the authorized-testing commit path.

## Open questions for Zac

- Inventory scope: household store, or device-level (this machine's view)?
- How far into active testing do you want to go, and against which of your
  devices — list them, or auto-trust anything on your own subnet?
- Smart Home stack: Home Assistant as the hub MIA talks to, or direct
  per-protocol adapters?
- Does the inventory count as sealed-at-rest (DEC-0126)? (It names your
  devices and their weaknesses — I'd say yes.)

## Related
DEC-0117 (her browser — the gate pattern this copies), DEC-0126 (encryption at
rest), DEC-0094/0101 (loops), `core/dependency_audit.py` (the vuln-lookup
pattern), ROADMAP milestones 11 (Field Kit) and 13 (Smart Home).
