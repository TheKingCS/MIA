# MIA OS: more than one person (Prompt 02 §11)

*Claude, 2026-11-15. Scope from Zac:*
- *MIA OS is for him, and may extend to close friends later (DEC-0159).*
- *His wife may speak to MIA at the same time as him, and MIA must tell
  who is talking (DEC-0163).*

*LEP plans for the couple (DEC-0161). DEC-0119's "never children" still
stands.*

## What exists

- **Separate accounts.** Each person signs in by email and has their own stores (`PERSONAL_STORES`, 45).
- **Shared households** need a member's approval, and share 41 stores.
- **Each turn runs on one person's own view** (`view_for()`).
- **Approvals run as the person who approved** (`core.profile_manager.crediting`).

## Requirements

| ID | Requirement | Priority |
|---|---|---|
| MU-1 | Each person has their own identity, memories, private journal, conversations and approvals; nothing personal is shared without that person's yes | Must (exists) |
| MU-2 | MIA identifies the speaker from voice, on the device, from samples each person chose to give | Must (new) |
| MU-3 | When two people speak in one session, each turn is attributed to its speaker and runs as them | Must (new) |
| MU-4 | When MIA isn't sure who spoke, she asks; a guess never unlocks private data | Must |
| MU-5 | Consequential approvals by voice need an identified speaker on that person's own device; never on an unidentified voice | Must |
| MU-6 | A shared answer (the couple's weekend plan) uses only what both may see: shared calendar, the household budget line for fun, both people's stated interests; never one person's private notes | Must |
| MU-7 | Couples' profile for LEP: each person's interests plus a shared one, each person editing their own | Should |
| MU-8 | Guests (later, close friends): a guest identity with no access to personal stores, only what the owner shares for that visit | Could (later, DEC-0159) |
| MU-9 | Voiceprints are personal data: sealed at rest, never synced to a cloud, deletable by their owner | Must |
| MU-10 | A shared screen (a household display) shows household items; personal ones only after that person is identified | Should |

## Open

- **Q-09:** May the wife's account see Zac's LEP interests, and the reverse? Default: each person's interests are private, and the shared profile is shared.
- **Speaker identification on the phone** versus the PC versus the glasses: where the model runs (Prompt 07).
