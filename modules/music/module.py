"""
modules.music.module
======================

Music — replaces the pure placeholder that stood here since this
module was first discovered by ModuleManager. Real local audio library
scanning + playlists + real playback (core/music_manager.py,
AppContext.music) — see that module's docstring for why the historical
"blocked on missing libpulse" documentation no longer applies.

Two tabs (Library / Playlists) plus a transport bar docked below them,
persistent across both tabs and across navigating away entirely —
gui/main_window.py caches this widget forever once built and never
tears it down on navigate-away, so the transport bar's QTimer keeps
reflecting real playback state (and music keeps playing) even while
the user is on a different screen. Same QTabWidget-multi-feature
shape as modules/power/module.py/modules/budget/module.py; the
transport bar's slider drag-guard (`isSliderDown()`) is the exact
pattern gui/home_dashboard.py's Volume card already established.

format_duration()/format_track_row()/format_now_playing_line()/
format_scan_result() are free functions (not methods), same
pure-formatting-logic shape as every other module in this codebase —
testable without Qt, see tests/test_music_module.py.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.music_manager import NowPlaying, ScanResult, Track
from gui.add_edit_playlist_dialog import AddEditPlaylistDialog
from gui.list_widget_helpers import add_empty_state_item, selected_item_data
from modules.module_base import ModuleBase

_TRANSPORT_REFRESH_MS = 500


def format_duration(seconds: float) -> str:
    """Pure formatting logic — testable without Qt (see tests/test_music_module.py)."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def format_track_row(track: Track) -> str:
    """Pure formatting logic — testable without Qt."""
    artist_part = f" — {track.artist}" if track.artist else ""
    album_part = f" ({track.album})" if track.album else ""
    return f"{track.title}{artist_part}{album_part}   {format_duration(track.duration_seconds)}"


def format_now_playing_line(now_playing: Optional[NowPlaying]) -> str:
    """Pure formatting logic — testable without Qt."""
    if now_playing is None:
        return "Nothing is currently playing."
    state = "▶" if now_playing.is_playing else "⏸"
    artist_part = f" — {now_playing.artist}" if now_playing.artist else ""
    position = format_duration(now_playing.position_seconds)
    duration = format_duration(now_playing.duration_seconds)
    return f"{state} {now_playing.title}{artist_part}   {position} / {duration}"


def format_scan_result(result: ScanResult) -> str:
    """Pure formatting logic — testable without Qt."""
    if result.root_missing:
        return "Could not scan — the library folder isn't currently accessible."
    return f"Scan complete: {result.added} added, {result.updated} updated, {result.removed} removed."


class MusicModule(ModuleBase):
    module_id = "music"
    display_name = "Music"
    description = "Local audio library, playlists, and playback."
    icon = "\U0001F3B5"  # musical note

    def __init__(self, context) -> None:
        super().__init__(context)
        self._library_list: Optional[QListWidget] = None
        self._search_edit: Optional[QLineEdit] = None
        self._playlist_list: Optional[QListWidget] = None
        self._playlist_tracks_list: Optional[QListWidget] = None

        self._play_pause_button: Optional[QPushButton] = None
        self._seek_slider: Optional[QSlider] = None
        self._volume_slider: Optional[QSlider] = None
        self._time_label: Optional[QLabel] = None
        self._transport_timer: Optional[QTimer] = None

    def get_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        header = QLabel(f"{self.icon}  {self.display_name}")
        header.setObjectName("TitleLabel")
        layout.addWidget(header)

        subtitle = QLabel(self.description)
        subtitle.setObjectName("SubtitleLabel")
        layout.addWidget(subtitle)

        tabs = QTabWidget()
        tabs.addTab(self._build_library_tab(), "Library")
        tabs.addTab(self._build_playlists_tab(), "Playlists")
        layout.addWidget(tabs, stretch=1)

        layout.addWidget(self._build_transport_bar())

        self._transport_timer = QTimer(widget)
        self._transport_timer.timeout.connect(self._refresh_transport)
        self._transport_timer.start(_TRANSPORT_REFRESH_MS)
        self._refresh_transport()

        return widget

    # ------------------------------------------------------------------
    # Library tab
    # ------------------------------------------------------------------

    def _build_library_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search title, artist, or album…")
        self._search_edit.textChanged.connect(lambda _text: self._refresh_library_list())
        layout.addWidget(self._search_edit)

        self._library_list = QListWidget()
        layout.addWidget(self._library_list, stretch=1)

        button_row = QHBoxLayout()
        scan_button = QPushButton("Scan Library")
        scan_button.clicked.connect(self._on_scan_library)
        button_row.addWidget(scan_button)

        play_button = QPushButton("Play")
        play_button.clicked.connect(self._on_play_selected_track)
        button_row.addWidget(play_button)

        add_to_playlist_button = QPushButton("Add to Playlist…")
        add_to_playlist_button.clicked.connect(self._on_add_selected_track_to_playlist)
        button_row.addWidget(add_to_playlist_button)
        layout.addLayout(button_row)

        self._refresh_library_list()
        return tab

    def _refresh_library_list(self) -> None:
        self._library_list.clear()
        query = self._search_edit.text() if self._search_edit is not None else ""
        tracks = self.context.music.search_tracks(query)
        for track in tracks:
            item = QListWidgetItem(format_track_row(track))
            item.setData(Qt.ItemDataRole.UserRole, track.track_id)
            self._library_list.addItem(item)
        if self._library_list.count() == 0:
            if query:
                add_empty_state_item(self._library_list, "No tracks match your search.")
            else:
                add_empty_state_item(self._library_list, "No tracks in your library yet — click Scan Library to get started.")

    def _selected_library_track_id(self) -> Optional[str]:
        return selected_item_data(self._library_list)

    def _on_scan_library(self) -> None:
        result = self.context.music.scan_library()
        self._refresh_library_list()
        QMessageBox.information(None, "Library Scan", format_scan_result(result))

    def _on_play_selected_track(self) -> None:
        track_id = self._selected_library_track_id()
        if track_id is None:
            QMessageBox.information(None, "No Track Selected", "Select a track to play.")
            return
        self.context.music.play_track(track_id)
        self._refresh_transport()

    def _on_add_selected_track_to_playlist(self) -> None:
        track_id = self._selected_library_track_id()
        if track_id is None:
            QMessageBox.information(None, "No Track Selected", "Select a track to add to a playlist.")
            return

        menu = QMenu()
        for playlist in self.context.music.all_playlists():
            action = menu.addAction(playlist.name)
            action.triggered.connect(lambda _checked=False, pid=playlist.playlist_id: self._add_track_to_playlist(track_id, pid))
        menu.addSeparator()
        new_action = menu.addAction("New Playlist…")
        new_action.triggered.connect(lambda: self._on_new_playlist_with_track(track_id))
        menu.exec(self._library_list.mapToGlobal(self._library_list.rect().center()))

    def _add_track_to_playlist(self, track_id: str, playlist_id: str) -> None:
        self.context.music.add_track_to_playlist(playlist_id, track_id)
        self._refresh_playlist_list()

    def _on_new_playlist_with_track(self, track_id: str) -> None:
        dialog = AddEditPlaylistDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        playlist = self.context.music.create_playlist(dialog.entered_name)
        self.context.music.add_track_to_playlist(playlist.playlist_id, track_id)
        self._refresh_playlist_list()

    # ------------------------------------------------------------------
    # Playlists tab
    # ------------------------------------------------------------------

    def _build_playlists_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)

        left = QVBoxLayout()
        self._playlist_list = QListWidget()
        self._playlist_list.currentItemChanged.connect(lambda *_: self._refresh_playlist_tracks_list())
        left.addWidget(self._playlist_list, stretch=1)

        left_button_row = QHBoxLayout()
        new_button = QPushButton("New Playlist…")
        new_button.clicked.connect(self._on_new_playlist)
        left_button_row.addWidget(new_button)
        delete_button = QPushButton("Delete Playlist")
        delete_button.clicked.connect(self._on_delete_playlist)
        left_button_row.addWidget(delete_button)
        left.addLayout(left_button_row)
        layout.addLayout(left, stretch=1)

        right = QVBoxLayout()
        self._playlist_tracks_list = QListWidget()
        right.addWidget(self._playlist_tracks_list, stretch=1)

        right_button_row = QHBoxLayout()
        play_playlist_button = QPushButton("Play Playlist")
        play_playlist_button.clicked.connect(self._on_play_playlist)
        right_button_row.addWidget(play_playlist_button)
        remove_track_button = QPushButton("Remove Track")
        remove_track_button.clicked.connect(self._on_remove_track_from_playlist)
        right_button_row.addWidget(remove_track_button)
        right.addLayout(right_button_row)
        layout.addLayout(right, stretch=2)

        self._refresh_playlist_list()
        return tab

    def _refresh_playlist_list(self) -> None:
        previously_selected_id = self._selected_playlist_id()
        self._playlist_list.blockSignals(True)
        self._playlist_list.clear()
        playlists = self.context.music.all_playlists()
        for playlist in playlists:
            item = QListWidgetItem(f"{playlist.name}   ({len(playlist.track_ids)} tracks)")
            item.setData(Qt.ItemDataRole.UserRole, playlist.playlist_id)
            self._playlist_list.addItem(item)
            if playlist.playlist_id == previously_selected_id:
                self._playlist_list.setCurrentItem(item)
        if not playlists:
            add_empty_state_item(self._playlist_list, "No playlists yet — click New Playlist to get started.")
        self._playlist_list.blockSignals(False)
        self._refresh_playlist_tracks_list()

    def _selected_playlist_id(self) -> Optional[str]:
        return selected_item_data(self._playlist_list)

    def _refresh_playlist_tracks_list(self) -> None:
        self._playlist_tracks_list.clear()
        playlist_id = self._selected_playlist_id()
        if playlist_id is None:
            return
        tracks = self.context.music.tracks_for_playlist(playlist_id)
        for track in tracks:
            item = QListWidgetItem(format_track_row(track))
            item.setData(Qt.ItemDataRole.UserRole, track.track_id)
            self._playlist_tracks_list.addItem(item)
        if not tracks:
            add_empty_state_item(self._playlist_tracks_list, "No tracks in this playlist yet.")

    def _on_new_playlist(self) -> None:
        dialog = AddEditPlaylistDialog()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.context.music.create_playlist(dialog.entered_name)
        self._refresh_playlist_list()

    def _on_delete_playlist(self) -> None:
        playlist_id = self._selected_playlist_id()
        if playlist_id is None:
            QMessageBox.information(None, "No Playlist Selected", "Select a playlist to delete.")
            return
        playlist = self.context.music.get_playlist(playlist_id)
        confirm = QMessageBox.question(
            None, "Delete Playlist", f"Delete '{playlist.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.context.music.delete_playlist(playlist_id)
        self._refresh_playlist_list()

    def _on_play_playlist(self) -> None:
        playlist_id = self._selected_playlist_id()
        if playlist_id is None:
            QMessageBox.information(None, "No Playlist Selected", "Select a playlist to play.")
            return
        item = self._playlist_tracks_list.currentItem()
        start_index = self._playlist_tracks_list.row(item) if item is not None else 0
        self.context.music.play_playlist(playlist_id, start_index=max(0, start_index))
        self._refresh_transport()

    def _on_remove_track_from_playlist(self) -> None:
        playlist_id = self._selected_playlist_id()
        track_id = selected_item_data(self._playlist_tracks_list)
        if playlist_id is None or track_id is None:
            QMessageBox.information(None, "No Track Selected", "Select a track to remove from this playlist.")
            return
        self.context.music.remove_track_from_playlist(playlist_id, track_id)
        self._refresh_playlist_list()

    # ------------------------------------------------------------------
    # Transport bar — persistent across both tabs
    # ------------------------------------------------------------------

    def _build_transport_bar(self) -> QWidget:
        bar = QWidget()
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(0, 8, 0, 0)

        self._time_label = QLabel("")
        layout.addWidget(self._time_label)

        self._seek_slider = QSlider(Qt.Orientation.Horizontal)
        self._seek_slider.setRange(0, 0)
        self._seek_slider.sliderReleased.connect(self._on_seek_slider_released)
        layout.addWidget(self._seek_slider)

        controls_row = QHBoxLayout()
        previous_button = QPushButton("⏮")  # ⏮
        previous_button.clicked.connect(self._on_previous_clicked)
        controls_row.addWidget(previous_button)

        self._play_pause_button = QPushButton("▶")  # ▶
        self._play_pause_button.clicked.connect(self._on_play_pause_clicked)
        controls_row.addWidget(self._play_pause_button)

        stop_button = QPushButton("⏹")  # ⏹
        stop_button.clicked.connect(self._on_stop_clicked)
        controls_row.addWidget(stop_button)

        next_button = QPushButton("⏭")  # ⏭
        next_button.clicked.connect(self._on_next_clicked)
        controls_row.addWidget(next_button)

        controls_row.addWidget(QLabel("Volume:"))
        self._volume_slider = QSlider(Qt.Orientation.Horizontal)
        self._volume_slider.setRange(0, 100)
        self._volume_slider.sliderReleased.connect(self._on_volume_slider_released)
        controls_row.addWidget(self._volume_slider)

        layout.addLayout(controls_row)
        return bar

    def _refresh_transport(self) -> None:
        now_playing = self.context.music.now_playing()
        self._time_label.setText(format_now_playing_line(now_playing))
        self._play_pause_button.setText("⏸" if now_playing is not None and now_playing.is_playing else "▶")

        if now_playing is not None:
            if not self._seek_slider.isSliderDown():
                self._seek_slider.setRange(0, int(now_playing.duration_seconds))
                self._seek_slider.setValue(int(now_playing.position_seconds))
            if not self._volume_slider.isSliderDown():
                self._volume_slider.setValue(now_playing.volume_percent)
        elif not self._volume_slider.isSliderDown():
            last_volume = self.context.config.get("music.last_volume", 70)
            self._volume_slider.setValue(last_volume)

    def _on_play_pause_clicked(self) -> None:
        now_playing = self.context.music.now_playing()
        if now_playing is not None and now_playing.is_playing:
            self.context.music.pause()
        elif now_playing is not None:
            self.context.music.resume()
        else:
            self._on_play_selected_track()
        self._refresh_transport()

    def _on_stop_clicked(self) -> None:
        self.context.music.stop()
        self._refresh_transport()

    def _on_previous_clicked(self) -> None:
        self.context.music.previous_track()
        self._refresh_transport()

    def _on_next_clicked(self) -> None:
        self.context.music.next_track()
        self._refresh_transport()

    def _on_seek_slider_released(self) -> None:
        self.context.music.seek(self._seek_slider.value())
        self._refresh_transport()

    def _on_volume_slider_released(self) -> None:
        self.context.music.set_volume(self._volume_slider.value())
        self._refresh_transport()
