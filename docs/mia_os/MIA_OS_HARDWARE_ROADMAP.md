# MIA OS: hardware roadmap (Prompt 06 §18)

*Claude (Opus), 2026-11-17. Planning only. Each stage starts on a trigger, not a date; purchases are Zac's.*

| Stage | Hardware | Trigger | Cost (Nov 2026, approximate) | Unlocks |
|---|---|---|---|---|
| **H0, now** | the PC as built, the phone, the glasses | — | none | MIA OS MVP (DEC-0201) |
| **H1, small** | a USB stick; a 2 to 4 TB NVMe; a USB UPS | PoC 1; disk past 80%; the first lost overnight run | $10; $150 to $350; $150 to $250 | Fedora on the PC; room for models and packs; safe long jobs |
| **H2, homestead** | Pi 5 node, ESP32, sensors, relays, its UPS; Meshtastic radios | the greenhouse build starts (DEC-0150) | per `homestead/` and `docs/HARDWARE.md` | the greenhouse under the node's control |
| **H3, model node** | a 128 GB unified-memory machine (Ryzen AI Max+ 395 class) | the bench shows a specialist needs a model that doesn't fit, or W1 shows the card can't serve the Workroom, or an independent reviewer must stay loaded | $3,300 to $4,350 | 70B and 120B models, two families loaded at once (DEC-0202) |
| **H4, MIA Core on a Pi** | Pi 5 with the AI HAT+ 2 | MIA OS stable on the PC (DEC-0015's order) | about $250 with the HAT | MIA where the PC isn't |
| **H5, memory** | 64 GB (2 x 32 GB) | prices fall, or VMs and agents run out of memory | $750 to $1,400 now | headroom |
| **H6, rebuild** | an ATX board with two x16 slots | the PC is replaced anyway | — | two cards in one box |

The order follows DEC-0015 (PC, phone, glasses, then Pis). Nothing in H2 to H6 blocks the MVP.
