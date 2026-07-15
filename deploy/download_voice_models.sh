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
# 2026-07-15: now fetches every voice in core/voice_catalog.py's
# VOICE_CATALOG (curated multi-voice selection, modules/settings/module.py's
# Voice dropdown), not just the single default. Keep the PIPER_VOICES
# array below in sync with core/voice_catalog.py by hand — this is bash,
# it can't import the Python module directly.
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

# id|hf_path (hf_path has no file extension) — must match
# core/voice_catalog.py's VOICE_CATALOG exactly.
PIPER_VOICES=(
    "en_US-lessac-low|en/en_US/lessac/low/en_US-lessac-low"
    "en_US-amy-low|en/en_US/amy/low/en_US-amy-low"
    "en_US-ryan-medium|en/en_US/ryan/medium/en_US-ryan-medium"
    "en_GB-alan-low|en/en_GB/alan/low/en_GB-alan-low"
    "en_GB-southern_english_female-low|en/en_GB/southern_english_female/low/en_GB-southern_english_female-low"
)

for entry in "${PIPER_VOICES[@]}"; do
    voice_id="${entry%%|*}"
    hf_path="${entry##*|}"
    if [ -f "${voice_id}.onnx" ]; then
        echo "Piper TTS voice already present at voice_models/${voice_id}.onnx — skipping."
    else
        echo "Downloading Piper TTS voice (${voice_id}, ~60MB)..."
        curl -sL -o "${voice_id}.onnx" \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/${hf_path}.onnx"
        curl -sL -o "${voice_id}.onnx.json" \
            "https://huggingface.co/rhasspy/piper-voices/resolve/main/${hf_path}.onnx.json"
    fi
done

echo ""
echo "Done. Voice models are in ${MODELS_DIR}"
