"""
tests.test_update_manager
============================

Unit tests for core.update_manager. Isolates _PROJECT_ROOT into a
tmp_path scratch area (same monkeypatch pattern as
test_backup_manager.py) so these tests never touch the real project
files. Git-commit tests `git init` a throwaway repo in tmp_path —
never the real project repo — with a local (not global) commit
identity, so they don't depend on the test machine's git config and
can never write a commit into this project's real history.
"""

from __future__ import annotations

import json
import subprocess
import zipfile
from pathlib import Path

import pytest

import core.update_manager as update_manager_module
from core.update_manager import apply_update_package, peek_update_manifest


def _write_update_zip(path: Path, files: dict, manifest: dict | None = None) -> None:
    """files: {relative_path_str: content_str}. manifest=None means omit it entirely."""
    with zipfile.ZipFile(path, "w") as zf:
        if manifest is not None:
            zf.writestr("update_manifest.json", json.dumps(manifest))
        for relative_path, content in files.items():
            zf.writestr(relative_path, content)


@pytest.fixture
def isolated_project(tmp_path, monkeypatch):
    project_root = tmp_path / "project"
    project_root.mkdir()
    monkeypatch.setattr(update_manager_module, "_PROJECT_ROOT", project_root)
    return project_root


@pytest.fixture
def isolated_git_project(isolated_project):
    project_root = isolated_project
    subprocess.run(["git", "init", "-q"], cwd=project_root, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=project_root, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=project_root, check=True)
    (project_root / "README.md").write_text("baseline\n")
    subprocess.run(["git", "add", "-A"], cwd=project_root, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "baseline"], cwd=project_root, check=True)
    return project_root


def test_valid_update_applies_files(isolated_project, tmp_path):
    update_zip = tmp_path / "update.zip"
    _write_update_zip(
        update_zip,
        files={"core/thing.py": "print('hello')\n", "docs/NOTE.md": "a note\n"},
        manifest={"app": "M.I.A.", "manifest_version": 1, "description": "test update"},
    )

    result = apply_update_package(update_zip)

    assert result.passed is True
    assert set(result.applied_files) == {"core/thing.py", "docs/NOTE.md"}
    assert (isolated_project / "core" / "thing.py").read_text() == "print('hello')\n"
    assert (isolated_project / "docs" / "NOTE.md").read_text() == "a note\n"


def test_update_overwrites_existing_file(isolated_project, tmp_path):
    existing = isolated_project / "core" / "thing.py"
    existing.parent.mkdir(parents=True)
    existing.write_text("old content\n")

    update_zip = tmp_path / "update.zip"
    _write_update_zip(
        update_zip,
        files={"core/thing.py": "new content\n"},
        manifest={"app": "M.I.A."},
    )

    result = apply_update_package(update_zip)

    assert result.passed is True
    assert existing.read_text() == "new content\n"


def test_missing_manifest_is_rejected(isolated_project, tmp_path):
    update_zip = tmp_path / "update.zip"
    _write_update_zip(update_zip, files={"core/thing.py": "x\n"}, manifest=None)

    result = apply_update_package(update_zip)

    assert result.passed is False
    assert "missing manifest" in result.errors[0]
    assert not (isolated_project / "core").exists()


def test_wrong_app_in_manifest_is_rejected(isolated_project, tmp_path):
    update_zip = tmp_path / "update.zip"
    _write_update_zip(
        update_zip, files={"core/thing.py": "x\n"}, manifest={"app": "SomeOtherApp"}
    )

    result = apply_update_package(update_zip)

    assert result.passed is False
    assert not (isolated_project / "core").exists()


def test_manifest_only_package_is_rejected(isolated_project, tmp_path):
    update_zip = tmp_path / "update.zip"
    _write_update_zip(update_zip, files={}, manifest={"app": "M.I.A."})

    result = apply_update_package(update_zip)

    assert result.passed is False
    assert "no files besides the manifest" in result.errors[0]


def test_not_a_zip_is_rejected(isolated_project, tmp_path):
    junk = tmp_path / "not_an_update.zip"
    junk.write_bytes(b"just some random bytes")

    result = apply_update_package(junk)

    assert result.passed is False


def test_safe_extract_rejects_path_traversal(tmp_path):
    malicious_zip_path = tmp_path / "evil.zip"
    with zipfile.ZipFile(malicious_zip_path, "w") as zf:
        zf.writestr("update_manifest.json", json.dumps({"app": "M.I.A."}))
        zf.writestr("../../evil.txt", "gotcha")

    target_dir = tmp_path / "staging"
    target_dir.mkdir()

    with zipfile.ZipFile(malicious_zip_path) as zf:
        with pytest.raises(update_manager_module.UpdateError):
            update_manager_module._safe_extract_all(zf, target_dir)


def test_peek_update_manifest_reads_description_and_version(tmp_path):
    update_zip = tmp_path / "update.zip"
    _write_update_zip(
        update_zip,
        files={"core/thing.py": "x\n"},
        manifest={"app": "M.I.A.", "target_version": "0.3.0", "description": "does a thing"},
    )

    manifest = peek_update_manifest(update_zip)

    assert manifest is not None
    assert manifest.target_version == "0.3.0"
    assert manifest.description == "does a thing"


def test_peek_update_manifest_returns_none_for_non_update_zip(tmp_path):
    junk_zip = tmp_path / "junk.zip"
    with zipfile.ZipFile(junk_zip, "w") as zf:
        zf.writestr("hello.txt", "not an update package")

    assert peek_update_manifest(junk_zip) is None


def test_peek_update_manifest_returns_none_for_non_zip_file(tmp_path):
    junk = tmp_path / "not_a_zip.txt"
    junk.write_text("hello")
    assert peek_update_manifest(junk) is None


def test_apply_creates_git_commit_touching_only_applied_files(isolated_git_project, tmp_path):
    project_root = isolated_git_project
    # Simulate unrelated uncommitted dev work already sitting in the tree.
    (project_root / "unrelated_wip.txt").write_text("do not touch\n")

    update_zip = tmp_path / "update.zip"
    _write_update_zip(
        update_zip,
        files={"core/thing.py": "print('hi')\n"},
        manifest={"app": "M.I.A.", "description": "adds thing.py"},
    )

    result = apply_update_package(update_zip)

    assert result.passed is True
    assert result.committed is True
    assert result.warnings == []

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout
    # The update's own file was committed (clean); the unrelated file
    # is still untracked/uncommitted, exactly as it was before.
    assert "core/thing.py" not in status
    assert "unrelated_wip.txt" in status

    log_output = subprocess.run(
        ["git", "log", "-1", "--pretty=%B"], cwd=project_root, check=True, capture_output=True, text=True
    ).stdout
    assert "adds thing.py" in log_output


def test_apply_without_git_repo_reports_no_commit(isolated_project, tmp_path):
    # isolated_project has no .git at all.
    update_zip = tmp_path / "update.zip"
    _write_update_zip(update_zip, files={"core/thing.py": "x\n"}, manifest={"app": "M.I.A."})

    result = apply_update_package(update_zip)

    assert result.passed is True
    assert result.committed is False
    assert result.warnings  # explains why no commit was made
