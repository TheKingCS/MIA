# MIA OS: self-awareness diagrams (Prompt 09 §20)

*Claude (Opus), 2026-11-17. Mermaid.*

## 1. The registry from its sources

```mermaid
flowchart LR
  CODE["code: manifests, tools, kinds"] --> REG["capability truth registry (derived)"]
  TESTS["tests, bench, golden set"] --> REG
  RUN["runtime: services, models, health"] --> REG
  LOG["Fix-It Log, gaps, corrections"] --> REG
  PLANS["decisions, parity todo"] --> REG
  REG --> ANS["answers about herself"]
  REG --> ROUTE["routing"]
  REG --> NS["Night School's work"]
```

## 2. Capability states

```mermaid
stateDiagram-v2
  planned --> working: built, tested
  working --> malfunctioning: failures
  malfunctioning --> working: fixed, test passes
  working --> degraded: fallback answered
  degraded --> working: primary back
  working --> unverified: no evidence lately
  unverified --> working: test or success
  working --> retired
```

## 3. From failure to fix

```mermaid
flowchart LR
  F["Fix-It Log"] --> E["evidence: trace, logs, code, recent changes"] --> H["hypothesis (derived)"]
  H --> T["failing test"] --> LAB["lab: fix, suite before/after"] --> INS["Claude's inspection"] --> M["merge"]
  M -->|new failure| REV["automatic revert"]
```

## 4. What she may change

```mermaid
flowchart TB
  CH["a proposed change"] --> P{"touches a protected file?"}
  P -->|yes| REF["refused before testing"]
  P -->|no| LAB["the lab"]
```
