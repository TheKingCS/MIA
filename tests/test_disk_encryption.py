"""Tests for FW-05's disk encryption pieces (os/files/mia-disk-enrol, the boot image's TPM support, the VM workflow):
the recovery key is made and shown once, the TPM is bound to PCR 7 with a PIN, the install's passphrase is removed,
and the VM checks the three outcomes."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_enrolment_makes_a_recovery_key_binds_the_tpm_with_a_pin_and_drops_the_install_passphrase():
    """The first run makes the recovery key and enrols the TPM and removes nothing; only `finish`, after the
    recovery key has been typed back and checked, wipes the install's passphrase; `again` enrols the TPM afresh."""
    script = (ROOT / "os" / "files" / "mia-disk-enrol").read_text(encoding="utf-8")
    start = script[script.index("\nstart)"):script.index("\nfinish)")]
    finish = script[script.index("\nfinish)"):script.index("\nagain)")]
    again = script[script.index("\nagain)"):]
    assert "--recovery-key" in start and "enrol_tpm" in start and "--wipe-slot" not in start
    assert "tpm2-device=auto" in start  # refuses an install that would never ask for the PIN
    assert finish.index("--test-passphrase") < finish.index("--wipe-slot=password")
    assert "--wipe-slot=tpm2" in again and "--tpm2-pcrs=7 --tpm2-with-pin=yes" in script
    assert "dbx" in script and script.startswith("#!/bin/bash")  # says what else changes PCR 7


def test_the_image_can_open_the_disk_with_the_tpm_at_boot():
    """The boot image is checked for cryptsetup and the TPM's library, and built again only when they're missing."""
    conf = (ROOT / "os" / "files" / "dracut-mia-tpm.conf").read_text(encoding="utf-8")
    assert "tpm2-tss" in conf and "crypt" in conf
    containerfile = (ROOT / "os" / "Containerfile").read_text(encoding="utf-8")
    assert "dracut.conf.d/50-mia-tpm.conf" in containerfile and "dracut --no-hostonly --reproducible" in containerfile
    assert "has systemd-cryptsetup && has libtss2-esys" in containerfile  # checked, built again only when missing


def test_the_vm_checks_the_pin_an_update_without_the_recovery_key_and_secure_boot_off():
    """Secure Boot firmware, a software TPM, and the three acceptance checks."""
    wf = (ROOT / ".github" / "workflows" / "mia-os-encryption.yml").read_text(encoding="utf-8")
    assert "OVMF_CODE_4M.secboot.fd" in wf and "swtpm socket --tpm2" in wf
    assert "1. A boot asks only for the PIN" in wf and "2. After an update the PIN still opens it" in wf
    assert "3. With Secure Boot off the TPM refuses" in wf
    assert "PASSWORD=install-temporary" in wf  # enrolment has no terminal to ask at
    # the PIN alone, before and after the update: neither a recovery-key prompt nor a passphrase one, checked with
    # something that can fail the step (a bare `! grep` can't under bash -e)
    assert wf.count('absent "(recovery key|assphrase) for" /tmp/serial.log') == 2 and "\n          ! " not in wf
    assert "mia-disk-enrol finish" in wf and "A wrong recovery key was accepted" in wf and "mia-disk-enrol again" in wf
    typing = (ROOT / "os" / "poc" / "vm" / "type_at_prompt.sh").read_text(encoding="utf-8")
    assert "/tmp/serial.sock" in typing and "sendkey" not in typing  # typed where the boot's prompt listens
    assert "permissions:\n  contents: read" in wf
