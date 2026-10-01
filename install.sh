#!/usr/bin/env bash
#
# install.sh: MIA's installer for Linux and the Raspberry Pi
# ===========================================================
#
# One command sets everything up:
#
#     bash install.sh
#
# It asks before each big step, and is safe to run again (it skips what's
# already there, and finishes anything that was interrupted).
#
#   1. System tools (apt): Python, the libraries the window needs, the
#      microphone and speaker library, and Tesseract for reading photos.
#   2. MIA's brain: Ollama (from ollama.com), if it isn't installed.
#   3. MIA's Python packages, in a private .venv folder.
#   4. Voice models, the AI model, an app-menu shortcut, and a setup
#      check (deploy/finish_install.py).
#   5. Optional, Raspberry Pi: start MIA fullscreen at boot (--kiosk).
#
# Options:
#   --yes          don't ask, say yes to every step
#   --kiosk        also set up the Pi to boot into MIA (deploy/install_kiosk.sh)
#   --no-system    skip apt (you installed the system tools yourself)
#   --no-ollama    skip installing Ollama and the model
#   --no-voice     skip downloading the voice models
#   --dry-run      only show what would be done

set -euo pipefail

MIA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${MIA_DIR}"

ASSUME_YES=0
KIOSK=0
DO_SYSTEM=1
DO_OLLAMA=1
DO_VOICE=1
DRY_RUN=0
for arg in "$@"; do
    case "${arg}" in
        --yes|-y) ASSUME_YES=1 ;;
        --kiosk) KIOSK=1 ;;
        --no-system) DO_SYSTEM=0 ;;
        --no-ollama) DO_OLLAMA=0 ;;
        --no-voice) DO_VOICE=0 ;;
        --dry-run) DRY_RUN=1 ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "Unknown option: ${arg} (try --help)"; exit 2 ;;
    esac
done

APT_PACKAGES=(git curl unzip python3 python3-venv python3-pip
              libportaudio2 libegl1 libgl1 libxkbcommon0 libxcb-cursor0 libpulse0
              tesseract-ocr)

step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$1"; }
note() { printf '   %s\n' "$1"; }

ask() {
    # ask "question" -> 0 for yes
    if [ "${ASSUME_YES}" = 1 ] || [ "${DRY_RUN}" = 1 ]; then return 0; fi
    local reply
    read -r -p "   $1 [Y/n] " reply || reply=""
    case "${reply}" in [nN]*) return 1 ;; *) return 0 ;; esac
}

run() {
    # run a command, or just show it with --dry-run
    if [ "${DRY_RUN}" = 1 ]; then printf '   would run: %s\n' "$*"; return 0; fi
    "$@"
}

python_ok() {
    command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'
}

echo "MIA installer"
echo "Folder: ${MIA_DIR}"
[ "${DRY_RUN}" = 1 ] && echo "(dry run: nothing will be changed)"

# ---------------------------------------------------------------- 1. system tools
step "1/5 System tools"
if [ "${DO_SYSTEM}" = 0 ]; then
    note "Skipped (--no-system)."
elif command -v apt-get >/dev/null 2>&1; then
    missing=()
    for pkg in "${APT_PACKAGES[@]}"; do
        dpkg -s "${pkg}" >/dev/null 2>&1 || missing+=("${pkg}")
    done
    if [ "${#missing[@]}" = 0 ]; then
        note "Already installed."
    else
        note "Needed: ${missing[*]}"
        if ask "Install them now? (asks for your password)"; then
            SUDO=""
            [ "$(id -u)" != 0 ] && SUDO="sudo"
            run ${SUDO} apt-get update
            run ${SUDO} apt-get install -y "${missing[@]}"
        else
            note "Skipped. MIA may not open without them."
        fi
    fi
else
    note "This isn't a Debian/Ubuntu/Raspberry Pi OS system (no apt)."
    note "Install with your package manager: Python 3.10+, python3-venv, PortAudio,"
    note "the Qt/X11 libraries (libEGL, libGL, xkbcommon, xcb-cursor) and tesseract."
fi
if ! python_ok && [ "${DRY_RUN}" = 0 ]; then
    echo "MIA needs Python 3.10 or newer (python3). Install it and run this again."
    exit 1
fi

# ---------------------------------------------------------------- 2. ollama
step "2/5 MIA's brain (Ollama)"
if [ "${DO_OLLAMA}" = 0 ]; then
    note "Skipped (--no-ollama)."
elif command -v ollama >/dev/null 2>&1; then
    note "Ollama is installed."
elif ask "Install Ollama from ollama.com? (runs on this computer; nothing leaves it)"; then
    if [ "${DRY_RUN}" = 1 ]; then
        note "would run: curl -fsSL https://ollama.com/install.sh | sh"
    else
        curl -fsSL https://ollama.com/install.sh | sh
    fi
else
    note "Skipped. MIA can't chat until Ollama is installed (ollama.com)."
fi

# ---------------------------------------------------------------- 3. python packages
step "3/5 MIA's Python packages"
if [ ! -x .venv/bin/python ]; then
    run python3 -m venv .venv
fi
run .venv/bin/python -m pip install --upgrade pip --quiet
run .venv/bin/python -m pip install -r requirements.txt
note "Installed into ${MIA_DIR}/.venv"

# ---------------------------------------------------------------- 4. finish
step "4/5 Voice, model, shortcut and setup check"
FINISH_ARGS=()
[ "${DO_VOICE}" = 0 ] && FINISH_ARGS+=(--no-voice)
[ "${DO_OLLAMA}" = 0 ] && FINISH_ARGS+=(--no-model)
if [ "${DRY_RUN}" = 1 ]; then
    note "would run: .venv/bin/python deploy/finish_install.py ${FINISH_ARGS[*]:-}"
else
    # A missing piece is reported, not fatal: the check lists what's left.
    .venv/bin/python deploy/finish_install.py "${FINISH_ARGS[@]}" || true
fi

# ---------------------------------------------------------------- 5. kiosk
step "5/5 Start at boot (Raspberry Pi kiosk)"
if [ "${KIOSK}" = 1 ]; then
    run bash deploy/install_kiosk.sh
else
    note "Not set up. For a Pi that boots straight into MIA: bash install.sh --kiosk"
fi

echo
echo "Done. Start MIA from your app menu (\"MIA\"), or run:"
echo "    cd \"${MIA_DIR}\" && .venv/bin/python main.py"
echo "Run this installer again any time to finish or update anything."
