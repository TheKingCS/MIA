# MIA OS: shared services catalogue (Prompt 02 §8)

*Prompt 04 (2026-11-15): requirements now live in [MIA_OS_SYSTEM_REQUIREMENTS.md](MIA_OS_SYSTEM_REQUIREMENTS.md) and [MIA_OS_FUNCTIONAL_REQUIREMENTS.md](MIA_OS_FUNCTIONAL_REQUIREMENTS.md); each shared service's requirements are there.*

*Prompt 03 gives each service its contract (inputs, outputs, boundary, failure) and the local API for out-of-process callers: [MIA_OS_APPLICATION_API_ARCHITECTURE.md](MIA_OS_APPLICATION_API_ARCHITECTURE.md).*

*Claude, 2026-11-15. These are services every app should use instead of
building its own. "Exists" is from Prompt 01's evidence; "New" are
proposals.*

| Service | Responsibility | Consumers | Depends on | Where / status |
|---|---|---|---|---|
| Identity | who the person is; profiles, households, child accounts | everything | stores, crypto | `core/profile_manager.py`, `household_manager.py`: exists |
| Person settings | per-person preferences | every app | stores | `core/person_settings.py`: exists |
| Memory | facts about the person, reviewable and deletable | Talk, LEP, Closet | stores | `core/user_memory_manager.py`: exists (keyword) |
| History and links | what happened; how things relate | Dashboard, missions, LEP journal | stores | `core/life_events.py`, `links.py`: exists |
| Context assembly | the facts a turn sees | Talk, every tool | stores | `core/presence.py`, `context_assembler.py`: exists |
| Model routing | which model answers | Talk, captions, tutoring | Ollama, llama-server | `core/llm_manager.py`, `home_link.py`: exists |
| Speech in and out | speech to text, text to speech | Talk, glasses, Pi | Vosk, Piper, Kokoro | `core/voice_manager.py`: exists |
| **Speaker identification** | who is speaking | every voice surface | voice models | **New** (DEC-0163) |
| Actions and approvals | propose, approve, execute, record, undo | every change | stores | `core/actions.py`: exists |
| Speaking up | rate-limit and merge unprompted messages | daily checks, LEP, Closet | notifications | `core/communication_gate.py`: exists |
| Notifications | toasts, persisted, web push | everything | pywebpush | `core/notification_manager.py`: exists |
| Search | find anything (Ctrl+K) | every app registers a provider | — | `core/search_manager.py`: exists |
| Calendar and time | events, recurring events, free time | LEP, Closet, missions | stores | `core/calendar_manager.py`: exists; **free time across two people: new** |
| Rhythms | when work, chores and routines happen | Loop, Dungeon, LEP, Closet | calendar | `core/the_loop.py`: exists |
| Places | the person's places, arrivals | LEP, places quests | phone location | `core/places.py`: exists |
| Maps and routes | maps, routes, distance | LEP, trips | offline maps | `core/maps_web.py`, `trip_route.py`: exists |
| Weather | forecast for the person's town | Dashboard, LEP, Closet | network | `core/weather.py`: exists |
| Money | balances, budgets, bills | Finances, LEP, Dungeon | Plaid | `core/finance_manager.py`, `budget_manager.py`: exists |
| **Discretionary money** | what can be spent on fun without touching bills, goals or reserves | LEP, destination savings | Money | **New**: worked out in code, never by the model |
| Media and photos | Memory Vault, photos | LEP journal, Closet pictures | phone gallery | `core/memory_vault.py`: exists |
| Files | the person's files and inbox | Talk, Send to MIA | filesystem | partial |
| Sync | phone ↔ PC | everything | network | `core/sync.py`: exists |
| Scheduling | periodic jobs | daily checks, discovery, backups | Qt today | in `core/application.py`; **a runtime scheduler is new** (R-01) |
| **Online fetch policy** | what MIA may fetch in the background, from where, how often | LEP discovery, weather, news | network | **New** (Q-08) |
| Capability registry | what MIA can do, from code | Talk, Settings, discovery | code | `core/capabilities.py`: exists |
| Logging and the Fix-It Log | errors, issues | everything | — | exists |

**Duplication to avoid:**
- LEP must not keep its own calendar, budget or photos.
- Smart Closet must not keep its own weather or photo store.
- Both use the services above.

**Existing duplication:** listed in Prompt 01 (R-10).
