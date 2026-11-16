# MIA OS: the minimum viable MIA OS (Prompt 04, deliverable 12, with §25 to §27)

*Claude (Opus), 2026-11-15. Planning only. DEC-0182, approved 2026-11-15. The requirements tagged `MVP` in the
specification are this release; `R1` is the first Zac could use as his only PC system every day.*

## 1. What belongs where (§25)

| Class | What | Boot needs it? |
|---|---|---|
| 1 Core OS | the Linux image: kernel, drivers, systemd, login, disk encryption, networking, PipeWire, the compositor(s), Flatpak, updates and rollback, recovery | yes |
| 2 Core MIA platform | the MIA Runtime: stores, history and links, the capability and app registries, the action contract, grants, the scheduler, homeostasis, the gate, sync, model backends, the local API, the web front end's server | MIA's session needs it; the OS doesn't |
| 3 Native MIA apps | the ~53 apps in `apps/` (Home, Money, Greenhouse, Kitchen…) | no; each can fail alone |
| 4 Optional apps | Flatpak apps he chooses | no |
| 5 AI capabilities | the model runner (Ollama), the models, STT and TTS, vision, embeddings | no; their absence degrades conversation only |
| 6 Background services | jobs, daily checks, watches, backups | no |
| 7 Device-specific | the phone app, the glasses relay, the homestead node, Pi images | no |
| 8 External integrations | Plaid, mail, SearXNG, feeds, Tailscale | no |
| 9 Experimental and future | Forge, extensions host, spatial interfaces, speaker identification | no |

Only class 1 is privileged. Nothing of MIA's runs as root (REQ-ARC-010).

## 2. The MVP (§26)

**The smallest coherent MIA-first environment on the reference PC:**

1. **Boot and session:** the signed image; the disk unlocked; MIA's session by default; KDE Plasma one choice away;
   the previous deployment and recovery at boot.
2. **MIA's primary interface:** her web front end full screen in her session (what the Windows desktop app shows today,
   DEC-0124), with Talk, search, Home, Apps and the switch to Plasma.
3. **Conventional desktop:** Plasma with Firefox, a file manager, a terminal, LibreOffice and the dev tools.
4. **App management:** her apps from the registry with their status; Flatpak installs on his yes.
5. **Core interaction:** text everywhere, voice on the PC, every capability by screen and voice.
6. **Local-first intelligence:** Ollama on the GPU with the everyday and strong models; no cloud configured.
7. **Memory and context:** every store migrated from Windows, the history, links, memories on "keep it".
8. **Permissions:** the tiers and grants as built (M4); the runtime unprivileged; the helper for the few system
   operations the MVP needs (updates, restart services, power).
9. **Settings:** MIA's Settings and the OS's System Settings, reachable from her session.
10. **Devices:** the phone and the glasses working against the Linux PC exactly as against Windows.
11. **Diagnostics:** the runtime's health, the app statuses, the Fix-It Log, `systemd-analyze` for boot.
12. **Recovery:** nightly backups, a rehearsed restore, a USB recovery path.
13. **Updates:** atomic image updates with rollback.

**Existing components that make this fast:** the whole engine (it already runs headless on Linux: the Linux run on
2026-11-15), the web front end, the runtime and its systemd unit (`deploy/install_runtime.sh`), the sealed-store key on
Linux (DEC-0169), the app registry and grants, the phone app, the relay, the backups.

**Deferred without losing the identity:** the Universal Action Layer on any selection (R1), meaning search (R1),
cross-app plans as one approvable plan (R1), workspaces (R1), speaker identification (Mature), Forge (Mature), the
extensions host (R1, but nothing needs it before third-party code exists), immersive modes (Mature), smart displays,
the Pi runtime and the truck (later).

**Why this isn't a chatbot on Linux:** the MVP is a whole working desktop whose default is a personal intelligence over
all of his records, with checked capabilities, a history of every change, grants and undo, and it stays a working
computer when the intelligence is gone.

## 3. Completion conditions

The MVP is complete when every `Must · MVP` requirement passes its verification (the matrix lists them), the
scenarios S-01, S-03, S-04, S-09, S-12, S-13, S-14, S-16, S-17 and S-18 pass on the image, Zac has used it for a week
as his main system with Windows still on its own drive (dual boot, DEC-0157), and nothing in his data was lost in the
move (REQ-CMP-002).

## 4. Long-term direction (§27), kept apart from the first system

| Direction | Realistic now | Later | Speculative |
|---|---|---|---|
| Personal computing environment | the MVP and R1 | — | — |
| Distributed personal AI | the PC, phone, glasses | the Pi runtime, the truck | dedicated hardware |
| Multi-device assistant | sync, handoff | device capability reports | — |
| Smart home and homestead | watch the node; devices with grants | MIA in more of the homestead | — |
| Knowledge and productivity | records, history, links, search | meaning search, workspaces, the knowledge graph (prompt 23) | — |
| Extensible platform | the registry, Forge in the lab | the extensions host | a public ecosystem (rejected: DEC-0177) |
| Spatial and wearable | glasses cards | AR on the glasses | full spatial computing |
| Self-maintaining | inspection, the lab, loops, his approvals | the lab proposing more on its own | — |
