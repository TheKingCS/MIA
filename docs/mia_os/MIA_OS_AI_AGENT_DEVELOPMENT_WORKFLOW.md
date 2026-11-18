# MIA OS: how the agents build it (Prompt 16)

*Claude (Opus), 2026-11-18. The engineering rules: Prompt 15 (DEC-0268).*

| Step | Rule |
|---|---|
| Pick | a work package from the board, by stage and the critical path |
| Read | `docs/NEXT_SESSION.md`, the package's documents, the knowledge entries for its files (`dev_knowledge.for_task`) |
| Build | test first where there's a bug; the full suite; docs and maps regenerated |
| Commit | own files only, a scratch worktree, the attribution line, push |
| Review | an unattended batch reviewed end to end by a model that didn't write it |
| Record | knowledge entries; NEXT_SESSION; CURRENT_STATE; WAITING_ON for his steps |
| Gate | the milestone's criteria checked; Zac passes it |
| MIA herself | Night School exercises on the packages' small pieces; her merges on Claude's pass |
| Fable / Opus | each reviews the other's work (DEC-0174) |
