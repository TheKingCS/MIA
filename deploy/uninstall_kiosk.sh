#!/usr/bin/env bash
#
# deploy/uninstall_kiosk.sh
# ===========================
#
# Reverses deploy/install_kiosk.sh: stops and removes the systemd user
# service and turns kiosk_mode back off, so you can return to running
# `python main.py` manually in a normal window for development.
#
# Does NOT disable autologin automatically, since you may want that
# regardless of M.I.A. — disable it yourself with:
#   sudo raspi-config nonint do_boot_behaviour B1   (console, no autologin)
#
# Usage:
#   bash deploy/uninstall_kiosk.sh

set -euo pipefail

MIA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${MIA_DIR}/.venv/bin/python"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "Stopping and disabling mia.service..."
systemctl --user stop mia.service 2>/dev/null || true
systemctl --user disable mia.service 2>/dev/null || true
rm -f "${SYSTEMD_USER_DIR}/mia.service"
systemctl --user daemon-reload

if [ -f "${VENV_PYTHON}" ]; then
    echo "Disabling kiosk_mode in config..."
    "${VENV_PYTHON}" - << PYEOF
import sys
sys.path.insert(0, "${MIA_DIR}")
from core.config_manager import ConfigManager
cfg = ConfigManager()
cfg.set("system.kiosk_mode", False)
cfg.save()
print("kiosk_mode disabled.")
PYEOF
fi

echo "Done. Autologin was left as-is — see this script's header comment to disable it manually."
