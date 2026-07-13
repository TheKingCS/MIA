"""
modules.files_mod.module
==========================

Files: a real file manager (docs/ROADMAP.md milestone 3.6), replacing
the earlier placeholder. Browses starting from the user's home
directory but can navigate anywhere the OS permits — matching the
project's "browse (USB/SSD/SD/NAS)" vision for this module, not just
M.I.A.'s own data folder.

Built on QFileSystemModel + QTreeView (Qt's own file-browsing widgets)
rather than hand-rolled directory listing — sorting, icons, and live
filesystem-change updates all come for free. modules/files_mod/
file_operations.py covers what QFileSystemModel doesn't: create/
rename/delete (with a strong, typed confirmation for delete — see
gui/delete_confirm_dialog.py — since there is no trash/recycle bin)
and building a text/image preview.

Not yet wired into Global Search (core/search_manager.py) — that's a
natural future enhancement (see docs/ADDING_MODULES.md's "Making your
module searchable" section) deliberately deferred rather than guessed
at now; a filesystem-wide search has real performance/scope questions
(recurse how deep? which drives?) worth designing deliberately rather
than bolting on here.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QDir, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFileSystemModel,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from gui.delete_confirm_dialog import DeleteConfirmDialog
from gui.file_preview_dialog import FilePreviewDialog
from modules.files_mod.file_operations import (
    create_folder,
    delete_item,
    format_size,
    is_image_file,
    is_probably_text_file,
    read_text_preview,
    rename_item,
)
from modules.module_base import ModuleBase


class FilesModule(ModuleBase):
    module_id = "files"
    display_name = "Files"
    description = "Browse and manage local files and data."
    icon = "\U0001F5C2"  # card index dividers

    def __init__(self, context) -> None:
        super().__init__(context)
        self._model: QFileSystemModel | None = None
        self._view: QTreeView | None = None
        self._path_edit: QLineEdit | None = None
        self._status_label: QLabel | None = None
        self._current_path: Path = Path.home()

    def get_widget(self) -> QWidget:
        widget = QWidget()
        outer = QVBoxLayout(widget)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(10)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        outer.addWidget(header)

        nav_row = QHBoxLayout()
        up_button = QPushButton("↑ Up")
        up_button.setObjectName("ModuleButton")
        up_button.clicked.connect(self._on_up_clicked)
        nav_row.addWidget(up_button)

        home_button = QPushButton("\U0001F3E0 Home")
        home_button.setObjectName("ModuleButton")
        home_button.clicked.connect(self._on_home_clicked)
        nav_row.addWidget(home_button)

        self._path_edit = QLineEdit()
        self._path_edit.returnPressed.connect(self._on_path_entered)
        nav_row.addWidget(self._path_edit, stretch=1)
        outer.addLayout(nav_row)

        action_row = QHBoxLayout()
        new_folder_button = QPushButton("\U0001F4C1 New Folder")
        new_folder_button.setObjectName("ModuleButton")
        new_folder_button.clicked.connect(self._on_new_folder_clicked)
        action_row.addWidget(new_folder_button)

        rename_button = QPushButton("✏ Rename")
        rename_button.setObjectName("ModuleButton")
        rename_button.clicked.connect(self._on_rename_clicked)
        action_row.addWidget(rename_button)

        delete_button = QPushButton("\U0001F5D1 Delete")
        delete_button.setObjectName("ModuleButton")
        delete_button.clicked.connect(self._on_delete_clicked)
        action_row.addWidget(delete_button)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Filter this folder…")
        self._search_edit.textChanged.connect(self._on_search_changed)
        action_row.addWidget(self._search_edit, stretch=1)
        outer.addLayout(action_row)

        self._model = QFileSystemModel()
        self._model.setRootPath(QDir.rootPath())
        # QFileSystemModel's default filter includes QDir.Filter.AllDirs,
        # which means "directories ignore name filters" — with it set,
        # setNameFilters() below would only ever narrow files, never
        # folders. Dropping AllDirs makes the search box filter both.
        self._model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)

        self._view = QTreeView()
        self._view.setModel(self._model)
        self._view.setSortingEnabled(True)
        self._view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self._view.setSelectionBehavior(QTreeView.SelectionBehavior.SelectRows)
        self._view.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self._view.doubleClicked.connect(self._on_item_double_clicked)
        header_view = self._view.header()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        outer.addWidget(self._view, stretch=1)

        self._status_label = QLabel("")
        self._status_label.setObjectName("SubtitleLabel")
        self._status_label.setWordWrap(True)
        outer.addWidget(self._status_label)

        self._navigate_to(self._current_path)
        return widget

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def navigate_to_path(self, path: Path) -> None:
        """
        Public entry point for other components to open Files rooted at
        a specific folder — added for Field Kit's "Browse Files" device
        action (docs/ROADMAP.md milestone 11.2), which navigates here
        via the `"files.browse_path_requested"` event
        (gui/main_window.py) rather than importing this module
        directly, per this project's module-isolation rule. Requires
        `get_widget()` to have already run — callers should go through
        `MainWindow.open_module("files")` first, same as any other
        cross-module navigation in this app.
        """
        self._navigate_to(path)

    def _navigate_to(self, path: Path) -> None:
        if not path.is_dir():
            self._set_status(f"Not a folder: {path}")
            return

        self._current_path = path
        self._view.setRootIndex(self._model.index(str(path)))
        self._path_edit.setText(str(path))
        self._search_edit.clear()
        self._model.setNameFilters([])
        self._set_status("")

    def _on_up_clicked(self) -> None:
        self._navigate_to(self._current_path.parent)

    def _on_home_clicked(self) -> None:
        self._navigate_to(Path.home())

    def _on_path_entered(self) -> None:
        candidate = Path(self._path_edit.text()).expanduser()
        if candidate.is_dir():
            self._navigate_to(candidate)
        else:
            self._set_status(f"No such folder: {candidate}")
            self._path_edit.setText(str(self._current_path))

    def _on_search_changed(self, text: str) -> None:
        self._model.setNameFilters([f"*{text}*"] if text else [])
        self._model.setNameFilterDisables(False)

    def _on_item_double_clicked(self, index) -> None:
        path = Path(self._model.filePath(index))
        if self._model.isDir(index):
            self._navigate_to(path)
            return
        self._preview_file(path)

    # ------------------------------------------------------------------
    # Selection helper
    # ------------------------------------------------------------------

    def _selected_path(self) -> Path | None:
        indexes = self._view.selectionModel().selectedRows()
        if not indexes:
            self._set_status("Select an item first.")
            return None
        return Path(self._model.filePath(indexes[0]))

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _on_new_folder_clicked(self) -> None:
        name, ok = QInputDialog.getText(None, "New Folder", "Folder name:")
        if not ok or not name:
            return
        try:
            create_folder(self._current_path, name)
            self._set_status(f"Created folder '{name}'.")
        except (ValueError, FileExistsError, OSError) as exc:
            QMessageBox.warning(None, "Could Not Create Folder", str(exc))

    def _on_rename_clicked(self) -> None:
        path = self._selected_path()
        if path is None:
            return

        new_name, ok = QInputDialog.getText(None, "Rename", "New name:", text=path.name)
        if not ok or not new_name:
            return
        try:
            rename_item(path, new_name)
            self._set_status(f"Renamed '{path.name}' to '{new_name}'.")
        except (ValueError, FileExistsError, OSError) as exc:
            QMessageBox.warning(None, "Could Not Rename", str(exc))

    def _on_delete_clicked(self) -> None:
        path = self._selected_path()
        if path is None:
            return

        dialog = DeleteConfirmDialog(path.name, is_directory=path.is_dir(), parent=None)
        if dialog.exec() != DeleteConfirmDialog.DialogCode.Accepted:
            return

        try:
            delete_item(path)
            self._set_status(f"Deleted '{path.name}'.")
        except OSError as exc:
            QMessageBox.warning(None, "Could Not Delete", str(exc))

    # ------------------------------------------------------------------
    # Preview
    # ------------------------------------------------------------------

    def _preview_file(self, path: Path) -> None:
        if is_image_file(path):
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                dialog = FilePreviewDialog.for_image(path.name, pixmap, parent=None)
                dialog.exec()
                return

        if is_probably_text_file(path):
            try:
                text = read_text_preview(path)
            except OSError as exc:
                QMessageBox.warning(None, "Could Not Open File", str(exc))
                return
            dialog = FilePreviewDialog.for_text(path.name, text, parent=None)
            dialog.exec()
            return

        try:
            stat = path.stat()
            info = f"{path.name}\n\nSize: {format_size(stat.st_size)}\nType: {path.suffix or 'unknown'}"
        except OSError as exc:
            info = f"{path.name}\n\nCould not read file info: {exc}"
        QMessageBox.information(None, "File Info", info)

    def _set_status(self, text: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(text)
