# MIA OS: distributed open questions and risks (Prompt 12)

*Claude (Opus), 2026-11-18. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

**Answered 2026-11-18.** Q-87: "display that connects to tv": the Pi 5 first becomes the household display, on the TV over HDMI. Q-88 yes. Q-89 yes: he already has the laptop, not sure its hardware does everything; it runs as a full engine and thinks on the PC when it can (its model and memory to be checked). Q-90 yes. DEC-0241, 0244, 0247 approved.

| Q | Question | Recommended |
|---|---|---|
| **Q-87** | What should the Raspberry Pi 5 do first: the Zeta Astralis prototype (a small screen on your forearm), the household display for you and your wife, or a second always-on node in the house? | The household display: it's the one you said is important, and the Pi's kiosk mode is built for it |
| **Q-88** | Away from home, MIA is reached only through Tailscale, never through an open port on your router. OK? | Yes |
| **Q-89** | When the laptop comes, should it run MIA's whole engine like the phone (its own copy of your records, works without the PC, syncs when it can)? | Yes |
| **Q-90** | When you unlink a lost phone, should MIA on that phone erase its MIA data the next time it reaches your PC? | Yes |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-65 | A third full engine makes sync conflicts more frequent | one base per device, all through the hub; conflicts kept and told (REQ-DST-023) |
| R-66 | A lost phone that never reconnects keeps his data | sealed at rest with its own key; unlinked at once |
| R-67 | The glasses depend on the phone app staying alive | Android's foreground service; the glasses say so when it's gone |
| R-68 | The PC off means no big model and no specialists away from home | the phone's own model said plainly; a model node later (DEC-0202) |

## 3. Before Prompt 13

Prompt 13 designs security, privacy, identity and permissions in full; it takes this prompt's keys and scopes
(DEC-0242), the household key (Q-82) and the lost-device erase (Q-90) as given.
