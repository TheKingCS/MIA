---
id: K-0314
kind: debugging
title: MIA OS needs /boot as its own ext4 partition, or a broken update loops
status: confirmed
by: claude
created: 2026-11-19T20:11:46+00:00
concerns: .github/workflows/mia-os-vm.yml, os/files/boot-stays-mounted.conf, os/files/greenboot/required.d/43-mia-self-test.sh
from: commit:df9f3488, commit:e1af2147, task:FW-04
---
FW-04 (2026-11-19). greenboot caught a deliberately broken update and rebooted to fall back, but with /boot on the Btrfs root GRUB can't write its environment (loadenv.c: 'sparse file not allowed'), so boot_counter never moved and the VM rebooted into the broken version for 25 minutes. With /boot as its own ext4 partition (EFI, BIOS boot, ext4 /boot, Btrfs root; bootc install to-filesystem --boot-mount-spec) greenboot said 'Boot counter exhausted ... initiating rollback', called bootc rollback, and the previous version came back. Also: /boot as an automount lets go when idle and ostree then can't apply a staged update at shutdown; an fstab entry (which to-filesystem writes) or the image's drop-ins fix that.
