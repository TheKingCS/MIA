# MIA OS: self-inspection and root cause (Prompt 09 §12; DEC-0224)

*Claude (Opus), 2026-11-17. Planning only.*

## 1. From a failure to a fix

```
Fix-It Log entry (grouped, ranked) ──▶ evidence gathered: the trace, the logs, the code involved, recent changes
   ──▶ hypothesis (derived) ──▶ a test that fails now and would pass when fixed ──▶ the lab
```

**A root cause is a hypothesis until a failing test reproduces it** (DEC-0224). Night School's exercises already
require a test that fails first; the same rule applies to every fix she proposes.

| Step | Who | Exists |
|---|---|---|
| Grouping and ranking failures | `core/failure_log.py` | yes |
| Gathering evidence | code: the turn trace, the journal, `git log` of the files | partial |
| A hypothesis | her teacher (Claude, read-only) or her model, marked derived | partial (Night School) |
| The reproducing test | the lab | yes (exercises) |
| The fix | the lab, its suite | yes |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-SLF-012 | A fix MIA proposes for herself shall come with a test that fails before the fix and passes after. | Must | R1 | PC | Exists (Night School exercises) | T | DEC-0224 → 09 |
