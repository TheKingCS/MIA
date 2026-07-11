"""
modules.files_mod.file_operations
====================================

Pure filesystem logic backing the Files module (modules/files_mod/
module.py) — kept as free functions, not methods, so they're
unit-testable without a Qt event loop. The widget itself uses
QFileSystemModel + QTreeView for browsing/listing (Qt's own
battle-tested file-browsing widgets, not reimplemented here); these
functions cover the operations QFileSystemModel doesn't do for you:
creating/renaming/deleting with clear error messages, and building a
text/image preview.

Delete is genuinely permanent — there is no trash/recycle bin (that
would need an extra dependency, send2trash, which this project isn't
pulling in for one feature). The GUI layer is expected to gate delete
behind a strong, typed confirmation (see gui/delete_confirm_dialog.py)
given how irreversible this is.
"""

from __future__ import annotations

import shutil
from pathlib import Path

_TEXT_PREVIEW_MAX_BYTES = 200_000
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}


def format_size(size_bytes: int) -> str:
    """Human-readable file size, e.g. 1536 -> '1.5 KB'."""
    if size_bytes < 0:
        raise ValueError("size_bytes must be non-negative.")

    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB", "PB"):
        if size < 1024.0 or unit == "PB":
            return f"{int(size)} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0


def create_folder(parent_dir: Path, name: str) -> Path:
    """Create a new folder named `name` inside `parent_dir`. Raises on a bad name or a collision."""
    name = name.strip()
    if not name:
        raise ValueError("Folder name can't be empty.")
    if "/" in name or "\\" in name:
        raise ValueError("Folder name can't contain path separators.")

    target = parent_dir / name
    if target.exists():
        raise FileExistsError(f"'{name}' already exists.")

    target.mkdir()
    return target


def rename_item(path: Path, new_name: str) -> Path:
    """Rename `path` (file or folder) to `new_name`, staying in the same parent directory."""
    new_name = new_name.strip()
    if not new_name:
        raise ValueError("Name can't be empty.")
    if "/" in new_name or "\\" in new_name:
        raise ValueError("Name can't contain path separators.")

    target = path.parent / new_name
    if target.exists():
        raise FileExistsError(f"'{new_name}' already exists.")

    path.rename(target)
    return target


def delete_item(path: Path) -> None:
    """Permanently delete `path` — a file, or a folder and everything inside it. No trash/undo."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def is_image_file(path: Path) -> bool:
    """True if `path`'s extension is a raster format QPixmap can load natively."""
    return path.suffix.lower() in _IMAGE_EXTENSIONS


def is_probably_text_file(path: Path) -> bool:
    """
    Heuristic: read a small chunk and check it's valid UTF-8 with no
    NUL bytes. Not perfect (some legitimate text encodings will be
    rejected, some binary formats could pass), but good enough to
    decide "try a text preview" vs "show file info instead" without
    needing a real MIME-type library.
    """
    try:
        with path.open("rb") as f:
            chunk = f.read(8192)
    except OSError:
        return False

    if b"\x00" in chunk:
        return False
    try:
        chunk.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def read_text_preview(path: Path, max_bytes: int = _TEXT_PREVIEW_MAX_BYTES) -> str:
    """Read up to `max_bytes` of `path` as text, noting if the file was truncated."""
    with path.open("rb") as f:
        data = f.read(max_bytes + 1)

    truncated = len(data) > max_bytes
    text = data[:max_bytes].decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n… (truncated — file is larger than the preview limit)"
    return text
