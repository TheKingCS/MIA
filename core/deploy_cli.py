"""
MIA Homestead — Deploy CLI
v0.1

The human-facing (or deploy-script-facing) side of core/deploy_manager.py
— see that module's docstring for the full mechanism. Typical flow:

    git pull                                          # get the new code
    python3 core/deploy_cli.py --db mia_homestead.db --start-watch
    # ... restart the service (systemd does this on process exit) ...
    # wait out the validation window; check_deploy_watches() runs
    # automatically from main.py's periodic scan and either confirms
    # good (recording a new last-known-good commit) or auto-rolls-back

First-ever use on a fresh checkout needs one manual call before any
watch can start — there's no known-good commit to roll back to yet:

    python3 core/deploy_cli.py --db mia_homestead.db --mark-good "initial deploy"

Usage:
    python3 core/deploy_cli.py --db mia_homestead.db --mark-good "reason"
    python3 core/deploy_cli.py --db mia_homestead.db --start-watch
    python3 core/deploy_cli.py --db mia_homestead.db --status
"""

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.deploy_manager import DeployManager


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="mia_homestead.db")
    parser.add_argument("--mark-good", metavar="NOTE", nargs="?", const="", help="Mark the current commit as known-good")
    parser.add_argument("--start-watch", action="store_true", help="Start a deploy watch after a fresh deploy")
    parser.add_argument("--window", type=int, default=30, help="Validation window in minutes (with --start-watch)")
    parser.add_argument("--threshold", type=int, default=2, help="Critical alert count that triggers rollback")
    parser.add_argument("--status", action="store_true", help="Show the last known-good commit and any active watch")
    parser.add_argument("--emergency-rollback", action="store_true",
                         help="Unconditionally revert to the last known-good commit — the systemd "
                              "crash-loop trigger (deploy/mia-homestead-rollback.service), not for "
                              "manual use under normal circumstances")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    mgr = DeployManager(conn)

    if args.emergency_rollback:
        target = mgr.emergency_rollback_to_last_known_good()
        if target is None:
            print("No last-known-good commit recorded — nothing to roll back to. Manual investigation required.")
            sys.exit(1)
        print(f"Emergency rollback complete — reverted to {target[:8]}.")
        return

    if args.mark_good is not None:
        deploy_id = mgr.mark_last_known_good(note=args.mark_good or None)
        commit = mgr.get_last_known_good()
        print(f"Deploy #{deploy_id} recorded — {commit[:8] if commit else 'unknown'} is now last known-good.")
        return

    if args.start_watch:
        watch_id = mgr.start_deploy_watch(validation_window_minutes=args.window, critical_alert_threshold=args.threshold)
        print(f"Deploy watch #{watch_id} started — {args.window}min window, rolls back at {args.threshold} critical alert(s).")
        return

    if args.status:
        commit = mgr.get_last_known_good()
        print(f"Last known-good commit: {commit[:8] if commit else '(none recorded yet)'}")
        current = mgr.current_commit()
        print(f"Current commit: {current[:8] if current else '(not a git repo)'}")
        watching = conn.execute(
            "SELECT id, rollback_git_commit, applied_at, validation_window_minutes, critical_alert_threshold "
            "FROM code_update_watches WHERE status = 'watching'"
        ).fetchall()
        if watching:
            for w in watching:
                print(f"  Active watch #{w[0]}: started {w[2]}, {w[3]}min window, "
                      f"rolls back to {w[1][:8]} at {w[4]} critical alert(s)")
        else:
            print("  No active deploy watch.")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
