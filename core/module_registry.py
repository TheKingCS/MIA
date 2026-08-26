"""
MIA Homestead — Module Registry
v0.1

Central registry that discovers, loads, and runs all active modules
(aquaponics cells, power monitors, future add-ons like poultry or
irrigation zones) without the core loop needing to know about any
specific module's implementation.

Adding a new subsystem later = write a class implementing
MiaHomesteadModule, add one entry to config/modules.yaml. Nothing
else in the codebase changes. This is the mechanism that makes the
"modular, add onto later" requirement real rather than aspirational.
"""

import importlib
import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path

import yaml

from contracts.mia_homestead_contract import MiaHomesteadModule

logger = logging.getLogger("mia_homestead.registry")


@dataclass
class ModuleConfig:
    module_id: str
    enabled: bool
    class_path: str          # e.g. "modules.aquaponics_cell.AquaponicsCell"
    cell_id: int
    params: dict


class ModuleRegistry:
    """
    Loads module definitions from a YAML config, instantiates each
    enabled module, and runs their control cycles in sequence.

    A module that fails to load or crashes during a cycle does NOT
    take down the others — isolation between modules is a safety
    property, not just a nicety (a bug in the poultry module someday
    should never be able to stop the aquaponics dosing loop).
    """

    def __init__(self, config_path: str, db_path: str, notifier=None):
        self.config_path = Path(config_path)
        self.db_conn = sqlite3.connect(db_path)
        self.notifier = notifier
        self.modules: dict[str, MiaHomesteadModule] = {}

    def load(self) -> None:
        raw = yaml.safe_load(self.config_path.read_text())
        for entry in raw.get("modules", []):
            cfg = ModuleConfig(
                module_id=entry["id"],
                enabled=entry.get("enabled", True),
                class_path=entry["class"],
                cell_id=entry["cell_id"],
                params=entry.get("params", {}),
            )
            if not cfg.enabled:
                logger.info("Skipping disabled module: %s", cfg.module_id)
                continue
            try:
                self._instantiate(cfg)
            except Exception:
                logger.exception(
                    "Failed to load module %s — continuing without it. "
                    "Other modules are unaffected.", cfg.module_id
                )

    def _instantiate(self, cfg: ModuleConfig) -> None:
        module_path, class_name = cfg.class_path.rsplit(".", 1)
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        instance = cls(
            module_id=cfg.module_id,
            cell_id=cfg.cell_id,
            db_conn=self.db_conn,
            notifier=self.notifier,
            **cfg.params,
        )
        self.modules[cfg.module_id] = instance
        logger.info("Loaded module: %s (%s)", cfg.module_id, cfg.class_path)

    def run_all_cycles(self) -> dict[str, list]:
        """
        Runs one control cycle per loaded module. Returns commands per
        module_id. A single module raising does not stop the others —
        it's logged and alerted, then skipped for this cycle.
        """
        results = {}
        for module_id, module in self.modules.items():
            try:
                results[module_id] = module.run_cycle()
            except Exception:
                logger.exception(
                    "Module %s raised during run_cycle — skipping this "
                    "cycle for this module only.", module_id
                )
                results[module_id] = []
        return results

    def reload(self) -> None:
        """Hot-reload config without restarting the whole node — lets you
        add/disable a module without interrupting other running modules."""
        self.modules.clear()
        self.load()
