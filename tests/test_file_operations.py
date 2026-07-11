"""
tests.test_file_operations
=============================

Unit tests for modules.files_mod.file_operations. All filesystem
operations run against pytest's tmp_path, never real project or user
files.
"""

from __future__ import annotations

import pytest

from modules.files_mod.file_operations import (
    create_folder,
    delete_item,
    format_size,
    is_image_file,
    is_probably_text_file,
    read_text_preview,
    rename_item,
)


# ----------------------------------------------------------------------
# format_size
# ----------------------------------------------------------------------

def test_format_size_bytes():
    assert format_size(500) == "500 B"


def test_format_size_kilobytes():
    assert format_size(1536) == "1.5 KB"


def test_format_size_megabytes():
    assert format_size(5 * 1024 * 1024) == "5.0 MB"


def test_format_size_zero():
    assert format_size(0) == "0 B"


def test_format_size_negative_raises():
    with pytest.raises(ValueError):
        format_size(-1)


# ----------------------------------------------------------------------
# create_folder
# ----------------------------------------------------------------------

def test_create_folder(tmp_path):
    result = create_folder(tmp_path, "new_folder")
    assert result == tmp_path / "new_folder"
    assert result.is_dir()


def test_create_folder_empty_name_raises(tmp_path):
    with pytest.raises(ValueError):
        create_folder(tmp_path, "   ")


def test_create_folder_with_path_separator_raises(tmp_path):
    with pytest.raises(ValueError):
        create_folder(tmp_path, "a/b")


def test_create_folder_collision_raises(tmp_path):
    (tmp_path / "existing").mkdir()
    with pytest.raises(FileExistsError):
        create_folder(tmp_path, "existing")


# ----------------------------------------------------------------------
# rename_item
# ----------------------------------------------------------------------

def test_rename_file(tmp_path):
    original = tmp_path / "old.txt"
    original.write_text("hello")

    result = rename_item(original, "new.txt")

    assert result == tmp_path / "new.txt"
    assert result.read_text() == "hello"
    assert not original.exists()


def test_rename_empty_name_raises(tmp_path):
    original = tmp_path / "old.txt"
    original.write_text("hello")
    with pytest.raises(ValueError):
        rename_item(original, "")


def test_rename_collision_raises(tmp_path):
    original = tmp_path / "old.txt"
    original.write_text("hello")
    (tmp_path / "taken.txt").write_text("already here")

    with pytest.raises(FileExistsError):
        rename_item(original, "taken.txt")


# ----------------------------------------------------------------------
# delete_item
# ----------------------------------------------------------------------

def test_delete_file(tmp_path):
    target = tmp_path / "doomed.txt"
    target.write_text("bye")
    delete_item(target)
    assert not target.exists()


def test_delete_directory_recursively(tmp_path):
    target = tmp_path / "doomed_dir"
    target.mkdir()
    (target / "nested.txt").write_text("also bye")

    delete_item(target)

    assert not target.exists()


# ----------------------------------------------------------------------
# is_image_file
# ----------------------------------------------------------------------

def test_is_image_file_true_for_known_extensions(tmp_path):
    assert is_image_file(tmp_path / "photo.png") is True
    assert is_image_file(tmp_path / "photo.JPG") is True


def test_is_image_file_false_for_other_extensions(tmp_path):
    assert is_image_file(tmp_path / "notes.txt") is False


# ----------------------------------------------------------------------
# is_probably_text_file / read_text_preview
# ----------------------------------------------------------------------

def test_is_probably_text_file_true_for_utf8_text(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello world\n", encoding="utf-8")
    assert is_probably_text_file(path) is True


def test_is_probably_text_file_false_for_binary(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(bytes([0, 1, 2, 255, 254, 0, 0, 0]))
    assert is_probably_text_file(path) is False


def test_read_text_preview_returns_full_content(tmp_path):
    path = tmp_path / "notes.txt"
    path.write_text("hello world")
    assert read_text_preview(path) == "hello world"


def test_read_text_preview_truncates_long_files(tmp_path):
    path = tmp_path / "big.txt"
    path.write_text("x" * 100)

    preview = read_text_preview(path, max_bytes=10)

    assert preview.startswith("x" * 10)
    assert "truncated" in preview
