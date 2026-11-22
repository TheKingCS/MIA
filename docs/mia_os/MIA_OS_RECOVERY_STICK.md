# MIA OS: your recovery stick (FW-09, REQ-OPS-002)

*Claude (Opus), 2026-11-22. For Zac. When MIA OS won't start, and the boot menu's previous version and Plasma
don't help either, this stick still reaches a desktop and your files: without MIA, without the computer's own
system, and without the internet.*

## What it is

**Fedora's KDE live stick**, the same one you make for the graphics card test (HW-01): one stick for both. It
starts a full KDE desktop from the USB stick and changes nothing on the computer unless you tell it to. It has
everything needed to open MIA OS's encrypted disk (cryptsetup, Btrfs) built in.

You need: the stick, and **the recovery key** from your sealed envelope (FW-05: the disk's PIN won't work here; the
key will).

## Make it (once, on any computer)

1. Download **Fedora Media Writer** from fedoraproject.org and run it.
2. Choose **Fedora KDE Plasma Desktop**, the same release MIA OS is built on, and your USB stick (8 GB or more;
   it's wiped).
3. Label the stick "MIA recovery" and keep it with the envelope.

## Reach your files

1. Plug the stick in, turn the computer on, and choose the stick in the boot menu (F11 or F12 on most boards;
   the key shows briefly at power-on). With Secure Boot on, it starts as it is: Fedora's stick is signed.
2. Choose **Start Fedora** and wait for the desktop. Don't choose "Install".
3. **The easy way:** open **Dolphin** (the folder icon). On the left, under Devices, the MIA OS drive shows as an
   encrypted volume. Click it, type the recovery key (with its dashes), and it opens. Your files are in
   `home`, then your name.
4. **If Dolphin doesn't show it**, open **Konsole** and type, one line at a time:

   ```
   lsblk -f
   ```

   The MIA OS drive's big partition says `crypto_LUKS` (on most PCs `/dev/nvme0n1p4`; use the name it shows).

   ```
   sudo cryptsetup open /dev/nvme0n1p4 mia
   ```

   Type the recovery key when it asks. Then open your files **read-only**, so nothing can change them:

   ```
   sudo mkdir -p /mnt/mia
   sudo mount -o subvol=home,ro /dev/mapper/mia /mnt/mia
   ls /mnt/mia
   ```

   Your name is there, and your files under it.
5. **Copy what you need** to another drive (your external one): drag in Dolphin, or `cp -r` in Konsole.
6. **Close it when done:** `sudo umount /mnt/mia` and `sudo cryptsetup close mia` (or just shut down).

## What it doesn't do

- It doesn't start MIA, or repair MIA OS: that's the boot menu's previous version, or a reinstall from the image
  with your files kept (the restore guide, `MIA_OS_RESTORE_AND_DISASTER_RECOVERY.md`).
- It can't open the disk without the recovery key. That's on purpose: someone who finds the computer can't either.

## Rehearsed

To check with each release (REQ-OPS-002: "rehearsed once a release"), and once in a VM in CI (the stick's image
booted against an encrypted test disk, the key typed, a test file read). Neither is done yet: the VM rehearsal is
FW-09's remaining step, and the first real rehearsal is with you at MV-01.
