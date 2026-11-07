"""
core.geo_grid
===============

Grid references (build plan step 14, DEC-0099): UTM and MGRS, the Military
Grid Reference System that maps, search-and-rescue teams and TAK apps use
("18S UJ 23396 06441"), worked out in code from latitude and longitude on
the WGS84 ellipsoid. No dependency, no network. Accurate to well under a
metre inside a zone (checked against `pyproj` and the `mgrs` package in
tests/test_geo_grid.py's reference points).

- `to_mgrs(lat, lon, digits=5)`: 5 digits is 1 m, 4 is 10 m, 3 is 100 m.
- `from_mgrs("18SUJ2339606441")`: back to latitude and longitude (the
  square's south-west corner at the reference's precision, plus half a
  square, so it's the middle of what it names).
- UTM's two exceptions are kept (south-west Norway, Svalbard). MGRS covers
  80°S to 84°N; the poles use a different system (UPS), which isn't here.
"""

from __future__ import annotations

import math
import re

A = 6378137.0
F = 1 / 298.257223563
E2 = F * (2 - F)
EP2 = E2 / (1 - E2)
K0 = 0.9996
BANDS = "CDEFGHJKLMNPQRSTUVWX"
COLUMNS = ("ABCDEFGH", "JKLMNPQR", "STUVWXYZ")
ROWS = "ABCDEFGHJKLMNPQRSTUV"


class GridError(ValueError):
    """A position or reference outside what MGRS covers, or one that isn't a reference."""


def zone_of(lat: float, lon: float) -> int:
    """Pure logic. The UTM zone a point is in, with the exceptions for southwest Norway (32V) and Svalbard (31X
    to 37X).
    """
    lon = ((lon + 180) % 360) - 180
    zone = int((lon + 180) // 6) + 1
    if 56 <= lat < 64 and 3 <= lon < 12:
        return 32
    if 72 <= lat < 84 and 0 <= lon < 42:
        return 31 if lon < 9 else 33 if lon < 21 else 35 if lon < 33 else 37
    return min(zone, 60)


def band_of(lat: float) -> str:
    """Pure logic. The MGRS latitude band letter; GridError outside 80°S to 84°N (the poles use UPS)."""
    if not -80 <= lat <= 84:
        raise GridError("MGRS covers 80°S to 84°N; the poles use UPS.")
    return BANDS[min(int((lat + 80) // 8), 19)]


def _meridian(phi: float) -> float:
    """Pure logic. The distance along the meridian from the equator to a latitude (radians), on the WGS84
    ellipsoid.
    """
    e4, e6 = E2 * E2, E2 ** 3
    return A * ((1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
                - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
                + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
                - (35 * e6 / 3072) * math.sin(6 * phi))


def to_utm(lat: float, lon: float, zone: int = 0) -> tuple[int, str, float, float]:
    """(zone, band, easting, northing)."""
    band = band_of(lat)
    zone = zone or zone_of(lat, lon)
    phi, lam = math.radians(lat), math.radians(lon)
    lam0 = math.radians((zone - 1) * 6 - 180 + 3)
    n = A / math.sqrt(1 - E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = EP2 * math.cos(phi) ** 2
    a = math.cos(phi) * (lam - lam0)
    easting = K0 * n * (a + (1 - t + c) * a ** 3 / 6 + (5 - 18 * t + t * t + 72 * c - 58 * EP2) * a ** 5 / 120) + 500000
    northing = K0 * (_meridian(phi) + n * math.tan(phi) * (
        a * a / 2 + (5 - t + 9 * c + 4 * c * c) * a ** 4 / 24 + (61 - 58 * t + t * t + 600 * c - 330 * EP2) * a ** 6 / 720))
    if lat < 0:
        northing += 10_000_000
    return zone, band, easting, northing


def from_utm(zone: int, northern: bool, easting: float, northing: float) -> tuple[float, float]:
    """(latitude, longitude)."""
    x = easting - 500000
    y = northing if northern else northing - 10_000_000
    m = y / K0
    mu = m / (A * (1 - E2 / 4 - 3 * E2 ** 2 / 64 - 5 * E2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - E2)) / (1 + math.sqrt(1 - E2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu) + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32)
            * math.sin(4 * mu) + (151 * e1 ** 3 / 96) * math.sin(6 * mu) + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    n1 = A / math.sqrt(1 - E2 * math.sin(phi1) ** 2)
    t1 = math.tan(phi1) ** 2
    c1 = EP2 * math.cos(phi1) ** 2
    r1 = A * (1 - E2) / (1 - E2 * math.sin(phi1) ** 2) ** 1.5
    d = x / (n1 * K0)
    lat = phi1 - (n1 * math.tan(phi1) / r1) * (d * d / 2 - (5 + 3 * t1 + 10 * c1 - 4 * c1 * c1 - 9 * EP2) * d ** 4 / 24
                                              + (61 + 90 * t1 + 298 * c1 + 45 * t1 * t1 - 252 * EP2 - 3 * c1 * c1)
                                              * d ** 6 / 720)
    lon = (d - (1 + 2 * t1 + c1) * d ** 3 / 6 + (5 - 2 * c1 + 28 * t1 - 3 * c1 * c1 + 8 * EP2 + 24 * t1 * t1)
           * d ** 5 / 120) / math.cos(phi1)
    return math.degrees(lat), (zone - 1) * 6 - 180 + 3 + math.degrees(lon)


def _square(zone: int, easting: float, northing: float) -> str:
    """Pure logic. The 100 km square's two letters for an easting and northing in a zone (the row letters shift by
    five in even zones).
    """
    column = COLUMNS[(zone - 1) % 3][int(easting // 100000) - 1]
    row = int(northing // 100000) % 20
    if zone % 2 == 0:
        row = (row + 5) % 20
    return column + ROWS[row]


def to_mgrs(lat: float, lon: float, digits: int = 5) -> str:
    """Pure logic. "18S UJ 23396 06441" (digits per axis: 5 is 1 m, 1 is 10 km)."""
    if not 1 <= digits <= 5:
        raise GridError("A reference has 1 to 5 digits each way.")
    zone, band, easting, northing = to_utm(lat, lon)
    scale = 10 ** (5 - digits)
    e = int(easting % 100000 // scale)
    n = int(northing % 100000 // scale)
    return f"{zone}{band} {_square(zone, easting, northing)} {e:0{digits}d} {n:0{digits}d}"


_MGRS = re.compile(r"^\s*(\d{1,2})\s*([C-HJ-NP-X])\s*([A-HJ-NP-Z])\s*([A-HJ-NP-V])\s*(\d*)\s*(\d*)\s*$", re.IGNORECASE)


def parse(reference: str) -> tuple[int, str, str, str, str]:
    """Pure logic. An MGRS reference as (zone, band, column letter, row letter, digits); GridError when it isn't
    one or its digits don't split evenly.
    """
    m = _MGRS.match(reference or "")
    if not m:
        raise GridError("That isn't a grid reference (like 18S UJ 23396 06441).")
    zone, band, col, row, a, b = m.groups()
    digits = a + b
    if len(digits) % 2 or len(digits) > 10:
        raise GridError("A reference has the same number of digits each way, up to five.")
    return int(zone), band.upper(), col.upper(), row.upper(), digits


def from_mgrs(reference: str) -> tuple[float, float]:
    """Pure logic. The middle of the square a reference names, as (latitude, longitude)."""
    zone, band, col, row, digits = parse(reference)
    if not 1 <= zone <= 60:
        raise GridError("A zone is 1 to 60.")
    columns = COLUMNS[(zone - 1) % 3]
    if col not in columns:
        raise GridError(f"{col} isn't a column letter in zone {zone}.")
    half = len(digits) // 2
    scale = 10 ** (5 - half) if half else 100000
    e_in = int(digits[:half]) * scale if half else 0
    n_in = int(digits[half:]) * scale if half else 0
    easting = (columns.index(col) + 1) * 100000 + e_in + scale / 2
    r = ROWS.index(row)
    if zone % 2 == 0:
        r = (r - 5) % 20
    northing = r * 100000 + n_in + scale / 2
    south = BANDS.index(band) * 8 - 80
    northern = band >= "N"
    floor = to_utm(max(south, -80), (zone - 1) * 6 - 180 + 3, zone)[3]  # the band's southern edge, at the meridian
    if not northern and south >= 0:
        raise GridError("That band and hemisphere don't agree.")
    while northing < floor - 100000:  # the row letters repeat every 2,000 km: the cycle that lands in the band
        northing += 2_000_000
    return from_utm(zone, northern, easting, northing)
