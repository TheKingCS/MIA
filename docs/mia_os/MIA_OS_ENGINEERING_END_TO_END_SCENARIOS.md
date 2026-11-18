# MIA OS: engineering scenarios (Prompt 15)

*Claude (Opus), 2026-11-18.*

| Scenario | Path | Safeguards |
|---|---|---|
| Claude fixes a bug at night | test first, the fix, the suite, docs regenerated, a scratch worktree with only its files, commit, push, CI | the suite; staged own files only; the independent review of the batch |
| MIA fixes herself | Night School keeps an exercise; Claude's pass; the lab merges; the daily summary | protected list; suite before and after; revert; Undo |
| A dependency has a vulnerability | the weekly OSV check flags it; a task; bumped and tested | the suite; the lock's hashes |
| A new model comes out | benched on the three sets on his PC; replaces only if no worse; specialists after Claude's pass | the sets; the old model kept |
| A Fedora release | `next` image on the new base; VM boot; the suite inside; promoted after his OK | rollback on his machines |
| A store changes shape | a migration with `schema_version`, backup, fixtures of every older version | tests; additive by default |
| Two sessions edit the same docs | each stages only its own hunks; worktrees; nobody resets another's file | the commit routine; the classifier blocks broad restores |
| The PC is gone | the repository rebuilds MIA; his backup restores his data | `docs/REBUILD.md`; the off-PC backup |
| A release breaks his PC at night | greenboot rolls back; `stable` moved back | DEC-0257 |
