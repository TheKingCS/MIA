# MIA OS: application data, ownership and persistence (Prompt 03 §9)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).*

## 1. Who owns what (exists)

| Kind of data | Where | Owner | Evidence |
|---|---|---|---|
| A person's own records | `data/profiles/<id>/` (under `MIA_HOME`) | the person | `core/personal_data.PERSONAL_STORES` (49) |
| A household's shared records | `data/` or `data/households/<id>/` | the household, on members' approval | `HOUSEHOLD_STORES` (42), `core/household_manager.py` |
| Device-level state | the device's own config and logs | the device | the model, the voice, `config/config.json` |
| Temporary and cached | in memory, or the scratch/cache folders | nobody: may be dropped | the assembled context per turn |
| App configuration | `config/config.json` (`modules.<id>.*`), person settings | the person | `core/person_settings.py` |
| Session state | tokens in the server; a page's tab in its address | the session | `server/app.py` |
| History | `life_events.jsonl`, never rewritten | the person | `core/life_events.py` |

**Stores belong to people, not to apps.** An app's capabilities read and write stores; hiding or removing the app
leaves its stores (AF-8). Deleting a person's data is its own approved action (`core/account_data.py`: export and
delete, behind the password).

## 2. Access across apps

An app reads another app's facts through the life state, a screen's data or a capability, never the file. An
extension (out of process) gets only what its granted capabilities return. An external app gets only what the person
sends it, or what a portal hands it.

## 3. Protection

At-rest sealing of private stores (AES-256-GCM, `core/at_rest.py`, DEC-0126; on Linux the key kept by systemd with the
TPM, DEC-0169); the atomic write; a damaged file copied aside before a store starts empty; one MIA per data folder
(`core/instance_lock.py`); backups nightly (`core/auto_backup.py`), encrypted when given a passphrase.

## 4. Sync, continuity and conflicts

PC ↔ phone two-way sync (`core/sync.py`, DEC-0022) compares by content (`at_rest.open_bytes`) with its tie-break
rules. A project opened on the PC is on the phone; interface preferences stay per device. Glasses read through the
phone. **Gaps for Prompt 12:** more than two devices, a home server, conflict resolution beyond the current rules.

## 5. Versions and migration

Every store already tolerates old records (unknown fields ignored, missing ones defaulted on load). Proposed (T-03,
Prompt 15): a version number per store file and a migration function per version step, run on load, with the
pre-migration file kept beside it until the next backup.

## 6. Export and portability

The account export (`core/account_data.py`) writes every store a person owns, opened from its sealing, as files they
can take. MIA's folder moves whole with `tools/move_home.py`.

## 7. On uninstall

First-party apps aren't uninstalled, only hidden. An extension's removal (proposed host) asks: keep its data, export
it, or delete it (the last an approved, irreversible action).
