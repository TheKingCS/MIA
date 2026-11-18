# MIA OS: the final resource and hardware plan (Prompt 17 §11; 17b §7)

*Claude (Opus), 2026-11-18. Version 1.0. Figures marked "estimate" are estimates; prices are typical US retail, not
quotes.*

## 1. Hardware

| Item | Needed for | When | One-time cost (estimate) | Status |
|---|---|---|---|---|
| The reference PC as built (Ryzen, RX 7900 XTX 24 GB, one M.2 slot, TPM 2.0) | everything | now | owned | DEC-0201 |
| A USB stick, 8 GB or more | HW-01, then FW-09's recovery stick | **now**: it starts the critical path | $10 | waiting on Zac |
| A 4 TB NVMe drive (PCIe 4) | MV-01 | before MV-01 | $200 to $300 | waiting on Zac |
| A USB-C NVMe enclosure | HW-02, the Windows fallback | with the drive | $25 | approved (Q-102) |
| An external drive, 2 TB or more | the off-PC backup (DEC-0259) | before MV-01 | $60 to $90 | approved (Q-96) |
| A UPS | night updates and long jobs | when convenient | $150 to $250 | approved (Q-97) |
| The Pi 5 and an HDMI cable | the household display | Beta | owned; $20 | — |
| The laptop | a third full engine | Beta | owned; its suitability unknown until its model is known | waiting on Zac |
| A model-serving node | only if measured necessary (DEC-0202) | after Stable | — | not planned |

## 2. Recurring costs

| Cost | Estimate | Notes |
|---|---|---|
| Electricity | PC on all day at about 100 W on average with night jobs: roughly 70 kWh a month, about $10 to $15 at $0.15 to $0.20 a kWh (estimate; his rate decides) | the GPU at full load draws about 350 W, so long night benches cost more |
| Cloud inference | $0 required: no cloud is configured in the MVP; sensitive data never goes to a cloud (DEC-0251) | any later cloud use is per request with consent |
| CI | $0 while the repository is public (Q-99) | a private repository would cap minutes; the VM test is about an hour each run |
| Remote access | Tailscale's free personal tier | |
| Backup storage | the external drive and the laptop: no subscription | |
| Software licences | none paid | Piper's GPL-3.0 needs a licence decision for the repository (Q-108) |
| Device replacement | drives and the UPS battery every few years | estimate |
| Development | his Claude and ChatGPT subscriptions (already in use) | Codex runs under his ChatGPT sign-in |

## 3. People and skills

| Work | Who | Note |
|---|---|---|
| Most implementation (FW-01, 02, 04, 07 to 12, the Windows backlog) | Claude Code | suited to AI-assisted work: code plus tests in a VM |
| Linux desktop specifics (FW-03) | Claude Code, verified by running | the least certain package; facts about KWin and the login manager are proven in the VM, not assumed |
| Security-critical code (FW-05, FW-06, WP-02, WP-03) | Claude Code, reviewed by Codex | an experienced human's review is worth asking for if Zac knows someone |
| Real hardware (HW-01, HW-02, MV-01, MV-02) | Zac, guided | about two hours, two sessions, then a week |
| Approvals, releases, decisions | Zac | no AI approves its own change |

## 4. Compute for development

The PC (GPU benches at night), GitHub's hosted runners (CI, the VM with KVM: it works today but isn't a documented
guarantee, so a failing KVM check fails loudly), nothing rented.
