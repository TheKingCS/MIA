#!/usr/bin/env bash
#
# deploy/install_kiosk.sh
# =========================
#
# Sets up a Raspberry Pi (running Raspberry Pi OS) to boot directly into
# M.I.A. fullscreen, with automatic restart on crash.
#
# What this script does:
#   1. Enables desktop autologin for the current user (via raspi-config)
#   2. Enables "linger" for the current user, so their systemd --user
#      instance (and thus mia.service) starts at boot even before login
#      completes — needed because autologin still takes a few seconds
#   3. Installs deploy/mia.service into ~/.config/systemd/user/
#   4. Enables and starts the service
#   5. Turns kiosk_mode on in config/config.json
#
# What this script deliberately does NOT do:
#   - It does not install PySide6 or any Python dependencies — run
#     `pip install -r requirements.txt` in your venv first
#   - It does not build a custom minimal Wayland session — it relies on
#     Raspberry Pi OS's default desktop session, with M.I.A. taking over
#     the whole screen. This is a deliberate simplicity trade-off: a
#     fully custom session is more "pure" kiosk but far more fragile to
#     maintain across Raspberry Pi OS updates.
#
# Usage:
#   cd mia
#   bash deploy/install_kiosk.sh
#
# Safe to re-run — it overwrites its own generated files idempotently.

set -euo pipefail

MIA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_PYTHON="${MIA_DIR}/.venv/bin/python"
SERVICE_TEMPLATE="${MIA_DIR}/deploy/mia.service"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"

echo "== M.I.A. Kiosk Installer =="
echo "Install directory: ${MIA_DIR}"

# ---------------------------------------------------------------------
# 1. Sanity checks
# ---------------------------------------------------------------------
if [ ! -f "${VENV_PYTHON}" ]; then
    echo "ERROR: No virtual environment found at ${MIA_DIR}/.venv"
    echo "Run this first:"
    echo "  cd ${MIA_DIR} && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

if ! command -v raspi-config >/dev/null 2>&1; then
    echo "WARNING: raspi-config not found — skipping autologin setup."
    echo "This script is intended for Raspberry Pi OS. Continuing with"
    echo "the systemd service install only; set up autologin manually"
    echo "for your distro if needed."
    SKIP_AUTOLOGIN=1
else
    SKIP_AUTOLOGIN=0
fi

# ---------------------------------------------------------------------
# 2. Enable desktop autologin (B4 = Desktop Autologin in raspi-config)
# ---------------------------------------------------------------------
if [ "${SKIP_AUTOLOGIN}" -eq 0 ]; then
    echo "Enabling desktop autologin..."
    sudo raspi-config nonint do_boot_behaviour B4
fi

# ---------------------------------------------------------------------
# 3. Enable linger so the user's systemd instance runs at boot
# ---------------------------------------------------------------------
echo "Enabling linger for user '$(whoami)'..."
sudo loginctl enable-linger "$(whoami)"

# ---------------------------------------------------------------------
# 4. Generate and install the systemd user service
# ---------------------------------------------------------------------
echo "Installing systemd user service..."
mkdir -p "${SYSTEMD_USER_DIR}"

sed \
    -e "s|__MIA_INSTALL_DIR__|${MIA_DIR}|g" \
    -e "s|__MIA_VENV_PYTHON__|${VENV_PYTHON}|g" \
    "${SERVICE_TEMPLATE}" > "${SYSTEMD_USER_DIR}/mia.service"

systemctl --user daemon-reload
systemctl --user enable mia.service
systemctl --user restart mia.service

# ---------------------------------------------------------------------
# 5. Turn on kiosk_mode + set the Core device profile/theme in config
# ---------------------------------------------------------------------
# device_profile="core" + theme="low_energy" mark this install as the
# resource-constrained Pi 5 + AI HAT+ 2 edition (docs/ROADMAP.md
# milestone 13.1/13.2) — a Home (desktop) install never runs this
# script, so it keeps the defaults (device_profile="core" is still the
# unconditional JSON default in config/default_config.json, but a Home
# install is expected to switch it via Settings, or a future Home
# install script sets "home"/"dark_field" the same way this one sets
# the Core values).
echo "Enabling kiosk_mode + Core device profile in config..."
"${VENV_PYTHON}" - << PYEOF
import sys
sys.path.insert(0, "${MIA_DIR}")
from core.config_manager import ConfigManager
cfg = ConfigManager()
cfg.set("system.kiosk_mode", True)
cfg.set("system.device_profile", "core")
cfg.set("gui.theme", "low_energy")
cfg.save()
print("kiosk_mode enabled, device_profile=core, gui.theme=low_energy.")
PYEOF

echo ""
echo "== Done =="
echo "M.I.A. will now launch fullscreen automatically after each boot."
echo ""
echo "Useful commands:"
echo "  systemctl --user status mia          # check if it's running"
echo "  journalctl --user -u mia -f          # follow live logs"
echo "  systemctl --user restart mia         # restart manually"
echo "  systemctl --user disable mia         # stop launching at boot"
echo ""
echo "To exit kiosk mode on the device itself: Ctrl+Shift+Q"
