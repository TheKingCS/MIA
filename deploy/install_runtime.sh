#!/usr/bin/env bash
# deploy/install_runtime.sh
#
# Installs the MIA Runtime (MIA with no window, python -m core.runtime) as a
# systemd user service on Linux: MIA OS on the PC, Raspberry Pi OS on the
# Pi (DEC-0155, DEC-0168). Safe to run again: it rewrites the unit from
# deploy/mia-runtime.service and restarts it.
#
# Run it from anywhere, as the person MIA is for (never with sudo):
#     bash deploy/install_runtime.sh
#
# What it does:
#   1. finds this checkout and its virtual environment (.venv);
#   2. writes ~/.config/systemd/user/mia-runtime.service with those paths;
#   3. turns on lingering, so MIA keeps running with nobody signed in at
#      the screen (loginctl may ask for your password);
#   4. enables and starts the service.
#
# It doesn't install Python packages: do that first (see CLAUDE.md,
# "Commands"). It refuses to run while the kiosk window service (mia.service)
# is enabled, because only one MIA may use a data folder.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${MIA_DIR}/.venv/bin/python"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT="${UNIT_DIR}/mia-runtime.service"

if [ "$(id -u)" -eq 0 ]; then
    echo "Run this as yourself, not root: MIA runs as the person she's for." >&2
    exit 1
fi
if [ ! -x "${VENV_PYTHON}" ]; then
    echo "No virtual environment at ${MIA_DIR}/.venv. Create it first:" >&2
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi
if ! "${VENV_PYTHON}" -c "import core.runtime" 2>/dev/null; then
    echo "MIA's runtime doesn't import with ${VENV_PYTHON}. Install the requirements first." >&2
    (cd "${MIA_DIR}" && "${VENV_PYTHON}" -c "import core.runtime") || true
    exit 1
fi
if systemctl --user is-enabled mia.service >/dev/null 2>&1; then
    echo "The kiosk window service (mia.service) is enabled. Only one MIA may use this data folder." >&2
    echo "Turn it off first:  systemctl --user disable --now mia.service" >&2
    exit 1
fi

mkdir -p "${UNIT_DIR}"
sed \
    -e "s|__MIA_INSTALL_DIR__|${MIA_DIR}|g" \
    -e "s|__MIA_VENV_PYTHON__|${VENV_PYTHON}|g" \
    "${SCRIPT_DIR}/mia-runtime.service" > "${UNIT}"

# Keep running with nobody signed in at the screen (a headless Pi).
if command -v loginctl >/dev/null 2>&1; then
    loginctl enable-linger "$(id -un)" || echo "Couldn't turn on lingering; MIA will stop when you sign out."
fi

systemctl --user daemon-reload
systemctl --user enable mia-runtime.service
systemctl --user restart mia-runtime.service

echo
echo "The MIA Runtime is installed."
echo "  systemctl --user status mia-runtime      # is she running"
echo "  journalctl --user -u mia-runtime -f      # her log"
echo "  systemctl --user restart mia-runtime     # after updating the code"
echo "  systemctl --user disable --now mia-runtime   # stop, and don't start at sign-in"
