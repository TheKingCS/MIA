# MIA OS: storage and filesystem architecture (Prompt 05, deliverable 5)

*Claude (Fable), 2026-11-16. Planning only. The filesystem, where everything lives, who owns it, and how
applications and MIA reach files without more access than they need. Memory and intelligence stores are Prompt
07's; backup and recovery procedures are Prompt 14's. Decision: DEC-0193 (proposed). Comparison of filesystems:
[MIA_OS_CORE_TECHNOLOGY_EVALUATION.md](MIA_OS_CORE_TECHNOLOGY_EVALUATION.md) §6.*

## 1. Filesystem and encryption

- **The PC:** Btrfs on LUKS2. One encrypted volume, unlocked at boot by the TPM with a PIN (REQ-SEC-001), holding
  Btrfs subvolumes so the parts with different lifetimes are separate without fixed partition sizes.
- **The Pi:** ext4 as Raspberry Pi OS installs it. Its disk encryption is a later question (DEC-0169: the Pi may
  have no TPM); MIA's own sealing still protects the stores.
- **No proprietary filesystem, no ZFS** (an out-of-tree module on an image-based system).

Two layers of protection, on purpose: the disk's encryption protects against a stolen drive; MIA's sealing of
personal and household stores (`core/at_rest.py`, the key held by a systemd credential on Linux, DEC-0126) protects
a single copied file and keeps one person's stores closed to another account on the same machine (REQ-SEC-002).

## 2. The layout

It follows the Filesystem Hierarchy Standard as an image-based Fedora arranges it, and the XDG Base Directory
Specification for everything per person. Nothing of MIA's invents a new top-level place.

| What | Where | Subvolume | Owner | Written by | In updates | In MIA's nightly backup |
|---|---|---|---|---|---|---|
| The OS, **and MIA's code with its locked Python environment** | `/usr` (MIA's at `/usr/lib/mia`) | the image (read-only) | system | the image build only | replaced whole | no (rebuilt from the repository) |
| Units, session entry, polkit actions, udev rules, defaults | `/usr/lib/systemd`, `/usr/share/wayland-sessions`, `/usr/share/polkit-1`, `/usr/lib/udev` | the image | system | the image build | replaced whole | no |
| This machine's configuration | `/etc` | kept, merged on update | system | OS tools; the helper | merged | the differences, listed (Prompt 14) |
| His files | `/var/home/<him>` (seen as `/home/<him>`) | `home` | him | him; MIA only inside granted folders | untouched | his choice of folders |
| **MIA's data: every store, sealed** | `$XDG_DATA_HOME/mia` (`~/.local/share/mia`), which is `MIA_HOME` | `home` | him | **the runtime only** | untouched | **yes, all of it** |
| MIA's device and person settings | inside `MIA_HOME` (as today) | `home` | him | the runtime | untouched | yes |
| MIA's logs and health history | the journal; `$XDG_STATE_HOME/mia` for what must outlive the journal's rotation | `home` | him | the runtime | untouched | no |
| MIA's caches (thumbnails, the browser's cache; **not** the meaning index: Opus's review of prompt 23 found an embedding index carries his records' content, so it lives sealed in `MIA_HOME`) | `$XDG_CACHE_HOME/mia` | `home`, excluded from snapshots | him | the runtime and its children | untouched | **no**: every cache is rebuilt from the stores |
| Sockets, the session token, locks | `$XDG_RUNTIME_DIR/mia` (memory, gone at logout) | | him | the runtime | | no |
| Her browser's profile | `MIA_HOME/browser/<person>` | `home` | him | her browser | untouched | sign-ins yes, cache no |
| An extension's data | `MIA_HOME/extensions/<id>` | `home` | him, lent to that extension's sandbox | that extension only | untouched | yes |
| A conventional app's data | `~/.var/app/<app-id>` (Flatpak), or wherever that app keeps it | `home` | him | that app | untouched | his choice |
| **Models** (tens of gigabytes) | `/var/lib/ollama` | `models`, no snapshots | the model server's user | the model server | untouched | **no**: re-downloadable; a list of which models is kept |
| Voices, the speech and embedding models | `/usr/share/mia/models` when shipped in the image; `/var/lib/mia/models` when fetched later | image or `models` | system | the image build; a system action | | no |
| The journal, coredumps | `/var/log`, `/var/lib/systemd/coredump` | `var` | system | systemd | untouched | no |
| Temporary files | `/tmp` (memory), each service's private one | | | | | no |
| Shared household data | under the first person's `MIA_HOME` today (`data/` and `data/households/<id>`); `/var/lib/mia/households/<id>` with a group when a second person on the same machine joins | `home` or `var` | the household | the members' runtimes | untouched | yes |
| The inbox folder, vault files, paintings | inside `MIA_HOME` | `home` | him | the runtime | untouched | yes |

**Why MIA's code is in the image and not in his home:** it is then signed, read-only, the same on every boot, and
rolled back with the system (REQ-ARC-011, REQ-SEC-008). The engine already keeps what she writes apart from her
code through `MIA_HOME` (DEC-0155), with a test that nothing is written into the code's folder. Development happens
from a checkout in his home with `MIA_HOME` pointed at a separate folder, never the live one.

**Ownership in one line each:** *system-owned* is what the image and `/etc` hold; *user-owned* is his home;
*application-owned* is a store or an app's own directory, reached by others only through capabilities
(REQ-FUN-041); *MIA holds nothing of her own*: every record is his or the household's.

## 3. Snapshots and backups

- **OS:** the previous deployment is the OS's snapshot; nothing more is needed.
- **MIA's data:** the nightly backup (`core/auto_backup.py`, REQ-REL-007) stays the authority, to a second drive or
  a network share he chooses. It is tested by restore, not by existing.
- **Btrfs snapshots of `home`** are a cheap local addition (a point in time before a risky operation, such as
  moving to a new Fedora). They aren't a backup (same disk) and they are Prompt 14's to schedule. The `models` and
  cache locations are kept out so snapshots stay small.
- **The durable undo history** proposed in prompt 23's review (before-states kept for a while) lives inside
  `MIA_HOME`, sealed, with its own retention; it is not a filesystem feature.

## 4. Storage and data service boundaries

**No unified storage service.** Linux's filesystem is the file service; MIA's stores are the record service. A
second abstraction over both would be a new thing to secure and nothing would be gained.

| Need | Answer |
|---|---|
| MIA-native apps reading and writing records | the stores, through the runtime: capabilities, events, links, history. No app opens another's store (REQ-FUN-041); today enforced by layering and review, per process once extensions are sandboxed |
| MIA reading his documents | only inside folders he granted (REQ-FUN-006), through the files adapter. Enforced twice: by MIA's own grant list, and by the kernel narrowing the worker that touches files to those folders (privilege document §5) |
| MIA moving or deleting a file of his | always a proposal he approves; deletions go to the desktop's trash, never straight to gone |
| A conventional app's files | that app's business. A Flatpak app sees only what its permissions and the file-chooser portal give it; MIA shows those permissions before install (REQ-FUN-042) |
| Search and document indexing | one index, rebuilt from the stores and granted folders, **sealed in `MIA_HOME`** like the records it was made from (embeddings carry their content; prompt 23's review, section 14). Not a system-wide indexer: KDE's Baloo stays Plasma's own |
| Metadata | a file's meaning to MIA (which asset or project it belongs to) is a link in `core/links.py`, never extended attributes that other tools would lose |
| Databases | JSON files with atomic writes stay the stores (REQ-REL-005). SQLite where a store already uses it. No database server |
| External and removable drives | mounted by the desktop (UDisks2) as on any Linux; MIA sees one only when he grants a folder on it; backups to one are an existing setting |
| Network storage | mounted by the OS; treated as a granted folder that may vanish (the adapter reports "not reachable", never an empty folder) |
| Synchronisation between devices | `core/sync.py` and the home link; Prompt 12's |
| MIA and the shell | none. No tool runs a shell command on the system; file operations are typed adapter calls with paths checked against the grant |

## 5. What depends on later prompts

- Prompt 07: where memory, embeddings and model caches sit within this layout (the places exist: `MIA_HOME`, the
  cache, the `models` subvolume); a schema and version per store (T-03).
- Prompt 13: the exact sealing and key design; the sandbox's view of the filesystem.
- Prompt 14: backup scope for `/etc` and his folders; snapshot policy; the restore rehearsal.
- Prompt 12: where household data lives when two people share one machine.
