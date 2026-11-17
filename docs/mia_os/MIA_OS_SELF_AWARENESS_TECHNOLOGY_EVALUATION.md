# MIA OS: self-awareness technology evaluation and decision records (Prompt 09 §21, §23)

*Claude (Opus), 2026-11-17. Planning only. DEC-0220 to 0226 are PROPOSED.*

## 1. Technologies

| Option | For | Against | Recommendation |
|---|---|---|---|
| MIA's own registry, loops, Fix-It Log, lab (exist) | grounded in her code, per person, tested | grown by hand | **Keep and join** |
| Prometheus + Grafana | metrics and dashboards | another stack for one person's machine | **No**: systemd's accounting and her loops suffice (DEC-0195) |
| OpenTelemetry tracing | standard traces | heavy for in-process calls | **Maybe later** for the model node's calls |
| Langfuse (LLM traces) | model call tracing | a server; her turn trace already does it (DEC-0067 chose native first) | **No** |
| Automatic program repair tools | fixes from failures | unproven on her code; would bypass the test-first rule | **No**; the lab with a reproducing test |
| Feature flags | turning capabilities on and off | another state to keep true | **Use her settings and the registry** |

## 2. Decision records

### DEC-0220: one capability truth registry
Context: the prompt's critical priority. Requirements: REQ-SLF-001, 003 to 005, 020. Selected: a derived registry
joining code, tests, runtime and the Fix-It Log, with states including degraded and unverified. Rejected: a
hand-kept capability list (drifts). Reversibility: full (derived).

### DEC-0221: provenance on every self-statement
Requirements: REQ-SLF-002, 006, 007, 011, 021. Selected: verified, inferred, documented, planned, unknown; the
strongest provable label only.

### DEC-0222: health and performance from Linux and her counters
Requirements: REQ-SLF-008, 009. Selected: systemd, the journal, hwmon, SMART, psutil, the turn trace and loops, one
joined view. Rejected: a metrics server.

### DEC-0223: quality by code checks, corrections and fixed sets
Requirements: REQ-SLF-010. Selected: as Prompt 07's framework; a drop opens a finding.

### DEC-0224: investigations end in a reproducing test
Requirements: REQ-SLF-012. Selected: a hypothesis stays derived until a failing test reproduces it.

### DEC-0225: self-development only through the lab; protected files never hers to change
Requirements: REQ-SLF-013 to 017, 019. Selected: the lab as built, Claude's pass merging (DEC-0200), automatic revert,
a daily summary to Zac (Q-76), the protected list extended with grants, the stop, browser safety, action effects and
the inspection itself. Rejected: any second path for code changes.

### DEC-0226: new capabilities only through one path
Requirements: REQ-SLF-018. Selected: gap → proposal → lab → registry with tier, tests, parity, loop and documentation.
