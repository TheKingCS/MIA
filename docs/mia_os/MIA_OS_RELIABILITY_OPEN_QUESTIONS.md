# MIA OS: reliability open questions and risks (Prompt 14)

*Claude (Opus), 2026-11-18. Questions for Zac also appear in `MIA_OS_OPEN_QUESTIONS.md`.*

## 1. For Zac

| Q | Question | Recommended |
|---|---|---|
| **Q-95** | On MIA OS, updates download in the background. Should they install at a restart only when you say, or by themselves at night (say 3 am) when nothing's running? Either way a bad one undoes itself. | At night by themselves, with a message in the morning |
| **Q-96** | Where should the second copy of the nightly backup live, off the PC: an external USB drive left plugged in (about $60 for 2 TB), the laptop, or both? | An external drive, and the laptop too once it's set up |
| **Q-97** | A UPS (battery backup, about $150 to $250) so a power blip doesn't cut off overnight work or a write mid-way? | Yes, when convenient |
| **Q-98** | A monthly restore drill MIA runs by herself: restore last night's backup into a scratch folder, check every store opens, report, delete it? | Yes |

## 2. Risks

| ID | Risk | Response |
|---|---|---|
| R-74 | An update rolls back but the newer MIA already changed his data's shape | additive changes only; versioned migrations; the pre-update snapshot |
| R-75 | The only backup is on the same disk that fails | the off-PC copy (Q-96); the phone's sync |
| R-76 | A restore that's never tried doesn't work when needed | the monthly drill (Q-98) |
| R-77 | Windows updates restart the PC overnight until MIA OS | active hours; Night School resumes; MIA OS's own update timing |

## 3. Before Prompt 15

Prompt 15 builds, signs and tests the images and the phone app; it takes the update path (DEC-0257), the signature
check and the VM failure simulations as given.
