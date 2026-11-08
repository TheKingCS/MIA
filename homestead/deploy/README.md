# MIA Homestead — Self-Healing Deploy & Rollback

Two layers, working together, implementing the "safe and backed up
updates with... auto rebooting to previous update if system failure"
half of the project's stated vision (2026-08-30). Neither layer alone
covers both failure modes a running system can hit:

1. **App-level deploy watch** (`core/deploy_manager.py`, pure Python) —
   after a deploy, watches for a critical-alert spike and reverts the
   working tree to the last known-good git commit if one appears.
   Catches "the process runs, but the new code makes things worse."
2. **systemd crash-loop safety net** (this directory's two unit files) —
   `Restart=on-failure` + crash-loop detection, triggering an
   unconditional rollback once the process genuinely won't stay up at
   all. Catches what layer 1 structurally cannot: if the process is
   dead, there's no Python running to watch alerts with.

Layer 1 is the same shape as `core/backup_manager.py`'s existing
config-update watch (propose → snapshot → watch for a critical-alert
spike → auto-revert) — applied to code via git instead of config files,
since that module's own `restore_snapshot()` explicitly does not touch
code.

## Setup

```bash
cd mia-homestead
bash deploy/install_service.sh
python3 core/deploy_cli.py --db mia_homestead.db --mark-good "initial deploy"
systemctl --user start mia-homestead.service
```

There's nothing to roll back to until `--mark-good` has been run at
least once — `start_deploy_watch()` refuses to start a watch toward
nothing.

## After every future deploy

```bash
git pull
# ...restart however you restart (systemctl --user restart mia-homestead.service)...
python3 core/deploy_cli.py --db mia_homestead.db --start-watch
```

`check_deploy_watches()` runs automatically from `main.py`'s periodic
scan and resolves the watch on its own — either `confirmed_good`
(records a new last-known-good commit) or `auto_rolled_back` (reverts
and exits the process so systemd brings it back up on the reverted
code).

## Two real bugs found by actually testing this, not by reasoning about it

Both `core/deploy_manager.py`'s git-level logic and the systemd unit
files below were verified against real, disposable test infrastructure
(a scratch git repo for the Python layer; real `systemctl --user`
units under throwaway names for the systemd layer, cleaned up
immediately after each test — never against this repo's own commit
history or unit namespace). That process caught two real design bugs
the initial write-up got wrong:

1. **`OnFailure=` fires on every failed run, not only once
   `StartLimitBurst` is exhausted.** The original design assumed
   `OnFailure=` was itself the crash-loop signal. Confirmed directly:
   two ordinary crashes still eligible for `Restart=on-failure`'s own
   retry each triggered `OnFailure=` too. Fixed with a guard —
   `systemctl --user is-failed <service>` only reports true once the
   unit has actually stopped being auto-restarted — so the rollback
   script no-ops on an ordinary transient blip and only proceeds on a
   genuine, exhausted crash loop.
2. **`ExecStartPost=` runs after ANY successful `ExecStart=`,
   including the guard's early `exit 0` skip.** The first fix's
   reset-failed+restart steps were originally separate
   `ExecStartPost=` lines — which fired even when the guard correctly
   skipped, force-restarting the main service outside
   `Restart=on-failure`/`RestartSec`'s own pacing entirely. Observed
   directly: 13 rollback-service invocations in ~16 seconds, a real
   runaway loop, before the fix. Fixed by folding the guard, the
   rollback, and the restart into one conditional shell command in a
   single `ExecStart=`, so reset-failed+restart only ever runs after
   an actual rollback completed.

Final verification, with the fix applied and the real production unit
files (only the root path substituted): a service that crashes 3 times
(exhausting a 3-burst/300s limit) correctly triggers exactly one
rollback, and — with the rollback simulated to actually fix the
underlying problem — the service settles cleanly into `active
(running)`, no further crashes, no runaway. Confirmed via
`systemctl --user status` and a marker file proving the rollback script
ran exactly once.

## Manual recovery

If an emergency rollback ever fires and you want to understand what
happened:

```bash
python3 core/deploy_cli.py --db mia_homestead.db --status
git log --oneline -5              # see what was reverted
git stash list                     # anything auto-stashed to protect
                                    # uncommitted work during the rollback
```
