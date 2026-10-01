"""
modules.module_browser.module
===============================

Backs the "Modules" button on the main menu.

Fully functional: lists every discovered module, lets you enable/
disable each one (persisted, affects the main menu live via the event
bus — no restart needed), rescan for newly-added module folders, and
now install a new module directly from a folder or a .zip file. Every
install goes through core/module_validator.py first — see
docs/MODULE_SPEC.md for the exact compatibility contract being checked.

Note: unlike other modules, this one holds a direct reference to the
real ModuleManager (self.module_manager, set externally by
gui/main_window.py's _wire_module_browser()) rather than just a static
snapshot of module metadata. That's a deliberate, narrow exception —
this module's entire purpose is managing modules.

**Design restyle Phase 5 (2026-09-12)**: adds a second "Architecture"
tab — the handoff's own 1e screen, which its own spec calls "static"
and explicitly says belongs "in the Diagnostics or Modules screen,"
not as its own module. Only the MODULES row is live (rendered from
this module's own self.known_modules, the same real discovery list
the Modules tab already shows) — everything else is fixed structural
information about the codebase's own layering, which doesn't change
at runtime. See _build_architecture_tab()'s own docstring for the one
real correction made to the mockup's own content: it lists "Mobile —
not yet," which was true when the design was authored but is no
longer true after this same session's own Mobile access Phases 1-2.
"""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core import focus_presets
from gui.widgets.blueprint_frame import BlueprintFrame
from gui.widgets.glow import apply_panel_glow
from modules.module_base import ModuleBase


class ModuleBrowserModule(ModuleBase):
    module_id = "module_browser"
    display_name = "Modules"
    description = "View, enable/disable, install, and rescan modules."
    icon = "\U0001F9E9"  # puzzle piece

    def __init__(self, context) -> None:
        super().__init__(context)
        # Populated by gui/main_window.py's _wire_module_browser().
        self.known_modules: list[ModuleBase] = []
        self.module_manager = None
        self._list_layout = None
        self._status_label = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        tabs = QTabWidget()
        tabs.addTab(self._build_modules_tab(), "Modules")
        tabs.addTab(self._build_architecture_tab(), "Architecture")
        outer.addWidget(tabs)

        return widget

    def _build_modules_tab(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(0, 12, 0, 0)
        outer.setSpacing(12)

        header = QLabel("Loaded Modules")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        button_row = QHBoxLayout()

        rescan_button = QPushButton("\U0001F504 Rescan")
        rescan_button.setObjectName("ModuleButton")
        rescan_button.clicked.connect(self._on_rescan_clicked)
        button_row.addWidget(rescan_button)

        add_folder_button = QPushButton("\U0001F4C1 Add Module (Folder)")
        add_folder_button.setObjectName("ModuleButton")
        add_folder_button.clicked.connect(self._on_add_module_folder_clicked)
        button_row.addWidget(add_folder_button)

        add_zip_button = QPushButton("\U0001F5DC Add Module (.zip)")
        add_zip_button.setObjectName("ModuleButton")
        add_zip_button.clicked.connect(self._on_add_module_zip_clicked)
        button_row.addWidget(add_zip_button)

        outer.addLayout(button_row)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        list_container = QWidget()
        self._list_layout = QVBoxLayout(list_container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._list_layout.setSpacing(8)

        scroll.setWidget(list_container)
        outer.addWidget(scroll)

        self._populate_rows()
        return widget

    # ------------------------------------------------------------------
    # Architecture tab — design restyle Phase 5 (2026-09-12)
    # ------------------------------------------------------------------

    def _build_architecture_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 12, 12, 12)
        layout.setSpacing(20)

        layout.addLayout(self._build_architecture_row("INTERFACES", self._build_interfaces_chips()))
        layout.addLayout(self._build_architecture_row("GUI LAYER", self._build_gui_layer_chips()))
        layout.addLayout(self._build_architecture_row("MODULES", self._build_modules_chips()))
        layout.addWidget(self._build_core_block())
        layout.addLayout(self._build_architecture_row("PERSISTENCE", self._build_persistence_chips()))
        layout.addWidget(self._build_architecture_footer())
        layout.addStretch(1)

        scroll.setWidget(container)
        return scroll

    @staticmethod
    def _build_architecture_row(label_text: str, content: QHBoxLayout) -> QHBoxLayout:
        row = QHBoxLayout()
        label = QLabel(label_text)
        label.setObjectName("ArchitectureRowLabel")
        label.setFixedWidth(150)
        label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        row.addWidget(label)
        row.addLayout(content, stretch=1)
        return row

    @staticmethod
    def _chip(text: str) -> QLabel:
        chip = QLabel(text)
        chip.setObjectName("MissionDifficultyTag")
        return chip

    @staticmethod
    def _dashed_chip(text: str) -> QLabel:
        chip = QLabel(text)
        chip.setObjectName("ArchitectureDashedChip")
        return chip

    def _build_interfaces_chips(self) -> QHBoxLayout:
        """Real correction to the design handoff's own mockup content:
        it lists "Mobile — not yet," true when the design was
        authored but no longer true — this same session's own Mobile
        access Phases 1-2 (server/app.py, a PWA, Web Push) shipped a
        real, opt-in mobile interface tier since then. Shown active,
        not dimmed, with an honest "opt-in" caveat rather than quietly
        repeating a now-stale claim. AR/XR stays "concept only" —
        genuinely still true, nothing built."""
        row = QHBoxLayout()
        row.addWidget(self._chip("Pi 5 Kiosk"))
        row.addWidget(self._chip("Desktop"))
        row.addWidget(self._chip("Voice"))
        row.addWidget(self._chip("Mobile (opt-in)"))
        row.addWidget(self._dashed_chip("AR / XR — concept only"))
        row.addStretch(1)
        return row

    def _build_gui_layer_chips(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.addWidget(self._chip("gui/"))
        arrow = QLabel("→ core/ only")
        arrow.setObjectName("SubtitleLabel")
        row.addWidget(arrow)
        row.addWidget(self._chip("theme_manager.py"))
        row.addWidget(self._chip("main_window.py"))
        row.addWidget(self._chip("home_dashboard.py"))
        row.addStretch(1)
        return row

    def _build_modules_chips(self) -> QHBoxLayout:
        """The one live row on this otherwise-static screen — the
        design handoff's own behavior note ("rendered from
        ModuleManager's live discovery list so it can't drift") — reuses
        self.known_modules, the same real list the Modules tab already
        shows. Capped at 10 example chips (this app has dozens of real
        modules; a literal one-chip-per-module row would overflow any
        reasonable window width) — a real, stated simplification, not
        a hidden truncation, via the "+N more" label."""
        row = QHBoxLayout()
        modules = self.known_modules or [self]
        # Capped low enough that the row (plus the "+N more" label and
        # the dashed "drop a folder" chip) actually fits within the
        # design's own 1440px reference width without overflowing —
        # confirmed by re-screenshotting after an earlier attempt at 10
        # chips genuinely didn't fit.
        shown = modules[:6]
        for module in shown:
            row.addWidget(self._chip(module.display_name))
        if len(modules) > len(shown):
            more_label = QLabel(f"+{len(modules) - len(shown)} more")
            more_label.setObjectName("SubtitleLabel")
            row.addWidget(more_label)
        row.addWidget(self._dashed_chip("drop a folder → it appears"))
        row.addStretch(1)
        return row

    def _build_core_block(self) -> QFrame:
        card = BlueprintFrame(accent=True)
        card.setObjectName("DashboardCard")
        apply_panel_glow(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QLabel("\U0001F9CA  AppContext — the one shared object")
        title.setObjectName("SkillCardTitle")
        layout.addWidget(title)

        # The real core/app_context.py fields every module/GUI screen
        # is actually handed — not an illustrative subset invented for
        # this screen.
        services = ["config", "events", "profiles", "notifications", "search", "skills", "data_logger", "calendar"]
        grid = QGridLayout()
        grid.setSpacing(8)
        for index, name in enumerate(services):
            grid.addWidget(self._chip(name), index // 4, index % 4)
        layout.addLayout(grid)

        cells_row = QHBoxLayout()
        for label_text, filename in [
            ("Gamification", "core/gamification.py"),
            ("Leveling", "core/leveling.py"),
            ("Achievements", "core/achievements.py"),
        ]:
            cell = QFrame()
            cell.setObjectName("DashboardCard")
            cell_layout = QVBoxLayout(cell)
            cell_title = QLabel(label_text)
            cell_title.setObjectName("SkillCardTitle")
            cell_layout.addWidget(cell_title)
            cell_file = QLabel(filename)
            cell_file.setObjectName("SkillCardPrereq")
            cell_layout.addWidget(cell_file)
            cells_row.addWidget(cell)
        layout.addLayout(cells_row)

        return card

    def _build_persistence_chips(self) -> QHBoxLayout:
        row = QHBoxLayout()
        # Six representative data/*.json files (real filenames from
        # their owning managers — core/config_manager.py,
        # core/mission_manager.py, core/skill_manager.py x2,
        # core/notification_manager.py, core/data_logger_manager.py),
        # not literally every persisted file this app has (there are
        # many more) — matches the design's own "six mono filename
        # chips," picked to represent the M.I.A. CORE services above.
        files = [
            "config.json", "missions.json", "skill_definitions.json",
            "skill_progress.json", "notifications.json", "data_logger_readings.json",
        ]
        for name in files:
            row.addWidget(self._chip(name))
        row.addStretch(1)
        return row

    def _build_architecture_footer(self) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        rule = QFrame()
        rule.setObjectName("HairlineRule")
        layout.addWidget(rule)

        row = QHBoxLayout()
        row.addWidget(self._chip("ORGANIZATION"))
        row.addWidget(self._chip("AUTOMATION"))
        row.addWidget(self._chip("GAMIFICATION"))
        row.addWidget(self._dashed_chip("XR / AR — LATER"))
        row.addStretch(1)
        rule_text = QLabel("core/ never imports gui/ or modules/")
        rule_text.setObjectName("SkillCardPrereq")
        row.addWidget(rule_text)
        layout.addLayout(row)

        return container

    # ------------------------------------------------------------------
    # Row list
    # ------------------------------------------------------------------

    def _populate_rows(self) -> None:
        if self._list_layout is None:
            return
        # hide()+setParent(None) before deleteLater() — deleteLater()
        # alone doesn't remove a widget from the screen immediately, a
        # real ghosting bug found via an actual screenshot (see
        # modules/toolbox/tools/lite_captures_tool.py) and fixed across
        # this codebase's other actively-re-triggered refresh methods
        # the same day.
        while self._list_layout.count():
            item = self._list_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()

        modules_to_show = self.known_modules or [self]
        for module in modules_to_show:
            self._list_layout.addWidget(self._build_row(module))

    def _build_row(self, module: ModuleBase) -> QFrame:
        is_enabled = True if self.module_manager is None else self.module_manager.is_enabled(module.module_id)
        is_locked = module.module_id == "module_browser"

        row = QFrame()
        border_color = "#232b34" if is_enabled else "#5a3a3a"
        row.setStyleSheet(
            f"QFrame {{ background-color: #161b22; border: 1px solid {border_color}; border-radius: 8px; }}"
        )
        outer = QHBoxLayout(row)

        text_layout = QVBoxLayout()
        status_suffix = "" if is_enabled else "  (disabled)"
        title = QLabel(f"{module.icon}  {module.display_name}  (v{module.version}){status_suffix}")
        title.setStyleSheet("font-weight: 600;")
        subtitle = QLabel(f"id: {module.module_id} \u2014 {module.description}")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        outer.addLayout(text_layout, stretch=3)

        # Each person's own Apps screen (core/focus_presets.py): show or
        # tuck away without disabling it for everyone.
        if is_enabled and module.module_id not in focus_presets.ALWAYS_VISIBLE:
            tucked = module.module_id in focus_presets.current(self.context)[2]
            mine_button = QPushButton("Show on my Apps" if tucked else "Hide from my Apps")
            mine_button.setMinimumHeight(40)
            mine_button.setToolTip("Only for you. It still opens from here, search and the Assistant.")
            mine_button.clicked.connect(
                lambda checked=False, mid=module.module_id, t=tucked: self._on_mine_clicked(mid, t)
            )
            outer.addWidget(mine_button, stretch=1)
            if tucked:
                title.setText(title.text() + "  (hidden from your Apps)")

        toggle_button = QPushButton("Disable" if is_enabled else "Enable")
        toggle_button.setMinimumHeight(40)
        toggle_button.setEnabled(not is_locked)
        toggle_button.setToolTip("The Modules screen can't be disabled." if is_locked else "")
        toggle_button.clicked.connect(
            lambda checked=False, mid=module.module_id, en=is_enabled: self._on_toggle_clicked(mid, en)
        )
        outer.addWidget(toggle_button, stretch=1)

        return row

    def _on_mine_clicked(self, module_id: str, currently_tucked: bool) -> None:
        focus_presets.set_app_visible(self.context, module_id, currently_tucked)
        self._populate_rows()

    def _on_toggle_clicked(self, module_id: str, currently_enabled: bool) -> None:
        if self.module_manager is None:
            return
        success = self.module_manager.set_enabled(module_id, not currently_enabled)
        self._status_label.setText("" if success else "The Modules screen can't be disabled.")
        self._populate_rows()

    def _on_rescan_clicked(self) -> None:
        if self.module_manager is None:
            return
        new_count = self.module_manager.rescan()
        self.known_modules = self.module_manager.all()
        self._status_label.setText(
            f"Found {new_count} new module(s)." if new_count else "No new modules found."
        )
        self._populate_rows()

    # ------------------------------------------------------------------
    # Installing new modules
    # ------------------------------------------------------------------

    def _on_add_module_folder_clicked(self) -> None:
        if self.module_manager is None:
            return
        folder = QFileDialog.getExistingDirectory(None, "Select Module Folder")
        if not folder:
            return
        self._install_and_report(Path(folder))

    def _on_add_module_zip_clicked(self) -> None:
        if self.module_manager is None:
            return
        zip_path, _ = QFileDialog.getOpenFileName(None, "Select Module .zip", "", "Zip files (*.zip)")
        if not zip_path:
            return

        try:
            extract_dir = Path(tempfile.mkdtemp(prefix="mia_module_install_"))
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except Exception as exc:
            QMessageBox.warning(None, "Install Failed", f"Could not read the zip file: {exc}")
            return

        source_dir = self._resolve_module_source_dir(extract_dir)
        self._install_and_report(source_dir)

    @staticmethod
    def _resolve_module_source_dir(extracted_dir: Path) -> Path:
        """
        Zips of a module folder often contain the folder itself as a
        single top-level entry rather than its contents directly at the
        zip root. If module.py isn't at the root, but there's exactly
        one subfolder that has it, use that subfolder instead.
        """
        if (extracted_dir / "module.py").exists():
            return extracted_dir
        subdirs = [p for p in extracted_dir.iterdir() if p.is_dir()]
        if len(subdirs) == 1 and (subdirs[0] / "module.py").exists():
            return subdirs[0]
        return extracted_dir  # let the validator produce a clear error

    def _install_and_report(self, source_path: Path) -> None:
        result = self.module_manager.install_module_from_folder(source_path)

        if result.passed:
            message = f"Installed '{result.display_name}' successfully."
            if result.warnings:
                message += "\n\nWarnings:\n" + "\n".join(f"\u2022 {w}" for w in result.warnings)
            QMessageBox.information(None, "Module Installed", message)
            self.known_modules = self.module_manager.all()
            self._status_label.setText(f"Installed '{result.display_name}'.")
        else:
            message = "Could not install this module:\n\n" + "\n".join(f"\u2022 {e}" for e in result.errors)
            QMessageBox.warning(None, "Install Failed", message)
            self._status_label.setText("Install failed — see docs/MODULE_SPEC.md for requirements.")

        self._populate_rows()
