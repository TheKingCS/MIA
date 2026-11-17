# MIA OS: spatial interfaces and portals (Prompt 11 §15; DEC-0239)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. What exists

The Nexus (`web/nexus.html`, `web/nexus3d.js`): a three-dimensional room for Living Worlds (DEC-0153: the Nexus is
for Living Worlds only); portals (`portals.html`) to worlds; the old area "rooms" (`&room=1`) replaced by dashboards on
2026-11-17.

## 2. The concept

**A portal is a doorway to a place made of the same screens**: Home, Workshop, Greenhouse, Learning, Recreation,
Research, Creative. Entering one shows that area's dashboard in a spatial arrangement (panels in depth around him),
with the same data and actions. **Nothing exists only in space**: every panel is a screen reachable from the sidebar,
search and Talk.

| Feature | Needs | Feasible now |
|---|---|---|
| Portals as transitions between areas on the desktop | the 3D room's renderer | yes |
| Living Worlds in the Nexus | exists | yes |
| Panels arranged in depth | WebGL | yes, as an Immersive mode |
| Spatial windows anchored in a room | a headset (OpenXR, WebXR) | future |
| Objects anchored to the real world | AR glasses with world tracking | future |
| Hand interaction | a headset with hand tracking | future |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-VIS-020 | Every spatial panel or portal shall be a view of a screen also reachable from the sidebar, search and Talk. | Must | R1 | All | Partial | T | DEC-0239 → 11 |
| REQ-VIS-021 | Each spatial feature shall be labelled by the hardware it needs, and none shall be promised before that hardware is supported. | Must | R1 | All | New | R | DEC-0239 → 11, 12 |
