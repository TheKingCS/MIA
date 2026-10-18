# The Memory Vault (DEC-0030 phase E)

*Your phone's photos and videos, kept safe on your home computer, so the
phone can let them go. Built 2026-10-18 (`core/memory_vault.py`).*

## For you

1. Link the phone to your home computer first (Settings → Home Computer,
   `docs/HOME_COMPUTER_SETUP.md`).
2. On the phone: **Apps → Memory Vault → Turn On The Vault**. Android asks
   to let MIA see your photos and videos: allow all of them.
3. That's it. Every minute or so, while MIA is running, it looks for new
   photos and copies them to the computer, **on Wi-Fi only** unless you
   switch that off (Set Up). The strip says how many are safe on the PC
   and how many are waiting.

**Freeing space is always your call.** MIA never deletes anything.

- **Free Up Space** offers photos and videos older than 30 days (Set Up
  changes that) that are on the computer. When you press it, the computer
  first reads each of those files again. MIA offers only the ones it
  confirms. Then **Android asks you** and moves them to its **Trash**,
  where they stay for 30 days.
- **Exact Copies:** the same photo saved twice on the phone. One copy
  stays.
- **Bursts:** photos taken seconds apart. ★ marks the best one: the
  sharpest and best lit once the computer has looked at them, otherwise
  the most detailed. It's only a suggestion. "Keep The Best" frees the
  others, after the same check as above.

A freed photo stays in the vault. Open it from the Photos tab and it
comes from the computer. Each day shows what you did that day and the
trip it was on. The Chronicle counts each week's photos.

On the computer they're in your MIA folder:
`data\profiles\<your id>\vault\<year>\<month>\`, named by date. You can
back that folder up like any other.

## How it works (for the team)

- **The phone (`MemoryVault`, a personal store, `memory_vault.json`).**
  `scan()` walks the camera roll (DCIM, Pictures and Movies on Android;
  `vault.sources` in the config elsewhere). It skips hidden folders such
  as `.thumbnails` and `.trashed-*`. Each new or changed file gets a
  fingerprint (SHA-256), up to 400 MB a round so a big roll doesn't
  stall the phone. The date comes from EXIF DateTimeOriginal, else the
  file name (`IMG_20261018_101530`), else the file's time. GPS comes from
  EXIF; Android needs ACCESS_MEDIA_LOCATION to leave it in. The same
  fingerprint in two places is one memory with two copies.
- **Sending (`send`, `VaultLoop`, every 60 s).** The phone asks the PC
  which fingerprints it already has (`/api/vault/have`), so sending again
  does nothing. The rest go oldest first in 8 MB pieces
  (`PUT /api/vault/blob/<sha>?offset=`). A cut transfer carries on from
  the PC's `.part` size. The PC checks the whole file's fingerprint before
  keeping it (`VaultShelf.receive`), and a damaged file is thrown away
  and sent again. On mobile data (Android says "metered") it waits,
  unless `vault.wifi_only` is off.
- **Freeing (`free_plan`, `note_freed`).** For anything that isn't an
  exact copy, `/api/vault/verify` re-reads each file on the PC right
  then. Only the confirmed ones are passed to the phone app's bridge
  (`window.MIAAndroid.trash`, `android-phone/.../Gallery.kt`), which uses
  `MediaStore.createTrashRequest` (Android 11+). Android shows its own
  dialog. Afterwards the store forgets only the files that are really
  gone.
- **Best shot.** `/api/vault/scores` on the PC scores sharpness (edge
  variance) and exposure (mean brightness, clipping) with Pillow. Without
  Pillow, the largest file wins.
- **Previews.** The phone serves the photo's own EXIF preview, never the
  full picture, for a tile. The PC makes one with Pillow. A freed photo
  is fetched from the PC (`/api/vault/blob/<sha>?thumb=1`).
- **Not synced.** `memory_vault.json` stays on the phone (`NEVER_SYNC`).
  The vault folder on the PC isn't one of sync's folders, so freeing
  space on the phone never deletes anything on the PC.
- **Grown-ups only.** It isn't in `CHILD_APPS`, and the PC's endpoints
  refuse a child's account.

**Not yet:** copying while MIA is closed (that needs an Android
foreground service), near-duplicates that aren't bursts, search,
captions from a vision model on the PC, and a second backup of the
vault.
