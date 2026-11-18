"""
os.image_manifest
===================

FW-01's check that two builds of one commit made the same image (DEC-0279, REQ-IMP-010): a manifest of every file
under the given folders (its path, size and SHA-256), and a comparison of two manifests that names every difference
outside the known volatile files.

    python image_manifest.py make /usr manifest.txt     # inside the built image (CI mounts this file in)
    python image_manifest.py compare a.txt b.txt        # 0 when the only differences are VOLATILE ones

Standard library only, so it runs on the image's own Python. **Volatile** files are those a package manager rewrites
with the time or a random id on every install (`VOLATILE`); a difference there is listed but doesn't fail. Anything
else that differs fails the comparison, which is the point: an unexplained difference means an input wasn't pinned.
Symbolic links are recorded by their target, not followed. Fields are separated by tabs, since paths may hold spaces.
"""

from __future__ import annotations

import fnmatch
import hashlib
import os
import sys
from pathlib import Path

SEP = "\t"
VOLATILE = (
    "/usr/lib/sysimage/rpm/*",        # the RPM database: install times
    "/usr/share/rpm/*",               # the same database where an image-based system keeps it
    "/usr/lib/sysimage/libdnf5/*",    # dnf's own state and history
    "/usr/lib/sysimage/dnf/*",
    "/usr/share/info/dir",            # rebuilt by install scriptlets in install order
)


def _digest(path: Path) -> str:
    """A file's SHA-256, read in blocks."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def manifest(roots: list[str]) -> list[str]:
    """One line per file under `roots`, sorted by path: the SHA-256, the size and the path, separated by `SEP`; a
    symbolic link's first field is "link->" and its target, and its size "-"."""
    lines = []
    for root in roots:
        for folder, dirs, files in os.walk(root):
            dirs.sort()
            for name in sorted(files):
                path = Path(folder, name)
                if path.is_symlink():
                    lines.append(SEP.join(("link->" + os.readlink(path), "-", path.as_posix())))
                elif path.is_file():
                    lines.append(SEP.join((_digest(path), str(path.stat().st_size), path.as_posix())))
    return sorted(lines, key=lambda line: line.split(SEP, 2)[-1])


def _by_path(lines: list[str]) -> dict[str, str]:
    """A manifest's lines keyed by path."""
    out = {}
    for line in lines:
        if line.strip():
            digest, size, path = line.split(SEP, 2)
            out[path] = digest + " " + size
    return out


def compare(a: list[str], b: list[str]) -> tuple[list[str], list[str]]:
    """The differences between two manifests: (unexplained, volatile), each "<path>: <what differs>"."""
    left, right = _by_path(a), _by_path(b)
    unexplained, volatile = [], []
    for path in sorted(set(left) | set(right)):
        if left.get(path) == right.get(path):
            continue
        what = "only in the first" if path not in right else "only in the second" if path not in left else "content differs"
        (volatile if any(fnmatch.fnmatch(path, pattern) for pattern in VOLATILE) else unexplained).append(f"{path}: {what}")
    return unexplained, volatile


def main(argv: list[str]) -> int:
    """`make <root>... <out>` writes a manifest; `compare <a> <b>` prints the differences, 1 if any is unexplained."""
    if len(argv) >= 3 and argv[0] == "make":
        Path(argv[-1]).write_text("\n".join(manifest(argv[1:-1])) + "\n", encoding="utf-8")
        return 0
    if len(argv) == 3 and argv[0] == "compare":
        unexplained, volatile = compare(*(Path(p).read_text(encoding="utf-8").splitlines() for p in argv[1:]))
        print(f"{len(volatile)} volatile difference(s) (expected):")
        print("\n".join("  " + line for line in volatile[:50]))
        print(f"{len(unexplained)} unexplained difference(s):")
        print("\n".join("  " + line for line in unexplained[:200]))
        return 1 if unexplained else 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
