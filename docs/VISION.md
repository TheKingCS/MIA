# M.I.A. — Long-Term Vision & Multi-Project Architecture

This document captures the long-term mission behind M.I.A. and how it
relates to the near-term work in `docs/ROADMAP.md`. Read this for
*why* and *where this is all going*; read `ROADMAP.md` for *what we're
actually building next*. Keeping these separate is deliberate — see
"Why this is a separate document" below.

## Mission

M.I.A. is not a chatbot. It's meant to become a modular, offline-first,
privacy-focused engineering partner, survival assistant, research
platform, automation system, and lifelong knowledge base — one whose
value compounds over years, improving through every completed project
rather than staying static.

Guiding principles: offline-first, privacy-first, modular, expandable
hardware, long-term maintainability, security by design, user ownership
of all data, transparent reasoning, continuous learning through
documented experience, and built to assist human decision-making rather
than replace it.

## The four-project architecture

| Project | Role | Status |
|---|---|---|
| **1. M.I.A.** | "The Brain" — the portable field device and its core intelligence | **In progress.** This is "M.I.A. Core," the Pi5 kiosk device documented in `ROADMAP.md`, currently at v0.2. |
| **2. Personal Home Cloud Infrastructure** | "The Nervous System" — a stationary, more powerful compute extension the Pi5 docks to or syncs with | Not started. This is where compute-heavy reasoning belongs (see below). |
| **3. Smart Environment** | "The Senses" — sensor networks, environmental monitoring, smart home integration | Not started. Overlaps with the Agriculture/Smart Home/Power sections already planned in `ROADMAP.md`. |
| **4. Robotics and Physical Systems** | "The Hands" — robotic arms, drones, mobile robots, prosthetic research | Not started. Overlaps with the Fleet section already planned in `ROADMAP.md`. |

**Every future project should expand M.I.A.'s capabilities, and every
improvement to M.I.A. should make future projects easier.** That
compounding relationship is the actual long-term goal — not any single
feature.

## Why this is a separate document from ROADMAP.md

This vision includes ideas (a multi-agent "Expert Council," genetic
algorithms, particle swarm optimization, a full simulation layer) that
are individually large enough to be their own multi-year efforts. If
they lived in the same document as the concrete, testable v0.2/v0.3
milestones, it would become impossible to tell "what we're building
this month" from "what we might build in year three" — and that
confusion is the single biggest risk to this project actually shipping
a working device. This document is the North Star. `ROADMAP.md` is the
map of the next several steps. Neither should be edited to look like
the other.

## Critical evaluation (honest assessment, not just enthusiasm)

- **Scope is the primary risk.** An Expert Council of debating
  specialized AI agents, genetic/PSO optimization, and a full
  simulation-before-recommending layer are each substantial research
  efforts on their own. Treat everything in this document beyond
  "Project 1, current phase" as aspirational and revisit-when-ready,
  not as a backlog to start executing now.
- **Hardware mismatch is real, but the document already contains its
  own answer.** None of the compute-heavy reasoning (Expert Council,
  GA/PSO, simulation) belongs on the Pi5 — it belongs on Project 2 (the
  Home Cloud "Nervous System"). The Pi5's job is to stay light,
  reliable, and always-available; the home system's job is to do heavy
  reasoning and sync results back down. This is also the real
  justification for the "dock to a computer" goal from the original
  brief — it's not just file transfer, it's compute offload.
- **"Continuous learning from every project" should start boring, not
  clever.** The realistic v1 of this is structured logging (already
  designed into the event bus / Activity Log) plus good search over
  your own project history — not machine learning. "I found two
  previous robotic arm projects, Project B used stronger servos" is
  achievable with a well-indexed database and an LLM summarizing
  retrieved records, long before anything resembling true learning is
  needed.
- **Security architecture is correctly flagged as mandatory, but is
  currently a gap.** v0.2 only has Backup/Restore. Encrypted backups
  and encrypted credential storage (wifi passwords, radio configs, any
  future API keys) should be pulled forward into the roadmap; full
  role-based permissions and audit logging are reasonable to defer
  until multiple profiles or networked access make them necessary.
- **Missing principle, worth adding explicitly: graceful degradation.**
  A device this dependent on sensors, radios, and an AI assistant needs
  a defined "safe mode" — if the Assistant or any single module fails,
  the base device (reference library, calculator, comms, navigation)
  must keep working. `ModuleManager`'s per-module failure isolation
  already supports this by accident; it should be treated as a first
  principle going forward, not an implementation detail.

## Where the new concepts map into existing plans

| Vision concept | Where it lives |
|---|---|
| Artificial Expert Council (multi-agent debate) | Project 2 (Home Cloud). Not feasible on Pi5 hardware; the Assistant module (v0.5) stays a single capable model on-device, with an optional "consult the Council" action that hands off to Project 2 when connected. |
| Genetic Algorithms / Particle Swarm Optimization | Project 2. A future "Optimization Engine" service, invoked by Workshop & Electronics / The Lab modules when docked to Project 2's compute. |
| Simulation Layer | Project 2, same reasoning as above. |
| Continuous Learning Framework / Personal Engineering Database | Extends the already-planned Data Logger, Notes/Journal Engine, and Activity Log (see `ROADMAP.md`'s shared core services) — implemented as structured storage + search, not ML, for the foreseeable future. Directly answers the "what did I do on Project Rocket Boots" goal from earlier. |
| Security Architecture (encryption, RBAC, audit log) | Pulled forward into v0.2's Backup/Restore milestone (encrypted backups, encrypted credential storage) with RBAC/audit logging deferred to whenever multi-profile or networked access makes them load-bearing. |
| Character/avatar, personality, transparency about uncertainty | Already planned — v0.6 Character/companion system, event-bus driven. |
| Smart Environment (sensors, GPS, LoRa, SDR, cameras) | Already covered by Project 1's Communications, Navigation, Agriculture, and Smart Home sections; Project 3 is the larger-scale version of the same idea once dedicated sensor infrastructure exists beyond the Pi5 itself. |
| Robotics / Drones / prosthetics research | Already covered by Project 1's Fleet section for what connects directly to the Pi5; Project 4 is the larger standalone robotics effort. |

## Realistic phased horizon (coarse-grained, not a commitment)

| Horizon | Focus |
|---|---|
| **Now** | Project 1, M.I.A. Core v0.2–v1.0 per `ROADMAP.md` — a working, reliable, offline field device |
| **Next** | Project 1 continues to v1.0+ (Fleet, Communications, Navigation, Agriculture, Medical, etc., as real hardware is acquired) |
| **Later** | Project 2 (Home Cloud) begins — this is where Expert Council, GA/PSO, and simulation become realistic to attempt, once Project 1 is stable and there's a genuine compute-offload target to build against |
| **Eventually** | Projects 3 and 4 — likely absorbed largely into Project 1's existing section structure rather than needing wholly separate builds, revisited once real hardware for each exists |

The goal is not to build every capability in this document. The goal
is a device that is genuinely useful today, architected so that none of
these future directions are foreclosed.
