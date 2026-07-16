"""
gui.widgets.avatar_camera_widget
===================================

AvatarCameraWidget: renders a live camera feed — VMagicMirror's Virtual
Camera Output, in the intended use case — inside a real dashboard
widget, via Qt's own `QCamera`/`QMediaCaptureSession`/`QVideoWidget`
APIs. See `core/avatar_manager.py`'s docstring for why this needs no
VMagicMirror-specific protocol or SDK: VMagicMirror publishes the
rendered avatar as a normal OS video-input device, the same mechanism
an OBS Virtual Camera uses, so this widget is just a generic camera
viewer that happens to be pointed at that device.

Degrades to a placeholder label — never a crash or a blank widget —
whenever there's nothing to show: no camera devices at all, no device
selected yet, or the selected device fails to open (unplugged,
VMagicMirror not running, in use by another app). Same graceful-
degradation stance as `gui/home_dashboard.py`'s Volume/Power widgets.

**Unverified end-to-end in this dev sandbox** — see
`core/avatar_manager.py`'s docstring. `start()`/`stop()`/error-handling
and the placeholder/video visibility toggling are all real code paths,
but there is no camera device anywhere in this sandbox to actually push
a frame through them. Re-verify on the real Windows machine once
VMagicMirror's Virtual Camera Output is enabled: confirm the widget
finds the device, `_on_active_changed` flips to the live feed, and
`_on_error` correctly falls back to the placeholder if VMagicMirror is
later closed while the widget is showing.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QCamera, QMediaCaptureSession, QMediaDevices
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.logger import get_logger

log = get_logger(__name__)

_PLACEHOLDER_NO_DEVICES = "No camera devices found on this system."
_PLACEHOLDER_NOT_SELECTED = "No camera selected — use the ⋯ menu to pick one."
_PLACEHOLDER_ERROR_PREFIX = "Camera unavailable: "


class AvatarCameraWidget(QWidget):
    """A live camera view with a graceful placeholder fallback. Caller
    (gui/home_dashboard.py) owns picking *which* device via
    core/avatar_manager.py — this widget only knows how to open/show/
    release whatever device id it's given."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._camera: Optional[QCamera] = None
        self._capture_session: Optional[QMediaCaptureSession] = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel(_PLACEHOLDER_NOT_SELECTED)
        self._placeholder.setObjectName("DashboardSectionBody")
        self._placeholder.setWordWrap(True)
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._video_widget = QVideoWidget()
        self._video_widget.setMinimumHeight(160)
        self._video_widget.hide()

        layout.addWidget(self._placeholder)
        layout.addWidget(self._video_widget)

    def show_unavailable(self, message: str = _PLACEHOLDER_NO_DEVICES) -> None:
        """No camera devices exist at all — distinct from "one exists
        but nothing's selected yet" so the placeholder text can guide
        the user correctly."""
        self.stop()
        self._placeholder.setText(message)
        self._placeholder.show()
        self._video_widget.hide()

    def show_not_selected(self) -> None:
        self.stop()
        self._placeholder.setText(_PLACEHOLDER_NOT_SELECTED)
        self._placeholder.show()
        self._video_widget.hide()

    def start(self, device_id: str) -> None:
        """Opens the given device (a core.avatar_manager.CameraDeviceInfo.device_id)
        and shows its live feed. Falls back to the placeholder rather
        than raising if the device no longer exists or fails to open —
        a virtual camera disappearing (VMagicMirror closed) is an
        expected, not exceptional, occurrence."""
        self.stop()

        camera_device = next(
            (device for device in QMediaDevices.videoInputs() if bytes(device.id()) == device_id.encode("utf-8")),
            None,
        )
        if camera_device is None:
            self.show_unavailable(f"{_PLACEHOLDER_ERROR_PREFIX}selected camera is no longer connected.")
            return

        self._camera = QCamera(camera_device)
        self._camera.errorOccurred.connect(self._on_error)
        self._capture_session = QMediaCaptureSession()
        self._capture_session.setCamera(self._camera)
        self._capture_session.setVideoOutput(self._video_widget)
        self._camera.start()

        self._placeholder.hide()
        self._video_widget.show()

    def stop(self) -> None:
        """Releases the camera device — call before this widget is
        discarded, same "stop before destroy" convention as
        gui/presence_widget.py's animation timer."""
        if self._camera is not None:
            self._camera.stop()
            self._camera.errorOccurred.disconnect(self._on_error)
            self._camera = None
        self._capture_session = None

    def _on_error(self, error, error_string: str) -> None:  # noqa: ANN001 - QCamera.Error enum
        log.warning("Companion avatar camera error: %s", error_string)
        self.show_unavailable(f"{_PLACEHOLDER_ERROR_PREFIX}{error_string}")
