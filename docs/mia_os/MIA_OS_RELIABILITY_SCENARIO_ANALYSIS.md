# MIA OS: reliability scenarios (Prompt 14)

*Claude (Opus), 2026-11-18.*

| Scenario | What happens | He sees | Lost |
|---|---|---|---|
| Power cut mid-day | atomic writes hold; on power-up, boot, login, MIA resumes; a run marked interrupted | "I was interrupted; resume the greenhouse checklist?" | nothing |
| The runtime crashes in a loop | systemd restarts it three times, then stops; Plasma and his apps work | "MIA couldn't start: here's what failed" (Diagnostics) | nothing |
| A night update breaks MIA's start | greenboot's checks fail; the previous deployment boots | the rollback message | nothing |
| Ollama won't start | screens and code answers work; self-repair tries; told | "Answers in words are off: the model server won't start" | words only |
| The disk fills | homeostasis eases off; snapshots and caches pruned | a warning with what's using space | nothing |
| A store file damaged | that store empty, the file aside, restore offered from `.prev`, a snapshot or backup | "Your recipes file was damaged; I kept it aside. Restore last night's?" | at most since the last good copy |
| The disk dies | a new disk; install; restore the off-PC backup; the recovery key | — | at most a day; none if the phone synced |
| A Windows update restarts the PC overnight (today) | Night School stops; resumes next night | — | that night's lessons |
| The household display loses power | it boots straight back to its screen | — | nothing |
| Her self-change breaks something subtle | the loops notice; the daily summary; his Undo | the summary | nothing |
