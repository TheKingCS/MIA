"""
core.security_cams
====================

Security (DEC-0033; Zac, 2026-10-18: "an app for Security or Smart Home
where I can monitor camera feeds"): your cameras, watched from MIA, with
no cloud in between. The smart-home half (lights, locks, thermostat)
comes later through a local Home Assistant (docs/ROADMAP.md).

- A **camera** is a name, where it is, its brand and its address on the
  home network. The brand fills in the camera's own picture address
  (BRANDS): a still-picture URL where the camera has one (Reolink,
  Amcrest/Dahua, Hikvision: nothing extra needed), else its RTSP stream,
  read one frame at a time with ffmpeg (Tapo, Wyze; on the PC).
- **Only the home network.** MIA only ever talks to addresses inside
  your network (private ranges, .local names, Tailscale's 100.64/10),
  never the internet, and never follows a redirect: the frame endpoint
  can't be turned into a way to fetch something else.
- **Passwords** stay on this device, in the household's folder
  (`security_logins.json`, never in the repo, never sent back to a
  screen, never in an action's record).
- **Pictures**: Save Picture keeps the frame in the household's
  `security/pictures/` folder.

**From anywhere (Zac, 2026-10-18).** The cameras stay on the home
computer's network; MIA on the PC talks to them. A phone linked to that
PC (Settings → Home Computer, core/home_link.py: same Wi-Fi, or anywhere
through Tailscale) shows the PC's cameras too: their ids carry REMOTE
("pc-…"), and their pictures come through the PC with the phone's link
key. Adding, changing and removing a PC camera from the phone is done
on the PC. The cameras themselves are never opened to the internet.

`SecurityBook` is the household's (a household store); camera records
write through atomic_write_text, so removing one can be undone.
"""

from __future__ import annotations

import ipaddress
import json
import re
import shutil
import socket
import subprocess
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote, urlsplit

from core.atomic_write import atomic_write_text
from core.data_recovery import notify_data_corruption
from core.logger import get_logger

log = get_logger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
_FILE = "security_cameras.json"
_LOGINS = "security_logins.json"
TIMEOUT_S = 6
FRESH_S = 0.8  # a frame this new is shared instead of asking the camera again
MAX_BYTES = 8 * 1024 * 1024
REMOTE = "pc-"  # a camera on the linked home computer

# brand: (still-picture path or None, RTSP path or None, help)
BRANDS = {
    "Reolink": ("/cgi-bin/api.cgi?cmd=Snap&channel=0&rs=mia&user={user}&password={password}", "/h264Preview_01_sub",
                "Works out of the box."),
    "Amcrest / Dahua": ("/cgi-bin/snapshot.cgi?channel=1", "/cam/realmonitor?channel=1&subtype=1", "Works out of the box."),
    "Hikvision / Annke": ("/ISAPI/Streaming/channels/101/picture", "/Streaming/Channels/102", "Works out of the box."),
    "Tapo": (None, "/stream2", "Make a camera account in the Tapo app (Camera Settings → Advanced → Camera Account)."),
    "Wyze (RTSP firmware)": (None, "/live", "Needs Wyze's RTSP firmware; use the address it shows."),
    "Other: picture address": ("", None, "Type the path to the camera's still picture (e.g. /snapshot.jpg)."),
    "Other: RTSP stream": (None, "", "Type the stream path (e.g. /stream1)."),
}
LOCATIONS = ("Front Door", "Driveway", "Backyard", "Garage", "Side Yard", "Porch", "Living Room", "Shop", "Barn",
             "Greenhouse", "Other")


class CameraError(Exception):
    """Something a person can fix: the address, the login, the network."""


# ------------------------------------------------------------------ pure logic


def on_home_network(host: str) -> bool:
    """Pure logic (plus a name lookup). True only for addresses inside a
    home network: private ranges, link-local, Tailscale (100.64/10),
    .local names; a name must resolve only to such addresses."""
    host = (host or "").strip().strip("[]").lower()
    if not host or host in ("localhost",) or host.startswith("127."):
        return False
    try:
        return _private(ipaddress.ip_address(host))
    except ValueError:
        pass
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        return False
    try:
        found = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except OSError:
        return host.endswith(".local")  # mDNS names may not resolve here; the fetch will say
    return bool(found) and all(_private(ipaddress.ip_address(a.split("%")[0])) for a in found)


def _private(ip) -> bool:
    if ip.is_loopback or ip.is_multicast or ip.is_unspecified:
        return False
    return ip.is_private or ip.is_link_local or ip in ipaddress.ip_network("100.64.0.0/10")


def clean_host(text: str) -> str:
    """Pure logic. "http://192.168.1.40:80/" -> "192.168.1.40:80"."""
    text = (text or "").strip()
    if "://" in text:
        text = urlsplit(text).netloc
    return text.split("/")[0].split("@")[-1]


def picture_url(brand: str, host: str, path: str = "", user: str = "", password: str = "") -> Optional[str]:
    snap = BRANDS.get(brand, (None, None, ""))[0]
    if snap is None:
        return None
    p = path if brand.startswith("Other") else snap
    if not p:
        return None
    p = p if p.startswith("/") else "/" + p
    return f"http://{host}{p.format(user=quote(user), password=quote(password))}"


def rtsp_url(brand: str, host: str, path: str = "", user: str = "", password: str = "") -> Optional[str]:
    stream = BRANDS.get(brand, (None, None, ""))[1]
    if stream is None:
        return None
    p = path if brand.startswith("Other") else stream
    if not p:
        return None
    p = p if p.startswith("/") else "/" + p
    login = f"{quote(user, safe='')}:{quote(password, safe='')}@" if user else ""
    port = "" if ":" in host else ":554"
    return f"rtsp://{login}{host}{port}{p}"


# ------------------------------------------------------------------ the store


@dataclass
class Camera:
    camera_id: str
    name: str
    location: str = "Other"
    brand: str = "Reolink"
    host: str = ""
    path: str = ""
    added_at: str = ""


class SecurityBook:
    def __init__(self, context, data_dir: Optional[Path] = None) -> None:
        self.context = context
        self.data_dir = Path(data_dir) if data_dir is not None else _DATA_DIR
        self._file = self.data_dir / _FILE
        self.cameras: list[Camera] = []
        self._frames: dict[str, tuple[float, bytes]] = {}
        self.last_error: dict[str, str] = {}
        self.remote_names: dict[str, str] = {}  # the home computer's cameras, as last seen
        self.home_down_until = 0.0  # the computer didn't answer: don't wait on it again until then
        self._load()

    def _load(self) -> None:
        self.cameras = []
        if not self._file.exists():
            return
        try:
            raw = json.loads(self._file.read_text(encoding="utf-8"))
            fields = Camera.__dataclass_fields__
            self.cameras = [Camera(**{k: v for k, v in c.items() if k in fields}) for c in raw.get("cameras") or []]
        except (json.JSONDecodeError, OSError, TypeError, ValueError, AttributeError):
            log.exception("security_cameras.json unreadable — starting empty.")
            notify_data_corruption(self.context, _FILE)

    def reload(self) -> None:
        self._load()

    def _save(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(self._file, json.dumps({"cameras": [asdict(c) for c in self.cameras]}, indent=2,
                                                 ensure_ascii=False))

    # Logins: a separate file, never shown, never in an action's record.
    def _logins(self) -> dict:
        try:
            return json.loads((self.data_dir / _LOGINS).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}

    def login(self, camera_id: str) -> tuple[str, str]:
        entry = self._logins().get(camera_id) or {}
        return str(entry.get("user") or ""), str(entry.get("password") or "")

    def set_login(self, camera_id: str, user: str, password: Optional[str]) -> None:
        logins = self._logins()
        old = logins.get(camera_id) or {}
        logins[camera_id] = {"user": user, "password": old.get("password", "") if password is None else password}
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / _LOGINS
        path.write_text(json.dumps(logins), encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass

    def get(self, camera_id: str) -> Optional[Camera]:
        return next((c for c in self.cameras if c.camera_id == camera_id), None)

    def save_camera(self, camera_id: Optional[str], name: str, location: str, brand: str, host: str, path: str,
                    user: str, password: Optional[str]) -> Camera:
        """Add or change a camera (with its login). Checks it first."""
        name, host = (name or "").strip(), clean_host(host)
        if not name:
            raise CameraError("Give the camera a name, like Front Door.")
        if brand not in BRANDS:
            raise CameraError("Pick the camera's brand (or Other).")
        if not host:
            raise CameraError("Type the camera's address on your network, like 192.168.1.40.")
        if not on_home_network(host.rsplit(":", 1)[0] if host.count(":") == 1 else host):
            raise CameraError("MIA only talks to cameras on your home network (an address like 192.168.x.x).")
        if brand.startswith("Other") and not (path or "").strip():
            raise CameraError("Type the camera's picture or stream path.")
        cam = self.get(camera_id) if camera_id else None
        if cam is None:
            cam = Camera(uuid.uuid4().hex[:10], name, added_at=datetime.now().isoformat(timespec="seconds"))
            self.cameras.append(cam)
        cam.name, cam.location, cam.brand, cam.host, cam.path = name, location or "Other", brand, host, (path or "").strip()
        self._save()
        self.set_login(cam.camera_id, (user or "").strip(), password)
        self._frames.pop(cam.camera_id, None)
        return cam

    def remove(self, camera_id: str) -> None:
        self.cameras = [c for c in self.cameras if c.camera_id != camera_id]
        self._save()

    # ------------------------------------------------------------------ frames

    def frame(self, camera_id: str) -> bytes:
        """The camera's picture right now (JPEG). Raises CameraError."""
        cam = self.get(camera_id)
        if cam is None and not camera_id.startswith(REMOTE):
            raise CameraError("That camera isn't set up anymore.")
        cached = self._frames.get(camera_id)
        if cached and time.monotonic() - cached[0] < FRESH_S:
            return cached[1]
        try:
            data = self._grab(cam) if cam is not None else self._from_home(camera_id[len(REMOTE):])
        except CameraError as problem:
            self.last_error[camera_id] = str(problem)
            raise
        self._frames[camera_id] = (time.monotonic(), data)
        self.last_error.pop(camera_id, None)
        return data

    def _from_home(self, remote_id: str) -> bytes:
        """A picture from one of the home computer's cameras, through MIA there."""
        from core.home_link import HomeLinkError, home_call

        if not re.fullmatch(r"[0-9a-f]{10}", remote_id):
            raise CameraError("That camera isn't set up anymore.")
        try:
            data = home_call(self.context, f"/api/security/cameras/{remote_id}/frame", timeout=TIMEOUT_S + 6, raw=True)
        except HomeLinkError as problem:
            raise CameraError(str(problem)) from None
        if not data.startswith(b"\xff\xd8"):
            raise CameraError("The home computer didn't send a picture.")
        return data

    def _grab(self, cam: Camera) -> bytes:
        host_only = cam.host.rsplit(":", 1)[0] if cam.host.count(":") == 1 else cam.host
        if not on_home_network(host_only):
            raise CameraError("That address isn't on your home network.")
        user, password = self.login(cam.camera_id)
        url = picture_url(cam.brand, cam.host, cam.path, user, password)
        if url:
            return _http_picture(url, user, password)
        stream = rtsp_url(cam.brand, cam.host, cam.path, user, password)
        if stream:
            return _rtsp_picture(stream)
        raise CameraError("MIA doesn't know how to reach this camera.")

    # ------------------------------------------------------------------ pictures

    def pictures_dir(self) -> Path:
        return self.data_dir / "security" / "pictures"

    def save_picture(self, camera_id: str) -> str:
        data = self.frame(camera_id)
        folder = self.pictures_dir()
        folder.mkdir(parents=True, exist_ok=True)
        name = f"{datetime.now():%Y%m%d-%H%M%S}_{camera_id.removeprefix(REMOTE)}.jpg"
        (folder / name).write_bytes(data)
        return name

    def pictures(self) -> list[dict]:
        folder = self.pictures_dir()
        names = {**self.remote_names, **{c.camera_id: c.name for c in self.cameras}}
        out = []
        if folder.is_dir():
            for p in sorted(folder.glob("*.jpg"), reverse=True)[:200]:
                stamp, _, rest = p.stem.partition("_")
                try:
                    when = datetime.strptime(stamp, "%Y%m%d-%H%M%S")
                except ValueError:
                    continue
                out.append({"name": p.name, "camera": names.get(rest, "A camera"), "at": when.isoformat(timespec="minutes")})
        return out

    def picture_path(self, name: str) -> Path:
        if not re.fullmatch(r"\d{8}-\d{6}_[0-9a-f]{10}\.jpg", name or ""):
            raise CameraError("No such picture.")
        path = self.pictures_dir() / name
        if not path.is_file():
            raise CameraError("No such picture.")
        return path

    def delete_picture(self, name: str) -> None:
        self.picture_path(name).unlink()


def _http_picture(url: str, user: str, password: str) -> bytes:
    import requests
    from requests.auth import HTTPDigestAuth

    try:
        r = requests.get(url, timeout=TIMEOUT_S, allow_redirects=False, stream=True,
                         auth=(user, password) if user else None)
        if r.status_code == 401 and user:
            r = requests.get(url, timeout=TIMEOUT_S, allow_redirects=False, stream=True,
                             auth=HTTPDigestAuth(user, password))
    except requests.Timeout:
        raise CameraError("The camera didn't answer. Is it on, and on the same network?") from None
    except requests.RequestException:
        raise CameraError("MIA couldn't reach the camera at that address.") from None
    if r.status_code in (401, 403):
        raise CameraError("The camera said the username or password is wrong.")
    if r.status_code != 200:
        raise CameraError(f"The camera answered with an error ({r.status_code}). Check the brand and address.")
    data = r.raw.read(MAX_BYTES + 1, decode_content=True)
    if len(data) > MAX_BYTES or not data.startswith(b"\xff\xd8"):
        raise CameraError("The camera didn't send a picture. Check the brand and address.")
    return data


def _rtsp_picture(url: str) -> bytes:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise CameraError("This camera streams video (RTSP), which needs ffmpeg on this device. "
                          "On the PC: winget install ffmpeg (docs/SECURITY_CAMERAS.md).")
    try:
        done = subprocess.run([ffmpeg, "-nostdin", "-loglevel", "error", "-rtsp_transport", "tcp", "-i", url,
                               "-frames:v", "1", "-q:v", "5", "-f", "image2", "-vcodec", "mjpeg", "pipe:1"],
                              capture_output=True, timeout=TIMEOUT_S + 4, check=False)
    except subprocess.TimeoutExpired:
        raise CameraError("The camera's stream didn't answer in time.") from None
    if done.returncode != 0 or not done.stdout.startswith(b"\xff\xd8"):
        err = done.stderr.decode("utf-8", "replace").lower()
        if "401" in err or "unauthorized" in err:
            raise CameraError("The camera said the username or password is wrong.")
        raise CameraError("MIA couldn't read the camera's stream. Check the brand, address and login.")
    return done.stdout[:MAX_BYTES]


# ------------------------------------------------------------------ the screen


def _home_cameras(context, book) -> dict:
    """The linked home computer's cameras (core/home_link.py): ready to
    show here, their pictures coming through the PC."""
    from core.home_link import HomeLinkError, home_call, linked

    if not linked(context):
        return {"linked": False, "reachable": False, "problem": "", "cameras": []}
    if time.monotonic() < book.home_down_until:
        return {"linked": True, "reachable": False, "problem": "Can't reach the home computer right now.", "cameras": []}
    try:
        there = home_call(context, "/api/security", timeout=4)
    except HomeLinkError as problem:
        book.home_down_until = time.monotonic() + 30
        return {"linked": True, "reachable": False, "problem": str(problem), "cameras": []}
    cams = []
    for c in there.get("cameras") or []:
        if c.get("on_pc") or not re.fullmatch(r"[0-9a-f]{10}", str(c.get("id") or "")):
            continue  # only the computer's own cameras, never a chain
        book.remote_names[c["id"]] = c.get("name") or "A camera"
        cams.append({**{k: c.get(k) for k in ("name", "location", "brand", "host", "path", "user", "has_password",
                                                "problem", "needs_ffmpeg")},
                     "id": REMOTE + c["id"], "on_pc": True,
                     "frame": f"/api/security/cameras/{REMOTE}{c['id']}/frame"})
    return {"linked": True, "reachable": True, "problem": "", "cameras": cams}


def security_page(context) -> dict:
    book = getattr(context, "security", None)
    if book is None:
        return {"available": False}
    cams = []
    for c in book.cameras:
        user, password = book.login(c.camera_id)
        cams.append({"id": c.camera_id, "name": c.name, "location": c.location, "brand": c.brand, "host": c.host,
                     "path": c.path, "user": user, "has_password": bool(password),
                     "problem": book.last_error.get(c.camera_id, ""),
                     "frame": f"/api/security/cameras/{c.camera_id}/frame",
                     "needs_ffmpeg": picture_url(c.brand, c.host, c.path) is None and shutil.which("ffmpeg") is None})
    home = _home_cameras(context, book)
    cams += home.pop("cameras")
    order = {loc: i for i, loc in enumerate(LOCATIONS)}
    cams.sort(key=lambda c: (order.get(c["location"], 99), c["name"].lower()))
    pictures = book.pictures()
    return {"available": True, "cameras": cams, "pictures": pictures[:60], "home": home,
            "counts": {"cameras": len(cams), "pictures": len(pictures)},
            "brands": [{"name": b, "help": h, "kind": "picture" if s is not None else "stream"}
                       for b, (s, _r, h) in BRANDS.items()],
            "locations": list(LOCATIONS), "ffmpeg": shutil.which("ffmpeg") is not None}
