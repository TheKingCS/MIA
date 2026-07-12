"""
modules.knowledge.module
==========================

Knowledge: the Reference Library's UI (docs/ROADMAP.md milestone 4.2),
replacing the earlier placeholder. A pack list (every .zim file
core.reference_library_manager.ReferenceLibraryManager discovers) and,
per pack, a reader screen: an in-pack search box plus a
modules.knowledge.zim_text_browser.ZimTextBrowser showing the article
HTML. All ZIM reading/searching logic lives in
core/reference_library_manager.py (self.context.reference_library);
this module is the Qt-facing wrapper around it, same split as every
other data-backed module (Notes, Toolbox).

List page <-> per-pack reader page navigation follows
modules/toolbox/module.py's QStackedWidget + cache-built-pages pattern
(a "← Back" button rather than a second top-level module), including
the same reasoning: reopening a pack shouldn't rebuild its reader or
lose its scroll position/history.

Registers a Global Search provider in on_load() (docs/ROADMAP.md
milestone 4.3), same action_type="open_module" pattern as
modules/notes/module.py — landing on the pack list rather than the
exact matched article, for the same reason Notes' own docstring gives
(a deep-link would need a new action_type and a gui/main_window.py
branch; not worth it for this milestone). Unlike Notes, this provider
deliberately caps its own result count: gui/search_dialog.py renders
every SearchResult from every provider with no cap of its own, and a
single installed pack can have hundreds of thousands of articles —
without a per-pack and total cap here, one keystroke in Ctrl+K could
try to build hundreds of result rows.

The pack list's "Install Content Pack" button (docs/ROADMAP.md
milestone 4.4) is a thin wrapper around
core.reference_library_manager.ReferenceLibraryManager.
install_pack_from_file — same validate-before-copy shape as
modules/module_browser/module.py's module installer, just without a
worker thread: this codebase's other large-file copies
(core/backup_manager.py's restore) are synchronous too, so a install
click blocking the UI for as long as the copy takes is consistent with
existing behavior, not a new tradeoff.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from core.reference_library_manager import ReferencePack
from core.search_manager import SearchResult
from modules.knowledge.zim_text_browser import ZimTextBrowser
from modules.module_base import ModuleBase

# Per-pack and total caps for the Global Search provider — see the
# module docstring for why these exist at all.
_SEARCH_HITS_PER_PACK = 3
_SEARCH_RESULTS_TOTAL = 15


class KnowledgeModule(ModuleBase):
    module_id = "knowledge"
    display_name = "Knowledge"
    description = "Offline reference material and personal knowledge base."
    icon = "\U0001F4DA"  # books

    def __init__(self, context) -> None:
        super().__init__(context)
        self._stack: Optional[QStackedWidget] = None
        self._list_page: Optional[QWidget] = None
        self._pack_list_layout: Optional[QVBoxLayout] = None
        self._pack_pages: dict[str, QWidget] = {}

    def on_load(self) -> None:
        super().on_load()
        self.context.search.register_provider("knowledge", self._search)

    def _search(self, query: str) -> list[SearchResult]:
        results = []
        for pack in self.context.reference_library.list_packs():
            hits = self.context.reference_library.search(pack.pack_id, query, limit=_SEARCH_HITS_PER_PACK)
            for hit in hits:
                results.append(SearchResult(
                    title=hit.title,
                    description=pack.title,
                    source=self.display_name,
                    action_type="open_module",
                    action_target=self.module_id,
                ))
            if len(results) >= _SEARCH_RESULTS_TOTAL:
                break
        return results[:_SEARCH_RESULTS_TOTAL]

    def get_widget(self) -> QWidget:
        self._stack = QStackedWidget()
        self._list_page = self._build_list_page()
        self._stack.addWidget(self._list_page)
        self._stack.setCurrentWidget(self._list_page)
        return self._stack

    # ------------------------------------------------------------------
    # Pack list page
    # ------------------------------------------------------------------

    def _build_list_page(self) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        header_row.addWidget(header, stretch=1)

        install_button = QPushButton("Install Content Pack")
        install_button.clicked.connect(self._on_install_pack_clicked)
        header_row.addWidget(install_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self._populate_pack_rows)
        header_row.addWidget(refresh_button)
        outer.addLayout(header_row)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        outer.addWidget(subtitle)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        list_container = QWidget()
        self._pack_list_layout = QVBoxLayout(list_container)
        self._pack_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._pack_list_layout.setSpacing(12)

        scroll.setWidget(list_container)
        outer.addWidget(scroll)

        self._populate_pack_rows()
        return page

    def _populate_pack_rows(self) -> None:
        layout = self._pack_list_layout
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        packs = self.context.reference_library.list_packs()
        if not packs:
            root_path = self.context.reference_library.root_path
            empty_label = QLabel(
                f"No reference packs installed yet.\nCopy .zim files into:\n{root_path}"
            )
            empty_label.setObjectName("SubtitleLabel")
            empty_label.setWordWrap(True)
            layout.addWidget(empty_label)
            return

        for pack in packs:
            layout.addWidget(self._build_pack_row(pack))

    def _on_install_pack_clicked(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(None, "Select Content Pack", "", "ZIM files (*.zim)")
        if not file_path:
            return

        result = self.context.reference_library.install_pack_from_file(Path(file_path))

        if result.passed:
            QMessageBox.information(None, "Pack Installed", f"Installed '{result.title}' successfully.")
        else:
            message = "Could not install this pack:\n\n" + "\n".join(f"• {e}" for e in result.errors)
            QMessageBox.warning(None, "Install Failed", message)

        self._populate_pack_rows()

    def _build_pack_row(self, pack: ReferencePack) -> QFrame:
        row = QFrame()
        row.setObjectName("CharacterPanel")  # reuse the dashed-panel style
        layout = QHBoxLayout(row)

        text_layout = QVBoxLayout()
        title = QLabel(pack.title)
        title.setStyleSheet("font-weight: 600;")
        detail_bits = [f"{pack.article_count} articles"]
        if pack.language:
            detail_bits.append(pack.language)
        subtitle_text = pack.description or " • ".join(detail_bits)
        subtitle = QLabel(subtitle_text)
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setWordWrap(True)
        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)
        layout.addLayout(text_layout, stretch=3)

        open_button = QPushButton("Open")
        open_button.setMinimumHeight(40)
        open_button.clicked.connect(lambda checked=False, p=pack: self._open_pack(p))
        layout.addWidget(open_button, stretch=1)

        return row

    def _show_list_page(self) -> None:
        if self._stack is not None and self._list_page is not None:
            self._stack.setCurrentWidget(self._list_page)

    # ------------------------------------------------------------------
    # Per-pack reader page
    # ------------------------------------------------------------------

    def _open_pack(self, pack: ReferencePack) -> None:
        if self._stack is None:
            return

        if pack.pack_id not in self._pack_pages:
            self._pack_pages[pack.pack_id] = self._build_pack_page(pack)
            self._stack.addWidget(self._pack_pages[pack.pack_id])

        self._stack.setCurrentWidget(self._pack_pages[pack.pack_id])

    def _build_pack_page(self, pack: ReferencePack) -> QWidget:
        page = QWidget()
        outer = QVBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        nav_row = QHBoxLayout()
        back_button = QPushButton("← Back to Reference Library")
        back_button.setObjectName("ModuleButton")
        back_button.clicked.connect(self._show_list_page)
        nav_row.addWidget(back_button)

        pack_title = QLabel(pack.title)
        pack_title.setObjectName("SubtitleLabel")
        nav_row.addWidget(pack_title, stretch=1)

        browser = ZimTextBrowser(self.context.reference_library)

        history_back_button = QPushButton("‹")
        history_back_button.setEnabled(False)
        history_back_button.clicked.connect(browser.backward)
        browser.backwardAvailable.connect(history_back_button.setEnabled)
        nav_row.addWidget(history_back_button)

        history_forward_button = QPushButton("›")
        history_forward_button.setEnabled(False)
        history_forward_button.clicked.connect(browser.forward)
        browser.forwardAvailable.connect(history_forward_button.setEnabled)
        nav_row.addWidget(history_forward_button)

        outer.addLayout(nav_row)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(24, 12, 24, 24)
        content_layout.setSpacing(8)

        search_edit = QLineEdit()
        search_edit.setPlaceholderText(f"Search {pack.title}…")
        results_list = QListWidget()
        results_list.setMaximumHeight(140)
        results_list.hide()

        def on_search_text_changed(text: str) -> None:
            query = text.strip()
            if not query:
                results_list.hide()
                results_list.clear()
                return
            hits = self.context.reference_library.search(pack.pack_id, query)
            results_list.clear()
            for hit in hits:
                item = QListWidgetItem(hit.title)
                item.setData(Qt.ItemDataRole.UserRole, hit.path)
                results_list.addItem(item)
            results_list.setVisible(bool(hits))

        def on_result_activated(item: QListWidgetItem) -> None:
            entry_path = item.data(Qt.ItemDataRole.UserRole)
            browser.open_entry(pack.pack_id, entry_path)
            results_list.hide()
            search_edit.clear()

        search_edit.textChanged.connect(on_search_text_changed)
        results_list.itemClicked.connect(on_result_activated)

        content_layout.addWidget(search_edit)
        content_layout.addWidget(results_list)
        content_layout.addWidget(browser, stretch=1)
        outer.addLayout(content_layout, stretch=1)

        main_page = self.context.reference_library.get_main_page(pack.pack_id)
        if main_page is not None:
            browser.open_entry(pack.pack_id, main_page)
        else:
            browser.setHtml("<p>This pack has no readable main page.</p>")

        return page
