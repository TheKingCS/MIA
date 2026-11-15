# MIA OS: functional acceptance requirements (Prompt 02 §15)

*Claude, 2026-11-15. These are testable statements. Targets marked
(provisional) need hardware measurements first.*

**Conversation**
- FR-C1: An answer about MIA's own capabilities names only capabilities in `core/capabilities.py`; tested by asking about one that doesn't exist.
- FR-C2: The model unavailable gives the human "unavailable" reply within 5 s (provisional), and the screens keep working.
- FR-C3: No reply contains "I don't know what to do" or similar dead ends in the person cases (`tests/live_model_check.py`).

**Memory**
- FR-M1: A memory pulled from a conversation can be seen, corrected and deleted by its owner.
- FR-M2: A deleted memory never comes back into context: not from sync, a backup restore or a later extraction of the same sentence.
- FR-M3: Another person's memories are never in a turn's context.

**Voice and speakers**
- FR-V1: With two enrolled people, each turn is attributed to the right speaker in at least 95% of test clips (provisional).
- FR-V2: An unidentified speaker gets "who's this?", and private data and approvals stay locked.

**Apps and actions**
- FR-A1: Every action has a tool and a screen control, or a decided exception (`core/parity.py`).
- FR-A2: Every change is undoable or labelled as not undoable before approval.

**Smart Closet**
- FR-SC1: Pieces can be added, edited and removed by screen and by voice.
- FR-SC2: A suggestion for a cold, rainy work day never includes only warm-weather pieces, is no more formal than the day needs, and prefers pieces not worn recently.
- FR-SC3: A rated outfit changes later suggestions (a 1-star outfit isn't suggested again unless asked).
- FR-SC4: With no weather, the suggestion says so rather than guessing.

**Life Enrichment Protocol**
- FR-L1: Events past their date never appear.
- FR-L2: The same event from two sources appears once.
- FR-L3: Every suggested outing shows an estimated cost (fuel, entry, food) and whether it fits the fun money left this month. It never suggests spending money already reserved for bills or goals.
- FR-L4: Unverified listings are labelled unverified.
- FR-L5: Nothing is booked or bought without the person's approval.
- FR-L6: Declined or done experiences aren't suggested again unless asked.

**Cross-app**
- FR-X1: A multi-app request ("prepare for the weekend's greenhouse work") becomes one plan the person can see and approve step by step (Prompt 08).

**Search and discovery**
- FR-S1: Every capability is findable by search and by asking.

**Sync**
- FR-Y1: A change made offline on the phone appears on the PC after the next sync, and a concurrent edit is merged or flagged, never silently lost.

**Multi-user**
- FR-U1: MU-1 to MU-6 in `MIA_OS_MULTI_USER_REQUIREMENTS.md`, each with a test.

**Send to MIA**
- FR-T1: A selection from another app becomes a proposal. Its text is marked untrusted, and nothing runs until chosen.
