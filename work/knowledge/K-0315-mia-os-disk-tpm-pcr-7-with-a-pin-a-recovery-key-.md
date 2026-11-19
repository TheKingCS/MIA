---
id: K-0315
kind: implementation
title: MIA OS disk: TPM (PCR 7) with a PIN, a recovery key, enrolled after install
status: confirmed
by: claude
created: 2026-11-19T20:11:46+00:00
concerns: os/files/mia-disk-enrol, .github/workflows/mia-os-encryption.yml
from: commit:9a4d798b, commit:ceaf2ca0, dec:DEC-0277, task:FW-05
---
FW-05 (2026-11-19). The install uses a temporary passphrase (LUKS2 root, kargs rd.luks.uuid and rd.luks.options=tpm2-device=auto); os/files/mia-disk-enrol then runs systemd-cryptenroll three times: --recovery-key (shown once), --tpm2-device=auto --tpm2-pcrs=7 --tpm2-with-pin=yes, --wipe-slot=password. With no terminal it needs PASSWORD (the current passphrase) and NEWPIN in the environment, or it hangs. Fedora's own initramfs already has cryptsetup and libtss2, so nothing is rebuilt. What the boot shows: 'Please enter LUKS2 token PIN' and nothing else under Secure Boot, before and after an update; with Secure Boot off the PIN is asked first, the TPM refuses, then 'Please enter recovery key for disk root'.
