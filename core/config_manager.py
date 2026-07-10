"""
core.config_manager
====================

Handles reading, writing, and defaulting M.I.A.'s configuration.

Configuration lives in config/config.json (user-specific, gitignored) and
is seeded from config/default_config.json (checked into version control,
never overwritten). This split means:

    - New installs always have sane defaults, even if config.json is missing.
    - Upgrading M.I.A. can add new default keys without clobbering a user's
      existing settings (see `_merge_defaults`).
    - config.json can be safely deleted by the user to "factory reset".

Any part of the system that needs a setting should go through
ConfigManager rather than reading config/config.json directly, so that
defaulting, validation, and save behavior stay in one place.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.logger import get_logger

log = get_logger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
_CONFIG_FILE = _CONFIG_DIR / "config.json"
_DEFAULT_CONFIG_FILE = _CONFIG_DIR / "default_config.json"


class ConfigManager:
    """
    Loads, holds, and persists M.I.A.'s configuration.

    The config is a plain nested dict. For v0.1 this is intentionally
    simple (no schema library) since the config surface is still small.
    If/when the config grows complex (many modules with their own
    settings), consider introducing per-module config namespaces under
    a "modules" key rather than a validation framework — see
    docs/ARCHITECTURE.md for the reasoning.
    """

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self.load()

    # ------------------------------------------------------------------
    # Loading / saving
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load config.json, merging in any missing default keys."""
        defaults = self._read_json(_DEFAULT_CONFIG_FILE, required=True)

        if _CONFIG_FILE.exists():
            user_config = self._read_json(_CONFIG_FILE, required=False)
        else:
            log.info("No config.json found — will be created on first save.")
            user_config = {}

        self._data = self._merge_defaults(defaults, user_config)

    def save(self) -> None:
        """Persist the current in-memory config to config/config.json."""
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with _CONFIG_FILE.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=4, sort_keys=True)
        log.info("Configuration saved to %s", _CONFIG_FILE)

    @staticmethod
    def _read_json(path: Path, required: bool) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            if required:
                log.error("Required config file missing: %s", path)
                raise
            return {}
        except json.JSONDecodeError as exc:
            log.error("Malformed JSON in %s: %s", path, exc)
            if required:
                raise
            return {}

    @staticmethod
    def _merge_defaults(defaults: dict, user: dict) -> dict:
        """Recursively fill in missing keys from `defaults` into `user`."""
        merged = dict(defaults)
        for key, value in user.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ConfigManager._merge_defaults(merged[key], value)
            else:
                merged[key] = value
        return merged

    # ------------------------------------------------------------------
    # Access
    # ------------------------------------------------------------------

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get a config value using dot notation, e.g. get("user.name").
        Returns `default` if the path doesn't exist.
        """
        node: Any = self._data
        for part in key_path.split("."):
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                return default
        return node

    def set(self, key_path: str, value: Any) -> None:
        """
        Set a config value using dot notation, e.g. set("user.name", "Alex").
        Does not save automatically — call save() when ready to persist.
        """
        parts = key_path.split(".")
        node = self._data
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = value

    @property
    def is_first_run(self) -> bool:
        return not self.get("system.setup_complete", False)

    def mark_setup_complete(self) -> None:
        self.set("system.setup_complete", True)
        self.save()
