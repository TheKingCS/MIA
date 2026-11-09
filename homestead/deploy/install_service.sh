#!/usr/bin/env bash
#
# deploy/install_service.sh
# ============================
#
# Installs the two systemd --user units that make the control loop
# self-healing per core/deploy_manager.py's module docstring:
#   - mia-homestead.service      the control loop itself, restart-on-
#                                 failure with crash-loop detection
#   - mia-homestead-rollback.service   fires ONLY when the main service
#                                       is genuinely crash-looping (not
#                                       on an ordinary transient
#                                       restart) — reverts to the last
#                                       known-good commit and brings
#                                       the main service back up
#
# What this does NOT do: mark any commit as known-good for you. Run
# this once, manually, before relying on any of this:
#   python3 core/deploy_cli.py --db mia_homestead.db --mark-good "initial deploy"
# There is nothing to roll back to until that's been done at least once.
#
# Safe to re-run — it overwrites its own generated files idempotently,
# same convention as the sibling MIA project's deploy/install_kiosk.sh.
#
# Usage:
#   cd mia-homestead
#   bash deploy/install_service.sh

set -euo pipefail

HOMESTEAD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "== MIA Homestead Service Installer =="
echo "Install directory: ${HOMESTEAD_DIR}"

if [ ! -f "${HOMESTEAD_DIR}/.venv/bin/python" ]; then
    echo "ERROR: No virtual environment found at ${HOMESTEAD_DIR}/.venv"
    echo "Run this first:"
    echo "  cd ${HOMESTEAD_DIR} && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

mkdir -p "${SYSTEMD_USER_DIR}"

for unit in mia-homestead.service mia-homestead-rollback.service; do
    sed -e "s|__MIA_HOMESTEAD_ROOT__|${HOMESTEAD_DIR}|g" \
        "${HOMESTEAD_DIR}/deploy/${unit}" > "${SYSTEMD_USER_DIR}/${unit}"
done

systemctl --user daemon-reload
systemctl --user enable mia-homestead.service

echo ""
echo "Installed. Next steps:"
echo "  1. If you haven't already, mark the current commit as known-good:"
echo "     python3 core/deploy_cli.py --db mia_homestead.db --mark-good \"initial deploy\""
echo "  2. Start the service:"
echo "     systemctl --user start mia-homestead.service"
echo "  3. Check on it:"
echo "     systemctl --user status mia-homestead.service"
echo ""
echo "After any future code deploy (git pull), start a watch so a bad"
echo "deploy auto-rolls-back instead of quietly staying broken:"
echo "  python3 core/deploy_cli.py --db mia_homestead.db --start-watch"
