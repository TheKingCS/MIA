#!/usr/bin/env bash
#
# deploy/download_voice_models.sh
# =================================
#
# Fetches the offline STT/TTS models the Voice interface (docs/ROADMAP.md
# milestone 5.3, core/voice_manager.py) needs. Not committed to the repo
# (see .gitignore) — these are large binary model files, same reasoning
# as Reference Library content packs not being committed either.
#
# Downloads into voice_models/ at the repo root, matching the config
# defaults in config/default_config.json (voice.stt_model_path /
# voice.tts_model_path). Safe to re-run — skips files already present.
#
# Usage:
#   bash deploy/download_voice_models.sh

set -euo pipefail

MIA_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="${MIA_DIR}/voice_models"

mkdir -p "${MODELS_DIR}"
cd "${MODELS_DIR}"

VOSK_MODEL_DIR="vosk-model-small-en-us-0.15"
if [ -d "${VOSK_MODEL_DIR}" ]; then
    echo "Vosk STT model already present at voice_models/${VOSK_MODEL_DIR} — skipping."
else
    echo "Downloading Vosk STT model (${VOSK_MODEL_DIR}, ~40MB)..."
    curl -sL -o vosk-model.zip "https://alphacephei.com/vosk/models/${VOSK_MODEL_DIR}.zip"
    unzip -q vosk-model.zip
    rm vosk-model.zip
fi

PIPER_VOICE="en_US-lessac-low"
if [ -f "${PIPER_VOICE}.onnx" ]; then
    echo "Piper TTS voice already present at voice_models/${PIPER_VOICE}.onnx — skipping."
else
    echo "Downloading Piper TTS voice (${PIPER_VOICE}, ~60MB)..."
    curl -sL -o "${PIPER_VOICE}.onnx" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/${PIPER_VOICE}.onnx"
    curl -sL -o "${PIPER_VOICE}.onnx.json" \
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/low/${PIPER_VOICE}.onnx.json"
fi

echo ""
echo "Done. Voice models are in ${MODELS_DIR}"
