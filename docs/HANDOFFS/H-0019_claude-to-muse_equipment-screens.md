# H-0019: Garage, Property, Greenhouse, Maintenance and the asset page are working
- From: claude · To: muse (cc zac, chatgpt) · Date: 2026-10-06
- Related: DEC-0017, H-0018, Zac's concept set (the Garage card page and the mower page)

## What landed (yours to restyle; please keep the data flow)

- **The equipment screens: `garage.html`, `property.html`, `greenhouse.html` and `maintenance.html`.**
  - All four use one script, `equipment.js`. The page's `<body data-scope>` picks which screen it is.
  - The data comes from `MIA.equipment(scope)`.
  - Each screen has the strip (Tracked, Needs attention, Next up), the red needs-attention panel with Done buttons, asset cards with their top three tasks and status chips, and a Next up list.
  - Maintenance adds Tasks and Calendar tabs.
  - I replaced your `garage.html` and `garage.js` with these; your design work lives on in `components.css`.
- **The asset page: `asset.html?id=…`**, in the shape of Zac's mower concept. The data comes from `MIA.asset(id)`.
  - Stat tiles: engine hours, fuel and any other meter, each with Log.
  - Needs attention.
  - Tabs: Overview, Maintenance, Missions, Documents, Costs, History and Parts.
    - Documents can be uploaded from the phone or browser, opened and removed.
    - Parts is honestly marked as not tracked yet.
- **Every change is an action with a confirm and undo.** That covers Done, logging a reading, and adding, editing or deleting assets and tasks.
  - "Done" on an hour-based task asks for the meter reading.
  - Forms come from the engine's field lists (`MIAShell.form`, which now also handles whole numbers and an asset picker).

## Notes for the look
- **The concept's photo heroes and per-asset pictures:** assets have no photo field yet. If you want pictures per asset, say so in `QUESTIONS.md` and I'll add the field and an upload.
- **Asset icons** follow the asset's kind (🚗 vehicle, 🚜 power equipment, 🔌 appliance, 🏠 property, 🌱 garden, 🔨 tool). Change them freely.
- **On a phone,** the asset page's seven tabs scroll sideways under your tab styling. Your call.

## Acceptance criteria
- After a restyle, these all still work end to end:
  - Done, with and without a meter value;
  - log a reading;
  - add, edit and delete an asset or a task, with undo;
  - upload, open and remove a document.
