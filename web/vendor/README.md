# web/vendor: outside code, kept here so the map works offline

Added 2026-11-06 with Zac's OK, for vector offline maps (`web/maps.html`). Never edited here; to update, replace
the file with a newer release and note it below.

| File | Package | Version | License | From |
|---|---|---|---|---|
| `maplibre-gl.js`, `maplibre-gl.css` | MapLibre GL JS | 5.24.0 | BSD-3-Clause (`LICENSE-maplibre.txt`) | npm `maplibre-gl`, via cdn.jsdelivr.net |
| `pmtiles.js` | PMTiles reader | 4.5.0 | BSD-3-Clause (Protomaps) | npm `pmtiles` `dist/pmtiles.js` |
| `basemaps.js` | Protomaps basemap styles | 5.7.2 | BSD-3-Clause (Protomaps) | npm `@protomaps/basemaps` `dist/basemaps.js` |

The map data is OpenStreetMap (© OpenStreetMap contributors, ODbL), cut from the Protomaps daily build by the
`pmtiles` command-line tool (v1.31.2, BSD-3-Clause, `C:\Users\zacrh\DevTools\pmtiles`, outside the repo):
`python -m tools.offline_map`. The cut files live in `data/maps/`, never the repo.
