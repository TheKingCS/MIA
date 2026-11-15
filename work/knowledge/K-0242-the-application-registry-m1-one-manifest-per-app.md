---
id: K-0242
kind: implementation
title: The Application Registry, M1: one manifest per app, checked against the code
status: confirmed
by: claude
created: 2026-11-15T17:32:23+00:00
concerns: core/app_registry.py, tools/app_manifests.py, docs/schema/app_manifest.schema.json, tests/test_app_registry.py
from: dec:DEC-0178, dec:DEC-0175
---
What: every app in core/web_surfaces.APPS got apps/<id>/manifest.json (57 with apps/mia/ for the platform), written by tools/app_manifests.py from today's code; core/app_registry.py loads them, answers queries (owner_of, capabilities_of, dependents_of, on_device) and problems() checks every tool (parity.desktop_registry), action kind (ACTION_TYPES), store (PERSONAL_STORES + HOUSEHOLD_STORES), job and daily check (background_jobs) is claimed by exactly one manifest, and that named pages, Qt modules and dependencies exist. docs/schema/app_manifest.schema.json uses only the keywords core/schema_check supports.
Why this way: generated first so nothing changes behaviour (DEC-0178); the agreement test is what keeps manifests honest until the registry becomes the source in M3. Ownership was decided in hand-checked tables (FAMILY_OWNER, STORE_OWNER, JOB_OWNER, SHARED_DOMAIN_OWNER) rather than guessed from names; shared tool domains (maintenance, ledger, expeditions) have one owner and the rest list them under uses.
What went wrong: the first generation left the browser and workout action families, the alarms and email_drafts stores and some jobs unclaimed; the check found them all. write refuses to overwrite manifests unless --force, because after M1 they are hand-kept records.
