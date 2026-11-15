# MIA OS: data architecture audit (Prompt 01 §10)

*Claude, 2026-11-15, at `c0a71610`. Nothing here contains real data:
`data/` and `config/config.json` are gitignored, and this audit read
only code and seed files.*

## 1. Storage

| Kind | Where | Format | Evidence |
|---|---|---|---|
| Personal stores (45) | `data/profiles/<id>/` | JSON / JSONL | `core/personal_data.py` `PERSONAL_STORES` |
| Household stores (41) | `data/` (first household) or `data/households/<id>/` | JSON / JSONL | `HOUSEHOLD_STORES` |
| Device-level stores | `data/` | JSON | model, voice, device registry and similar |
| History | life events beside each store | JSONL, append-only | `core/life_events.py` (DEC-0006) |
| Relationships | `kind:id` references | JSON | `core/links.py` |
| Undo | undo log of previous file contents | JSON | `core/undo_log.py` |
| Development platform | `data/dev/`, `work/` | SQLite (council, dev store) and JSON | `core/council.py`, `core/dev_store.py` |
| Configuration | `config/default_config.json` merged with `config/config.json` | JSON | `core/config_manager.py` |
| Secrets | secrets vault and password vault | encrypted JSON | `core/secrets_manager.py`, `core/password_vault.py` |
| Logs | `logs/` | text | `core/logger.py` (secrets kept out, by test) |
| Seed data (tracked) | `data/skill_definitions.json`, `mission_pathways.json`, `foods.tsv` and others | JSON / TSV | `.gitignore` exceptions |

**No database server, no vector database, no embeddings.** All writes go
through `core/atomic_write.atomic_write_text`, which writes a temporary
file and replaces the original, then bumps `core/live.py`. A store lock
keeps it to one writer per data folder.

## 2. Characteristics

| | Local | Cloud | Synced | Encrypted | Backed up |
|---|---|---|---|---|---|
| Personal and household stores | yes | no | phone ↔ PC (`core/sync.py`) | 50 stores sealed at rest **on Windows only** | nightly encrypted (`core/backup_manager.py`) |
| Conversations | yes | no | yes | sealed (Windows) | yes |
| Model files | yes | no | no | no | no (can be downloaded again) |
| Bank data | local snapshots | Plaid holds the source | yes | sealed (Windows) | yes |
| Relay payloads | — | Cloudflare (sealed, short-lived) | — | end-to-end sealed (DEC-0062) | no |
| Dev council | yes | cloud AI accounts get prompts | no | partly | yes |

## 3. Ownership and identity

- **The person.** Each has a profile, signed in by email (`core/profile_manager.py`). Personal stores are per profile.
- **Sharing.** Households are shared only with a member's approval (`core/household_manager.py`).
- **Child accounts.** They still exist (`core/child_accounts.py`), but DEC-0119 says MIA is for Zac alone.
- **Tools.** Tools use the `context` they are given; on the phone a turn runs on the signed-in person's `view_for()`.
- **One identity across apps.** There is a single identity and data model: the apps don't keep separate accounts. Each store owns its own records.

## 4. Data flows

1. **A change from any screen or voice:**
   1. It goes through `core/actions.py` or a tool, then the store.
   2. `atomic_write` saves it and an undo entry is recorded.
   3. A life event is written, and `/api/live` bumps.
   4. Clients read again.
2. **Phone to PC:** `core/sync.py`, started by the phone.
   - JSON: three-way merge.
   - JSONL histories: merged line by line (`event_id`, `at`).
   - Files: blobs by hash.
3. **Turn context:** `core/presence.py` and `core/context_assembler.py` build the facts from stores. The model sees only what is assembled.

## 5. Duplicated sources of truth

These are documented in `docs/BODY_AND_RELATIONSHIP_PLAN.md`:
- shift and pay: the Dungeon versus the Loop;
- training days: workouts versus paths;
- chores: party/chores versus the Loop.

Each pair is reconciled in code, but there is no single owner per fact.

## 6. What cross-device, OS-wide context will need (input to Prompts 07 and 12)

- **A key backend on Linux and Android.** Without one, sealed data can't move to MIA OS (R-02).
- **A defined owner for each fact**, so a user model can't drift.
- **A decision on semantic retrieval** (embeddings or not). This is a Prompt 07 question.
- **Sync that isn't only phone-to-PC.** Today the phone starts every sync, and the glasses and Pi have no sync.
- **A schema per store.** Only the Life State has a JSON Schema (`docs/schema/life_state.schema.json`). The stores have dataclasses with no versioned schemas, which is a migration risk (R-09).
