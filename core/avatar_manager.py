"""
core.avatar_manager
======================

Companion-avatar camera source for the Home Dashboard's Companion
Avatar widget (gui/home_dashboard.py, gui/widgets/avatar_camera_widget.py).
Built for VMagicMirror (https://malaybaku.github.io/VMagicMirror/), a
separately-running, Windows-only Unity/VRM avatar app the user has been
running alongside M.I.A. — but this manager never talks to VMagicMirror
directly, and knows nothing VMagicMirror-specific at all. VMagicMirror's
own "Virtual Camera Output" setting (its Window tab) publishes the
rendered avatar as a normal OS video-input device, the same mechanism
an OBS Virtual Camera uses — any app can read it exactly like a real
webcam via Qt's own camera APIs, no VMagicMirror SDK/protocol needed.
That also means this manager works unchanged for literally any other
virtual-camera source someone points it at later.

**Config-driven device *selection*, not auto-detection.** A machine
typically has a real webcam alongside a virtual one, and there's no
reliable cross-platform way to tell them apart by name alone (a virtual
camera's device name isn't guaranteed stable across app versions/OS
reinstalls). `dashboard.avatar_camera_device` stores the exact
`QCameraDevice.id()` the user picked via the widget's own "Select
Camera" menu action — same self-contained-in-the-widget config pattern
as the Volume widget's mute button, no separate Settings-module page
needed.

**Why core/ imports PySide6 here despite the "core/ knows about nothing
else" layering rule**: this only touches Qt's device-enumeration API
(`QMediaDevices`), never a widget or any rendering — the same scoped
exception already established for `core/chat_worker.py`/
`core/tts_worker.py`/`core/push_to_talk_trigger.py` (QThread workers
living in core/ despite the "no threading in core" rule, because none
of them touch actual widgets). `gui/widgets/avatar_camera_widget.py`
owns the real `QCamera`/`QVideoWidget` construction and rendering —
gui/ owns rendering, core/ owns registry/config-backed truth, same
split as `core/dashboard_widgets.py`.

**Genuinely unverifiable end-to-end in this dev sandbox**: this is a
Linux/WSL2 sandbox with zero camera devices at all (confirmed —
`QMediaDevices.videoInputs()` returns an empty list here) and
VMagicMirror itself only runs on Windows, so there's no way to exercise
a real video frame from this environment. Same "confirmed blocked, not
just untested" situation as `core/volume_manager.py`'s missing
`amixer`. Device listing/selection/graceful-unavailable-state logic
below is real and covered by tests; the actual live video path needs
verification on the real Windows machine once VMagicMirror's Virtual
Camera Output is enabled there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from core.app_context import AppContext
from core.logger import get_logger

log = get_logger(__name__)

_CONFIG_KEY_DEVICE = "dashboard.avatar_camera_device"


@dataclass(frozen=True)
class CameraDeviceInfo:
    device_id: str
    description: str


class AvatarManager:
    """Core-level Companion Avatar service (`AppContext.avatar`)."""

    def __init__(self, context: AppContext) -> None:
        self.context = context

    def list_devices(self) -> list[CameraDeviceInfo]:
        """Every camera device the OS currently reports — real webcams
        and any virtual camera (e.g. VMagicMirror's) are indistinguishable
        by this layer alone, which is exactly why selection is manual,
        not automatic. Returns an empty list (never raises) on a
        platform/sandbox with no camera devices, e.g. this dev sandbox."""
        from PySide6.QtMultimedia import QMediaDevices

        try:
            devices = QMediaDevices.videoInputs()
        except Exception as exc:  # pragma: no cover - defensive, no known trigger
            log.debug("Camera device enumeration unavailable: %s", exc)
            return []
        return [
            CameraDeviceInfo(
                device_id=bytes(device.id()).decode("utf-8", errors="replace"),
                description=device.description(),
            )
            for device in devices
        ]

    def selected_device_id(self) -> Optional[str]:
        return self.context.config.get(_CONFIG_KEY_DEVICE, None)

    def set_selected_device_id(self, device_id: Optional[str]) -> None:
        self.context.config.set(_CONFIG_KEY_DEVICE, device_id)
        self.context.config.save()
        self.context.events.publish("dashboard.avatar_device_changed")

    def is_available(self) -> bool:
        """At least one camera device exists right now, whether or not
        the user has picked one yet — the widget's own "not configured"
        vs. "no camera at all" placeholder text tells those two apart."""
        return len(self.list_devices()) > 0
