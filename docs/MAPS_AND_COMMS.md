# Maps and Comms, inspired by defense systems

*DEC-0099 (Zac, 2026-11-06: "Maps should take inspiration from Palmer Luckys work with military mapping and
communications technologies" and "Really dive into military level technology resources for MIA"). Build plan
step 14. Open, civilian standards only. Facts marked (verify) are from memory and should be checked before
they're built on.*

## 1. What the defense world does that's worth borrowing

| Idea | Where it comes from | What it means for MIA |
|---|---|---|
| **One shared picture** of everything that matters, fused from many sensors, each thing a track with a history | Anduril's Lattice (closed; we borrow the idea, not the product) | MIA's places, people (by their consent), devices and sensors on one map, each with where it was and when |
| **A grid everyone can say out loud** | MGRS (NATO's Military Grid Reference System, built on UTM) | "Meet at 18S UJ 234 064": a place by voice, to the metre, no lat/lon decimals. **Built.** |
| **A plain format for "this thing is here"** | Cursor on Target (CoT): an XML event with a uid, a type, a point and a stale time | MIA's places readable by any TAK app. **Built** (as a data package). |
| **A map app everyone can use** | ATAK-CIV (Android, free, open source), iTAK, WinTAK-CIV; TAK Server (open source) (verify the current repos) | The person's own TAK app shows MIA's picture; MIA doesn't need to build that map |
| **Comms without cell towers** | LoRa mesh radios (Meshtastic: open-source firmware, license-free ISM band, AES-encrypted channels, an ATAK plugin) | Messages and positions between family radios on the property, at the cabin, on a trail, with no service |
| **Maps that work with no signal** | Offline tiles | **Built** for raster (USGS topo, `core/map_tile_cache.py`); vector tiles (Protomaps PMTiles from OpenStreetMap, a single file per region) would be smaller and sharper |

## 2. Built (2026-11-06)

- **`core/geo_grid.py`**: latitude/longitude to UTM and MGRS and back, on WGS84, in code with no dependency.
  Checked against `pyproj` and the `mgrs` package: 4,000 random points between 80°S and 84°N agreed, the
  Norway and Svalbard zone exceptions included, digits within a metre, the round trip within half a metre.
- **Waypoints speak grids**: "add a waypoint called Spring at 18S UJ 23478 06483", "what's the grid for
  Spring?"; the Assistant's waypoint list shows each grid; `add_waypoint` takes a grid instead of lat/lon.
- **`core/tak.py`**: waypoints as Cursor on Target events (spot markers, `b-m-p-s-m`) and KML, packed as a TAK
  data package (`MANIFEST/manifest.xml`). `python -m tools.tak_export` writes `MIA_places.zip` to Documents;
  import it in ATAK-CIV. Nothing is sent anywhere.

## 3. Next, in order

1. ✅ **Tracks** (`core/gps_tracks.py`, 2026-11-06): GPX import (`python -m tools.tracks add walk.gpx`), distance,
   climb past GPS jitter, moving time, start and end grids, in the person's own folder; a line in the TAK
   package; "how far was my last hike?". Still to do: the phone recording one, and drawing them on MIA's map.
2. **Sharing on the local network**: CoT over UDP multicast (SA's usual address, 239.2.3.1:6969 (verify)), so a
   TAK app on the same Wi-Fi sees MIA's places live. A person's own places only, by an action they approve, and
   off again by one word.
3. **Vector offline maps** (PMTiles) for the property and trails, beside the USGS topo tiles.
4. **Meshtastic** (needs hardware, see section 4): MIA on the PC talks to a radio over USB through the
   `meshtastic` Python package (verify its current API): messages in and out, members' positions on the map, a
   "where is everyone?" answer, and MIA's alerts reaching a radio when the phones have no signal.
5. **The shared picture**: people by consent (a family member's phone or radio position), devices and sensors
   (the greenhouse, the flock's coop, a gate) as tracks on one map, with "what changed since this morning?".

## 4. What it needs from Zac (also in `docs/WAITING_ON.md`)

- **For mesh: two or more LoRa radios** that run Meshtastic (common choices: Heltec LoRa 32 V3, LILYGO T-Beam
  with GPS, RAK WisBlock; usually $20 to $60 each (verify)), on the US 915 MHz band. One stays plugged into the PC.
- **Whether to install ATAK-CIV** on the phone (free, Google Play) to see MIA's places there.
- Which places to start with (the property's corners, the well, trailheads).

## 5. Limits we keep

Civilian and open only: no military-only formats, keys or services; nothing that tracks a person who hasn't
said yes, and a person can stop sharing at once; positions stay on the person's own devices unless they send
them; licensed radio bands only with the license (Meshtastic's default ISM use needs none in the US (verify)).
