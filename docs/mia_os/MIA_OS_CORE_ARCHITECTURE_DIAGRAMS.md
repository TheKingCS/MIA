# MIA OS: core architecture diagrams (Prompt 05, deliverable 13)

*Claude (Fable), 2026-11-16. Planning only. The twelve diagrams Prompt 05 asks for, in Mermaid. In every diagram:*

- *grey boxes are **existing Linux** components, used as they are;*
- *blue boxes are **existing MIA** components;*
- *green boxes are **new or modified MIA** components this architecture proposes;*
- *dashed boxes are **optional or external**.*

*The text of each is in the document named under it. Nothing drawn here is built unless it is blue or grey. The
diagrams' syntax was checked by reading, not yet by a renderer (2026-11-16).*

## 1. MIA OS, high level

Linux underneath, untouched; MIA as services and a session on top; applications and devices around.

```mermaid
flowchart TB
  subgraph EXT["External (optional)"]
    cloud["Search, bank data, outside models, the relay"]:::opt
    devs["Phone, glasses, Pi, greenhouse"]:::opt
  end
  subgraph APPS["Applications"]
    native["MIA-native apps (manifests in the registry)"]:::mia
    exts["Extensions (sandboxed)"]:::new
    conv["Conventional apps (Flatpak, ordinary)"]:::linux
  end
  subgraph MIA["MIA platform (user services)"]
    shell["MIA's shell"]:::new
    capture["Capture agent"]:::new
    runtime["MIA Runtime: stores, actions, grants, schedule, registry, API"]:::mia
    model["Model server"]:::linux
  end
  helper["System helper (root, fixed operations)"]:::new
  subgraph GFX["Graphical and session"]
    login["Login screen"]:::linux
    comp["Compositor"]:::linux
    plasma["KDE Plasma"]:::linux
  end
  subgraph SYS["System services"]
    svc["systemd, logind, NetworkManager, PipeWire, polkit, journal, update mechanism"]:::linux
  end
  kernel["Linux kernel, drivers, firmware"]:::linux

  native --> runtime
  exts -->|capability contract| runtime
  conv -->|hands over a capture| capture
  shell --> runtime
  capture --> runtime
  runtime --> model
  runtime -->|adapters, as him| svc
  runtime -->|typed request| helper
  helper -->|after polkit| svc
  devs --> runtime
  runtime -.-> cloud
  shell --> comp
  plasma --> comp
  conv --> comp
  login --> comp
  comp --> kernel
  svc --> kernel
  model --> kernel

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
  classDef opt fill:#fff,stroke:#888,stroke-dasharray:4 3,color:#111
```

*Core architecture §2 and §3.*

## 2. Linux foundation

Everything in this diagram is the distribution's. MIA adds only files to the image.

```mermaid
flowchart TB
  fw["UEFI firmware, Secure Boot, TPM2"]:::linux --> bl["Boot loader: current and previous deployment"]:::linux
  bl --> k["Kernel and initramfs (in the image)"]:::linux
  k --> luks["Unlock LUKS2: TPM2 and a PIN"]:::linux
  luks --> root["Read-only root from the image; /etc and /var writable"]:::linux
  root --> sd["systemd"]:::linux
  sd --> sys["System services: logind, NetworkManager, firewall, journal, model server"]:::linux
  sd --> dm["Login screen"]:::linux
  dm --> um["User manager: PipeWire, portals, the MIA Runtime"]:::linux
  um --> sess["The chosen session"]:::linux
  img["Containerfile in the repository: Fedora base plus MIA's files"]:::new -.->|built, signed, staged by the update mechanism| root

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Linux foundation §3.*

## 3. MIA platform integration

How MIA's services meet Linux: adapters for reading and ordinary use, the helper for system changes.

```mermaid
flowchart LR
  subgraph RT["MIA Runtime (his user)"]
    core["Engine: stores, actions, grants, registry"]:::mia
    ad["Adapters: keys, power, audio, camera, network, devices, files, notifications, apps, system state"]:::new
    core --> ad
  end
  ad -->|D-Bus, as him| os1["logind, UPower, NetworkManager, BlueZ, UDisks2, notifications, portals"]:::linux
  ad -->|library| pw["PipeWire"]:::linux
  ad -->|read| st["Update status, systemd unit states, pressure, hwmon, journal"]:::linux
  ad -->|credential| cr["systemd credentials"]:::linux
  core -->|system action, approved in MIA| h["System helper (root)"]:::new
  h --> pk{"polkit: the OS asks him"}:::linux
  pk -->|confirmed| ops["Update mechanism, systemd, firewall, fwupd"]:::linux
  ops -->|state read back| h
  h -->|verified result| core

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Core architecture §4; privilege boundaries §3.*

## 4. Service dependencies, at start and while running

Solid arrows are "requires"; dotted are "wants" (works without). No solid arrow points from Linux to MIA.

```mermaid
flowchart TB
  multi["multi-user.target"]:::linux --> gtarget["graphical.target: login screen"]:::linux
  multi --> ollama["Model server"]:::linux
  gtarget --> usermgr["user@.service (his user manager)"]:::linux
  usermgr --> pipewire["PipeWire, D-Bus session, portals"]:::linux
  usermgr --> rt["mia-runtime.service"]:::mia
  rt -.->|wants| net["Network"]:::linux
  rt -.->|wants| ollama
  rt -.->|wants| pipewire
  usermgr --> gs["graphical-session.target"]:::linux
  gs --> comp["Compositor"]:::linux
  comp --> sh["mia-shell.service"]:::new
  comp --> cap["mia-capture.service"]:::new
  sh -.->|wants, shows a recovery page without it| rt
  cap -.->|wants| rt
  rt -.->|starts on demand| kids["Heavy jobs, her browser, extensions (transient units)"]:::new
  bus["System D-Bus"]:::linux -.->|activates on call| helper["mia-system-helper.service"]:::new

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*System service architecture §2 and §3.*

## 5. Graphical session

Two entries at login, one running at a time, sharing the person's services. The compositor for MIA's session is
provisional (proof of concept 3).

```mermaid
flowchart TB
  login["Login screen: MIA by default, or Plasma"]:::linux
  subgraph S1["MIA's session"]
    c1["Compositor (KWin provisional; cage on the Pi)"]:::linux
    sh1["MIA's shell, full screen"]:::new
    cap1["Capture agent"]:::new
    apps1["Ordinary app windows (if the compositor allows)"]:::linux
    c1 --- sh1
    c1 --- cap1
    c1 --- apps1
  end
  subgraph S2["Plasma session"]
    c2["KWin"]:::linux
    ps["Plasma shell"]:::linux
    mw["MIA as a window and tray item"]:::new
    cap2["Capture agent"]:::new
    apps2["Ordinary apps"]:::linux
    c2 --- ps
    c2 --- mw
    c2 --- cap2
    c2 --- apps2
  end
  login --> S1
  login --> S2
  subgraph SHARED["Shared: belongs to the user, not the session"]
    rt["MIA Runtime"]:::mia
    pw["PipeWire, his files, Flatpak data"]:::linux
  end
  sh1 --> rt
  mw --> rt
  cap1 --> rt
  cap2 --> rt

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Graphical and session architecture §3 and §4.*

## 6. Applications and the platform

Prompt 03's framework on OS-level services: three kinds of application, three different doors.

```mermaid
flowchart LR
  subgraph N["MIA-native app (in the image)"]
    man["Manifest: tools, actions, tiers, stores, jobs"]:::mia
    page["Its page in web/"]:::mia
  end
  subgraph X["Extension (not MIA's code)"]
    xman["Manifest, signed"]:::new
    xproc["Its process in a sandbox"]:::new
  end
  subgraph C["Conventional app"]
    fp["Flatpak or ordinary package"]:::linux
  end
  reg["Application registry and manager (in the runtime)"]:::mia
  man --> reg
  xman --> reg
  page -->|API: state, actions, live| rt["MIA Runtime"]:::mia
  reg --- rt
  xproc -->|capability contract only| rt
  rt -->|schedules its jobs, paces them| sch["Scheduler and homeostasis"]:::mia
  rt -->|transient unit, limits| sysd["systemd user manager"]:::linux
  sysd --- xproc
  fp -->|installed and updated by| flat["Flatpak, the image"]:::linux
  fp -->|file chooser, camera, screenshots| portal["Portals"]:::linux
  fp -.->|hands over a capture| cap["Capture agent"]:::new
  cap --> rt
  rt -->|launch, list, show permissions| flat

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*System service architecture §2.5; storage §4.*

## 7. IPC and communication

One mechanism per kind of conversation.

```mermaid
flowchart TB
  shell["Shell, browser tab"]:::new -->|HTTP and SSE, loopback, token| rt["MIA Runtime"]:::mia
  phone["Phone, glasses, Pi"]:::opt -->|HTTPS, pairing keys| rt
  tools["Capture agent, command line, browser extension's host"]:::new -->|same API over a Unix socket, caller user checked| rt
  conv["Conventional app"]:::linux -->|session D-Bus: org.mia.Capture1| tools
  rt -->|loopback HTTP| model["Model server"]:::linux
  rt -->|D-Bus| os["OS services"]:::linux
  rt -->|system D-Bus| helper["System helper"]:::new
  helper -->|polkit, then the owning service API| os
  rt -->|socket pair, JSON, capability contract| ext["Extension"]:::new
  rt -->|arguments, result file, exit status| job["Heavy job"]:::new
  bus(["In-process event bus"]):::mia --- rt
  rec[("Records in stores: runs, approvals")]:::mia --- rt

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
  classDef opt fill:#fff,stroke:#888,stroke-dasharray:4 3,color:#111
```

*IPC and communication architecture §1.*

## 8. Storage and filesystem

Separate lifetimes on separate subvolumes of one encrypted volume.

```mermaid
flowchart TB
  luks["LUKS2 volume (TPM2 and a PIN)"]:::linux --> btrfs["Btrfs"]:::linux
  btrfs --> img["Image deployments, read-only: the OS, MIA's code and Python environment, units, policies"]:::new
  btrfs --> etc["/etc: this machine's configuration"]:::linux
  btrfs --> home["home subvolume"]:::linux
  btrfs --> models["models subvolume, no snapshots: /var/lib/ollama"]:::linux
  btrfs --> var["/var: journal, coredumps"]:::linux
  home --> files["His files"]:::linux
  home --> mh["MIA_HOME (~/.local/share/mia): every store, sealed"]:::mia
  home --> cache["~/.cache/mia: indexes, thumbnails (rebuilt, never backed up)"]:::mia
  home --> fpd["~/.var/app: conventional apps' data"]:::linux
  mh --> backup["Nightly backup to a second drive or share"]:::mia
  run["$XDG_RUNTIME_DIR/mia: sockets, session token (memory)"]:::new

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Storage and filesystem architecture §2.*

## 9. Hardware abstraction

MIA's code begins at the adapter; everything left of it is Linux.

```mermaid
flowchart LR
  hw["Hardware"]:::linux --> drv["Kernel drivers"]:::linux
  drv --> pw["PipeWire: microphones, speakers, cameras"]:::linux
  drv --> nm["NetworkManager"]:::linux
  drv --> bz["BlueZ"]:::linux
  drv --> up["UPower, logind, hwmon"]:::linux
  drv --> ud["udev, UDisks2"]:::linux
  drv --> gpu["Mesa, ROCm or Vulkan"]:::linux
  gpu --> ms["Model server"]:::linux
  drv --> tty["Serial and USB boards"]:::linux
  pw --> ad["MIA's adapters"]:::new
  nm --> ad
  bz --> ad
  up --> ad
  ud --> ad
  tty --> df["Device framework drivers"]:::mia
  df --> ad
  ms --> llm["Model interface"]:::mia
  ad --> cap["Capability: tier, grant, record"]:::mia
  llm --> cap
  cap --> app["A MIA app or tool"]:::mia
  pw --> portal["Portals: per-app permission"]:::linux
  portal --> fapp["A Flatpak app"]:::linux

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Hardware abstraction architecture §1 to §3.*

## 10. Privilege and trust boundaries

Each box can reach the next only through the labelled door. Root appears once.

```mermaid
flowchart TB
  out["Outside text: pages, mail, captures"]:::opt -->|marked as outside, no change in that turn| rt
  ext["Extension: sandbox, no network, own folder"]:::new -->|declared capabilities only| rt
  conv["Conventional app: Flatpak sandbox or his user"]:::linux -->|a capture, nothing else| capt["Capture agent: his user"]:::new
  capt --> rt
  sh["Shell: his user, holds no records"]:::new -->|API with a token| rt
  rt["MIA Runtime: his user, never root; the only writer of his records"]:::mia
  rt -->|as him: what his session may already do| os["OS services with their own polkit policy"]:::linux
  rt -->|typed system action he approved in MIA| help["System helper: ROOT, fixed operations, sandboxed unit"]:::new
  help --> pk{"polkit dialog, drawn by the OS outside MIA"}:::linux
  pk -->|he confirms at the machine| priv["Update mechanism, systemd, firewall, firmware"]:::linux
  priv --> kern["Kernel: Secure Boot, signed image, SELinux"]:::linux
  ms["Model server: its own user; sees only prompts"]:::linux --- rt

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
  classDef opt fill:#fff,stroke:#888,stroke-dasharray:4 3,color:#111
```

*System privilege boundaries §1 to §3.*

## 11. Resource management

Slices decide who wins; homeostasis decides whether MIA's own background work runs at all.

```mermaid
flowchart TB
  subgraph SYS["system.slice"]
    oll["Model server: memory ceiling; VRAM managed by routing"]:::linux
  end
  subgraph USR["his user"]
    sess["session.slice: compositor, shell. Protected"]:::linux
    app["app.slice: his applications"]:::linux
    mia["mia.slice: the runtime, capture agent. Protected, small"]:::new
    bg["mia-background.slice: heavy jobs, her browser. Low weight, killed first"]:::new
    ex["mia-ext.slice: extensions. Hard ceilings"]:::new
  end
  psi["Kernel pressure: processor, memory, disk"]:::linux --> oomd["systemd-oomd"]:::linux
  psi --> homeo["Homeostasis: deferrable work waits, says so once"]:::mia
  pwr["UPower, power profile, logind sleep signals, temperatures"]:::linux --> homeo
  homeo -->|starts or holds| bg
  oomd -->|kills first| bg
  oomd -.->|last| app
  route["Model routing (Prompt 07)"]:::opt --> oll

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
  classDef opt fill:#fff,stroke:#888,stroke-dasharray:4 3,color:#111
```

*System resource management §1 and §2.*

## 12. Build versus reuse

Almost everything is grey. What MIA writes is on the right.

```mermaid
flowchart LR
  subgraph USE["Used or configured as it is"]
    a["Kernel, firmware, boot"]:::linux
    b["systemd, logind, journal, oomd"]:::linux
    c["Update mechanism (bootc)"]:::linux
    d["KDE Plasma, compositor, login screen, portals"]:::linux
    e["NetworkManager, firewalld, PipeWire, BlueZ, UPower, UDisks2, fwupd"]:::linux
    f["Flatpak, bubblewrap, polkit, SELinux, LUKS"]:::linux
    g["Model server"]:::linux
  end
  subgraph HAVE["Existing MIA"]
    h["Runtime, stores, actions, grants, registry, scheduler, homeostasis, gate, API, web front end, sealing"]:::mia
  end
  subgraph WRITE["New or modified MIA"]
    i["The image definition, units, slices, session entry, polkit actions, udev rules"]:::new
    j["Adapters' Linux halves"]:::new
    k["Shell host and recovery page"]:::new
    l["Capture agent"]:::new
    m["System helper"]:::new
    n["Runtime: readiness, watchdog, journal logging, socket, workers"]:::new
  end
  USE --> HAVE
  HAVE --> WRITE

  classDef linux fill:#e6e6e6,stroke:#666,color:#111
  classDef mia fill:#cfe3ff,stroke:#2a5db0,color:#111
  classDef new fill:#d5f2d5,stroke:#2e7d32,color:#111
```

*Build versus reuse §2 and §3.*
