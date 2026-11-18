# MIA OS: git and change management (Prompt 15)

*Claude (Opus), 2026-11-18. Planning only.*

| Practice | How |
|---|---|
| One trunk | `master`; sessions commit and push to it |
| Several sessions at once | each stages only its own files; a scratch worktree from HEAD carries one session's change; nobody resets another's work |
| Each commit | tests pass; docs and maps regenerated; a message saying what and why; the attribution line |
| Her lab | worktrees and `lab/*` branches beside MIA; merged by the lab's own rules |
| Pull requests | for work Zac wants to review before it lands, or from other providers (the task board) |
| Tags | each release (`2026.11.1`) |
| History | never rewritten on `master` |

| ID | Requirement | Pri | Tier | Dev | Status | Verify | Trace |
|---|---|---|---|---|---|---|---|
| REQ-DEV-025 | `master`'s history shall never be rewritten, and a commit shall include only its author's own changes. | Must | MVP | All | Exists (practice) | R | DEC-0268 → 15 |
