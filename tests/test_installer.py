"""
MIA's installer (2026-10-01): install.sh (Linux, Raspberry Pi),
install.ps1 / install.bat (Windows), and the shared finishing step
deploy/finish_install.py.
"""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "deploy"))

import finish_install  # noqa: E402


LINUX_ONLY = pytest.mark.skipif(sys.platform == "win32", reason="the Linux installer and app menu; Windows uses install.ps1")


@LINUX_ONLY
def test_install_sh_is_valid_and_its_dry_run_changes_nothing(tmp_path):
    assert subprocess.run(["bash", "-n", str(ROOT / "install.sh")]).returncode == 0
    before = sorted(p.name for p in ROOT.iterdir())
    result = subprocess.run(["bash", str(ROOT / "install.sh"), "--dry-run", "--no-system"],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr
    for step in ("1/5 System tools", "2/5 MIA's brain", "3/5 MIA's Python packages", "4/5 Voice", "5/5 Start at boot"):
        assert step in result.stdout
    assert "would run: .venv/bin/python -m pip install -r requirements.txt" in result.stdout
    assert sorted(p.name for p in ROOT.iterdir()) == before
    bad = subprocess.run(["bash", str(ROOT / "install.sh"), "--nonsense"], capture_output=True, text=True)
    assert bad.returncode == 2 and "Unknown option" in bad.stdout


def test_windows_installer_files():
    bat = (ROOT / "install.bat").read_bytes()
    assert b"\r\n" in bat and b"install.ps1" in bat and b"ExecutionPolicy Bypass" in bat
    ps1 = (ROOT / "install.ps1").read_text()
    for piece in ("Python.Python.3.12", "Ollama.Ollama", "UB-Mannheim.TesseractOCR", "requirements.txt",
                  "finish_install.py", "--no-shortcut", "mia_icon.ico", "MIA.lnk"):
        assert piece in ps1
    assert (ROOT / "assets" / "mia_icon.ico").exists() and (ROOT / "assets" / "mia_icon.png").exists()


def test_voice_downloads_list_only_whats_missing(tmp_path):
    from core.voice_catalog import VOICE_CATALOG

    todo = finish_install.voice_downloads(tmp_path)
    assert todo[0] == (finish_install.VOSK_URL, tmp_path / finish_install.VOSK_MODEL)
    assert len(todo) == 1 + 2 * len(VOICE_CATALOG)
    (tmp_path / finish_install.VOSK_MODEL).mkdir()
    assert finish_install.voice_downloads(tmp_path)[0][0] == finish_install.VOSK_URL  # empty folder: still needed
    (tmp_path / finish_install.VOSK_MODEL / "am").mkdir()
    for voice in VOICE_CATALOG.values():
        (tmp_path / f"{voice.voice_id}.onnx").write_text("x")
        (tmp_path / f"{voice.voice_id}.onnx.json").write_text("x")
    assert finish_install.voice_downloads(tmp_path) == []


@LINUX_ONLY
def test_shortcut_goes_to_the_app_menu_and_an_existing_desktop(tmp_path):
    entry = finish_install.desktop_entry(ROOT)
    assert "Name=MIA" in entry and f'"{ROOT / ".venv" / "bin" / "python"}" "{ROOT / "main.py"}"' in entry
    assert f"Icon={ROOT / 'assets' / 'mia_icon.png'}" in entry
    written = finish_install.install_shortcut(ROOT, tmp_path)
    assert written == [tmp_path / ".local/share/applications/mia.desktop"]  # no Desktop folder: none made
    (tmp_path / "Desktop").mkdir()
    assert len(finish_install.install_shortcut(ROOT, tmp_path)) == 2


def test_model_is_skipped_kindly_without_ollama(capsys, monkeypatch):
    monkeypatch.setattr(finish_install.shutil, "which", lambda name: None)
    assert finish_install.install_model() is False
    assert "Ollama isn't installed" in capsys.readouterr().out


def test_the_check_prints_what_to_do(capsys, monkeypatch):
    import core.system_check as system_check

    monkeypatch.setattr(system_check, "_ollama_models", lambda url, timeout=3.0: None)
    code = finish_install.main(["--check-only"])
    out = capsys.readouterr().out
    assert "MIA setup check:" in out and "[!!] Assistant's model" in out and "installer" in out
    assert code == 1


def test_a_failed_download_doesnt_stop_the_install(tmp_path, monkeypatch, capsys):
    def offline(url, target):
        raise OSError("no network")

    monkeypatch.setattr(finish_install, "_download", offline)
    assert finish_install.install_voice(tmp_path) is False
    out = capsys.readouterr().out
    assert out.count("Couldn't download") == len(finish_install.voice_downloads(tmp_path))
    assert not list(tmp_path.glob("*.part"))
