"""
tests.test_os_image
=====================

FW-01's checks on how the MIA OS image is made (DEC-0263, DEC-0279; `docs/mia_os/MIA_OS_FINAL_IMPLEMENTATION_ROADMAP.md`
§4): the base pinned by digest, MIA's Python packages hash-locked and the locks covering `requirements.txt`, the
reference PC's model set in the image, the GPU bench measuring that same model, the build checked on every change and
weekly, and `os/image_manifest.py` naming every difference between two builds. They read files only: nothing is built.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version

ROOT = Path(__file__).resolve().parent.parent
OS = ROOT / "os"


def _load(name: str, path: Path):
    """Imports a file from `os/` as a module (the folder isn't a package)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lock_tool = _load("lock_requirements", OS / "lock_requirements.py")
manifest_tool = _load("image_manifest", OS / "image_manifest.py")


def _locked(path: Path) -> dict[str, tuple[Version, int]]:
    """A lock's packages: name -> (version, number of hashes)."""
    out, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)==(\S+)", line)
        if match:
            current = lock_tool.requirement_name(match.group(1))
            out[current] = (Version(match.group(2)), 0)
        elif current and "--hash=sha256:" in line:
            out[current] = (out[current][0], out[current][1] + 1)
    return out


def test_the_image_starts_from_a_base_pinned_by_its_digest():
    base = re.search(r"^ARG BASE=(\S+)", (OS / "Containerfile").read_text(encoding="utf-8"), re.M).group(1)
    assert re.fullmatch(r"quay\.io/fedora-ostree-desktops/kinoite@sha256:[0-9a-f]{64}", base), base


def test_the_lock_covers_every_requirement_the_image_installs_at_an_allowed_version():
    locked = _locked(OS / "requirements.lock")
    for line in lock_tool.image_requirements((ROOT / "requirements.txt").read_text(encoding="utf-8")):
        req = Requirement(line.split("#", 1)[0].strip())
        name = lock_tool.requirement_name(req.name)
        assert name in locked, f"{name} isn't in os/requirements.lock: run python os/lock_requirements.py"
        assert req.specifier.contains(locked[name][0], prereleases=True), (name, str(req.specifier), locked[name][0])


def test_every_locked_package_carries_a_hash_and_piper_stays_out():
    locked = _locked(OS / "requirements.lock")
    assert all(hashes >= 1 for _, hashes in locked.values())
    assert "piper-tts" not in locked and "piper-tts" in lock_tool.IMAGE_EXCLUDED
    build = _locked(OS / "requirements-build.lock")
    assert set(lock_tool.BUILD_TOOLS) <= set(build) and all(hashes >= 1 for _, hashes in build.values())


def test_the_containerfile_installs_only_from_the_locks_with_hashes_required():
    text = re.sub(r"^#.*$", "", (OS / "Containerfile").read_text(encoding="utf-8"), flags=re.M)
    assert "requirements.txt" not in text
    assert text.count("--require-hashes") == 2 and "--upgrade pip" not in text
    for name in lock_tool.SOURCE_ONLY:
        assert f"--no-binary {name}" in text


def test_the_compiled_python_cache_is_removed_after_everything_that_could_write_one():
    text = (OS / "Containerfile").read_text(encoding="utf-8")
    run = text[text.index("python3.13 -m venv"):text.index("# Her runtime as a user service")]
    assert run.index("-name __pycache__") > run.index("pip freeze") > run.index("import core.runtime")
    assert "/usr/share/rpm/*" in manifest_tool.VOLATILE


def test_the_image_sets_the_everyday_model_and_the_bench_measures_that_model():
    text = (OS / "Containerfile").read_text(encoding="utf-8")
    model = re.search(r"model='([^']+)', num_ctx=(\d+)", text)
    assert model and model.group(1) == "qwen2.5:14b" and model.group(2) == "32768"
    bench = _load("gpu_bench", OS / "poc" / "gpu_bench.py")
    assert bench.BAR[0] == model.group(1) and bench.BAR[0] in bench.MODELS and bench.BAR[0] in bench.WINDOWS
    assert abs(bench.BAR[1] - 0.9 * bench.WINDOWS[bench.BAR[0]][1]) < 0.5


def test_the_image_build_is_checked_on_every_push_and_the_vm_on_its_inputs_and_daily():
    poc = (ROOT / ".github" / "workflows" / "mia-os-poc.yml").read_text(encoding="utf-8")
    trigger = poc.split("\non:\n", 1)[1].split("\nconcurrency:", 1)[0]
    assert "push:" in trigger and "paths:" not in trigger and "cron:" in trigger  # the whole repository is an input
    assert "build --no-cache" in poc and "image_manifest.py compare" in poc
    assert poc.count("|| { echo") >= 1 and "exit 1; }" in poc  # a differing package list fails the step
    vm = (ROOT / ".github" / "workflows" / "mia-os-vm.yml").read_text(encoding="utf-8")
    assert 'cron: "47 8 * * *"' in vm
    for path in ('"os/**"', '"requirements.txt"', '"config/default_config.json"', '"core/config_manager.py"'):
        assert path in vm, path


def test_the_manifest_names_a_changed_file_but_not_a_volatile_one(tmp_path):
    for build in ("a", "b"):
        (tmp_path / build / "usr" / "lib" / "sysimage" / "rpm").mkdir(parents=True)
        (tmp_path / build / "usr" / "same.txt").write_text("same", encoding="utf-8")
        (tmp_path / build / "usr" / "with space.txt").write_text("same", encoding="utf-8")
    (tmp_path / "a" / "usr" / "changed.txt").write_text("one", encoding="utf-8")
    (tmp_path / "b" / "usr" / "changed.txt").write_text("two", encoding="utf-8")
    (tmp_path / "a" / "usr" / "lib" / "sysimage" / "rpm" / "rpmdb.sqlite").write_text("t1", encoding="utf-8")
    (tmp_path / "b" / "usr" / "lib" / "sysimage" / "rpm" / "rpmdb.sqlite").write_text("t2", encoding="utf-8")

    def made(build):
        """The build's manifest, with its paths made relative so the two compare."""
        root = (tmp_path / build).as_posix()
        return [line.replace(root, "") for line in manifest_tool.manifest([str(tmp_path / build / "usr")])]

    unexplained, volatile = manifest_tool.compare(made("a"), made("b"))
    assert unexplained == ["/usr/changed.txt: content differs"]
    assert volatile == ["/usr/lib/sysimage/rpm/rpmdb.sqlite: content differs"]
    assert manifest_tool.compare(made("a"), made("a")) == ([], [])


def test_a_requirement_line_is_read_by_its_normalised_name():
    assert lock_tool.requirement_name("PySide6>=6.6,<7.0") == "pyside6"
    assert lock_tool.requirement_name("plaid_python>=44  # bank sync") == "plaid-python"
    assert lock_tool.requirement_name("# a comment") == "" and lock_tool.requirement_name("") == ""
