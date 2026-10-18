# PC day: your home computer as MIA's home base (DEC-0022, DEC-0033)

*For the new computer (Ryzen 7 9800X3D, Radeon RX 7900 XTX 24 GB).
Once this is done, the phone (and the glasses) use the computer's bigger
model whenever they can reach it, from home or anywhere through
Tailscale, and the phone's own model when they can't. The cameras live
on the computer's Wi-Fi and you watch them from the phone. Your data
stays on your devices.*

**Time:** about an hour, most of it downloads. Two scripts do almost all
of it; this page is the order.

## 1. The computer itself (15 minutes)

- [ ] Plug in the Cat 8 cable, sign in to Windows, and run **Windows
      Update** until it says you're up to date.
- [ ] Update the **AMD graphics driver** (AMD Software: Adrenalin
      Edition, from amd.com, or the AMD app if it's already there). Ollama
      uses the Radeon through this driver; an old one makes it fall back
      to the much slower processor.
- [ ] Install **Git for Windows** (git-scm.com, the defaults are fine).

## 2. MIA (20 minutes)

In **PowerShell** (Start → type PowerShell):

```
cd ~
git clone https://github.com/TheKingCS/MIA.git
```

GitHub asks you to sign in the first time (it's your private repo).
Then in File Explorer open the new **MIA** folder and double-click
**install.bat**. It installs Python, Ollama, Tesseract, MIA's packages
and the voices, makes a MIA shortcut, and ends with a setup check.

- [ ] Open MIA from the shortcut and **sign in** (or make your account).
- [ ] **Settings → Change Password** if your account has none. The
      phone links with it.

## 3. The home base (30 minutes, mostly downloads)

In the MIA folder, double-click **setup_home_pc.bat**. It asks before
each step:

1. the brain: Ollama with **qwen2.5:14b** (and qwen2.5:32b to compare);
2. MIA's settings: that model, and Phone Access on (it only listens on
   this computer itself; the phone comes in through Tailscale);
3. **ffmpeg** (only for Tapo / Wyze cameras);
4. **Tailscale**: a browser opens to sign in, then it serves MIA to
   your own devices only, and prints **the phone's address for MIA**,
   like `https://your-pc.your-tailnet.ts.net` (also saved in
   `pc-check\tailscale.txt`);
5. MIA **starts when you sign in** to Windows, and the computer **doesn't
   sleep** while plugged in, so the phone and the cameras always find it;
6. the **model comparison** (optional, 30-60 minutes): MIA's own test
   questions on each model, on your graphics card. It recommends one and
   offers to switch, and the results go in `pc-check\models.md`;
7. the **readiness check**: every line `[ok]`, or exactly what to do.

Then **close and reopen MIA** (so Phone Access starts).

Run the check again any time: `.venv\Scripts\python tools\pc_check.py`.

## 4. The phone (5 minutes)

- [ ] Install **Tailscale** from the Play Store, sign in with the **same
      account**, and turn it on.
- [ ] MIA app: ⚙ → **Settings** → **Home Computer** → **Link**. Put in the
      address from step 3, your name or email, and your password. MIA
      says which model it found.
- [ ] Ask Talk something. The answer is marked **HOME PC**.

## What the link does (once it's set)

- **Talk** uses the computer's bigger model (HOME PC), and the phone's
  own when it can't reach it.
- **Everything stays in step:** a change on the phone or the computer
  (missions, the kitchen, money, quests, the journal, your XP and
  credits) shows up on the other one, by itself, about every 15 seconds
  after a change while they can reach each other. Settings → Home
  Computer says when it last synced; **Sync Now** does it right away.
- **Heavy jobs:** the computer reads photos and receipts, hears you, and
  speaks for MIA whenever the phone can't do it itself.

## 5. Tell Claude

Say "the PC is up", and either paste `pc-check\models.md` or just say
the comparison ran. Claude then picks the model (DEC-0022), and goes on
to the next steps: heavy jobs on the PC (voice, reading photos, email,
bank sync), then two-way sync between the phone and the PC.

## Cameras (when you have them)

Put them on the **computer's Wi-Fi**, then from the phone: **Security →
Add A Camera** → "On the home computer's Wi-Fi" (`docs/SECURITY_CAMERAS.md`).

## Updating MIA on the PC later

In PowerShell, in the MIA folder: `git pull`, then double-click
**install.bat** again (it only adds what's new).

## How it works (for the team)

- The phone links with `/api/model/link` (your own sign-in, never a new
  account) and gets a device key; the computer keeps only its hash
  (`home_link.devices` in its config), so the link survives a restart.
- Each turn, the phone's MIA builds the whole request (facts, memories,
  tools) itself and sends just the model call to `/api/model/chat`; any
  action still runs on the phone, approved there. The same link reaches
  the PC's cameras (`core/home_link.home_call`).
- MIA's server listens on 127.0.0.1 only; `tailscale serve` is the only
  way in, and only for devices on your tailnet.
- The phone checks the computer at most every 30 seconds, so away from
  home it doesn't wait on it. `core/home_link.py`, `core/llm_manager.py`.
- Two-way sync (`core/sync.py`): the phone drives it, the PC answers
  `/api/sync/*` with the person's link key. Two folders, matched by
  meaning (the phone's account and the PC's have different ids): the
  person's own and their household's, every JSON data file directly in
  them except device-only ones (`NEVER_SYNC`: camera logins, logs, the
  private journal for now). The phone keeps each file as of the last
  sync (`data/.sync/`): changed on one side, that side wins; on both, a
  three-way merge by record id, field by field, the newer file winning a
  field both changed; the history merges line by line; XP and credits
  add what each side earned. The PC only takes a file that's still the
  version the phone saw (409 otherwise). Not yet: photos and other files
  in subfolders, conversations, the private journal.
- Heavy jobs (`core/heavy_jobs.py`, `/api/heavy/ocr|transcribe|speak`):
  the phone's own engine first, the PC when it has none; after a
  failure the PC isn't asked for a minute.
- The kit: `setup_home_pc.ps1` (CI dry-runs it on Windows every push),
  `tools/pc_check.py`, `tools/pc_model_check.py`.
