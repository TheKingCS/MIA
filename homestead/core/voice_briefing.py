"""
MIA Homestead — Spoken Daily Briefing
v0.1

docs/SUSTAINING_FEATURES.md #25. report_generator.py already writes a
real natural-language daily report via the local model
(generate_and_send()); self_preservation.py's beacon is real
hardware-adjacent (light/speaker) but has only ever been driven as an
on/off relay — the two had never been connected before this.

Pipes the report's existing text through Piper (github.com/rhasspy/piper)
— a small, fully offline, locally-run TTS engine, matching this
project's whole local-first assistant stance
(docs/OFFLINE_ASSISTANT_PLAN.md) — rather than a cloud TTS API, which
would reintroduce exactly the network dependency that plan exists to
avoid. Confirmed installable and working in this environment
(pip install piper-tts, a real downloaded voice model, a real
synthesized .wav file — not assumed).

Config-gated the same null-safe way as config/location.yaml and
config/mia_home_sync.yaml: no voice_model_path configured means voice
briefing honestly doesn't run, never guessed. Stops at producing a
real .wav file — actually PLAYING it through a physical speaker needs
the beacon hardware (README punch-list #5), not bought yet. That's the
genuinely remaining hardware-gated step, same pattern as every other
"software done, hardware pending" item in this project.
"""

import logging
import sqlite3
import subprocess
from pathlib import Path

import yaml

from contracts.capability import Describable

logger = logging.getLogger("mia_homestead.voice_briefing")

DEFAULT_OUTPUT_PATH = "viewer/daily_briefing.wav"


class VoiceBriefing(Describable):
    def __init__(self, db_conn: sqlite3.Connection, config_path: str = "config/voice.yaml"):
        self.db = db_conn
        self.config_path = Path(config_path)
        self._config = self._load_config()

    def _load_config(self) -> dict:
        if not self.config_path.exists():
            return {}
        return yaml.safe_load(self.config_path.read_text()) or {}

    @property
    def voice_model_path(self) -> str | None:
        return self._config.get("voice_model_path") or None

    @property
    def output_path(self) -> str:
        return self._config.get("output_path", DEFAULT_OUTPUT_PATH)

    def synthesize_latest_report(self) -> dict:
        """The real integration point: report_generator.py's existing
        text, spoken. Honestly no-ops if no report has ever been
        generated yet — never fabricates something to say."""
        row = self.db.execute(
            "SELECT id, content FROM daily_reports ORDER BY id DESC LIMIT 1"
        ).fetchone()
        if not row:
            return {"synthesized": False, "reason": "no daily report has been generated yet"}
        return self.synthesize_text(row[1], source_report_id=row[0])

    def synthesize_text(self, text: str, source_report_id: int = None) -> dict:
        if self.voice_model_path is None:
            return {
                "synthesized": False,
                "reason": "no voice_model_path configured (config/voice.yaml) — honestly inert, not guessed",
            }
        model_path = Path(self.voice_model_path)
        if not model_path.exists():
            return {"synthesized": False, "reason": f"configured voice_model_path does not exist: {model_path}"}

        output_path = Path(self.output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["python3", "-m", "piper", "-m", str(model_path), "-f", str(output_path)],
                input=text, capture_output=True, text=True, timeout=60,
            )
        except FileNotFoundError:
            return {"synthesized": False, "reason": "piper is not installed in this environment (pip install piper-tts)"}
        except subprocess.TimeoutExpired:
            return {"synthesized": False, "reason": "piper synthesis timed out"}

        if result.returncode != 0 or not output_path.exists():
            return {"synthesized": False, "reason": f"piper failed: {result.stderr.strip()[:500]}"}

        size_bytes = output_path.stat().st_size
        logger.info("Voice briefing synthesized: %s (%d bytes)", output_path, size_bytes)
        return {
            "synthesized": True,
            "output_path": str(output_path),
            "size_bytes": size_bytes,
            "source_report_id": source_report_id,
            "note": (
                "a real audio file was produced — playing it through a physical speaker needs "
                "the beacon hardware (README punch-list #5), not bought yet; this is as far as "
                "software alone can go"
            ),
        }

    # ---------- Describable ----------

    def describe_capabilities(self):
        from contracts.capability import Capability
        return Capability(
            module_id="voice_briefing",
            display_name="Spoken Daily Briefing",
            purpose=(
                "Pipes report_generator.py's existing natural-language daily report through a "
                "local, fully offline TTS engine (Piper) to produce a real spoken .wav file — "
                "closing the gap between the report already being written in prose and the "
                "beacon's speaker hardware never having anything to say."
            ),
            data_produced=["a real synthesized .wav audio file of the latest daily report"],
            actions_possible=["synthesize the latest daily report (or arbitrary text) into a real local audio file"],
            limits_and_safety=(
                "Read-only against the report; writes only an audio file, never touches control "
                "logic. Honestly inert with no voice_model_path configured — never guesses or "
                "fabricates a fallback. Fully offline (Piper runs locally, no cloud TTS API, no "
                "network dependency), matching this project's local-first assistant stance. Does "
                "NOT play the audio through any speaker — that needs the beacon hardware, a "
                "separate, still-unbought punch-list item; this module stops at producing the "
                "file."
            ),
            example_questions=["Can you read me the daily report?"],
            verification_evidence=["scenarios.py::scenario_voice_briefing"],
        )

    def describe_hardware_requirements(self) -> list:
        from contracts.capability import HardwareRequirement
        return [
            HardwareRequirement(
                item="Speaker (self-preservation beacon hardware, README punch-list #5)",
                category="actuator", quantity=1,
                purpose="physically play the synthesized voice briefing at the greenhouse — "
                        "the synthesis itself needs no hardware beyond the Pi's own CPU",
                est_unit_cost=None,
                notes="the software half (real text-to-speech synthesis) is done; only physical "
                      "playback hardware is missing",
            ),
        ]
