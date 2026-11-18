# MIA OS: engineering diagrams (Prompt 15)

*Claude (Opus), 2026-11-18. Mermaid.*

## 1. From a change to his machines

```mermaid
flowchart LR
  DEV["a change (Claude, MIA's lab, another model)"] --> SUITE["full suite, docs, maps"] --> PUSH["push to master"]
  PUSH --> CI["CI: Linux, Windows, phone, image, VM"] --> NEXT["next channel"] --> OK{"his approval / monthly"} --> STABLE["stable"] --> MACH["his machines update at night"]
```

## 2. Her own change

```mermaid
flowchart LR
  NS["Night School exercise"] --> LAB["lab worktree"] --> CHK["protected list, suite before/after"] --> INS["Claude's pass"] --> MERGE["merge, suite, revert on failure"] --> SUM["daily summary, Undo"]
```

## 3. Tests in layers

```mermaid
flowchart TB
  U["unit"] --> C["contract"] --> I["integration"] --> R["rules (docs, tiers, parity, loops)"] --> AI["AI quality sets"] --> OS["OS in a VM"] --> DEVS["on his devices"]
```

## 4. Release artifacts

```mermaid
flowchart LR
  REPO["repository"] --> IMG["PC image"] & PI["Pi image"] & APK["phone app"]
  IMG & PI & APK --> SIGN["signed + SBOM"] --> PUB["GHCR / Releases"]
```

## 5. A store migration

```mermaid
flowchart LR
  OLD["older file"] --> BAK["backed up .vN.bak"] --> MIG["migrated in code"] --> NEW["written atomically, new schema_version"]
```
