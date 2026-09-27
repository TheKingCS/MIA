# Setting Up MIA on Your New Computer

One start-to-finish checklist, from a blank computer to everything built
so far: MIA itself, her local AI and voice, the conversation check,
the Private Journal, bank sync, your phone (web app and Android app),
and the Claude Design pass. Written 2026-09-27.

Work top to bottom. Each part ends with a checkbox. You can stop after
any part and pick up later. When something fails, jump to
[Troubleshooting](#troubleshooting) or send Claude the report described
in [Part 11](#part-11-report-back-to-claude).

**Time:** about 1 to 2 hours total, most of it downloads.

---

## Part 0: Before you start

**Which system is on the new computer?**

- **Ubuntu Linux (recommended).** MIA is built and tested on Linux, and
  it's what the Raspberry Pi runs. Every command below is written for
  Ubuntu 22.04 or 24.04.
- **Windows.** MIA is meant to run on Windows during development, but
  Claude hasn't been able to test it there. Look for the **🪟 Windows**
  notes; they replace the Ubuntu command in that step. If anything
  fights you on Windows, the fallback is installing Ubuntu (or dual-
  booting it), which is the long-term home for MIA anyway.

**Have these ready:**

- Your **GitHub** login (the MIA repo is private).
- Your **Android phone**, charged.
- A **password manager** (or a written note kept somewhere safe). You'll
  create up to three secrets today:
  1. **MIA profile password**: logs you in on the phone.
  2. **Vault passphrase**: locks your Plaid bank keys. Can't be recovered.
  3. **Journal passphrase**: locks the Private Journal. Can't be
     recovered. You may use the same one as the vault; then unlocking one
     unlocks both.

**Ground rules:**

- **Never paste a secret into a chat, email or text**: not your Plaid
  secret, a passphrase, a password, or an access token (a long string
  starting with `access-`). Secrets only get typed into MIA's own windows
  on your computer.
- Keep the MIA repo **private**.

- [ ] Ready

---

## Part 1: Install MIA

### 1a. System tools

**Ubuntu:** open a terminal (Ctrl+Alt+T) and run:

```bash
sudo apt update
sudo apt install -y git curl unzip python3 python3-venv python3-pip gh \
    libportaudio2 libegl1 libgl1 libxkbcommon0 libxcb-cursor0 libpulse0
```

(`libportaudio2` is for the microphone and speakers; the `lib…` ones let
the MIA window open.)

> 🪟 **Windows:** install these, accepting the defaults unless noted:
> - **Python 3.12** from python.org. On the first installer screen, tick
>   **"Add python.exe to PATH"**.
> - **Git for Windows** from git-scm.com (it includes **Git Bash**, used
>   once in Part 4).
>
> Then use **PowerShell** for the commands below.

- [ ] System tools installed

### 1b. Sign in to GitHub and download MIA

**Ubuntu:**

```bash
gh auth login
```

Answer: **GitHub.com** → **HTTPS** → **Yes** (authenticate Git) →
**Login with a web browser**. Copy the code it shows, press Enter, and
approve in the browser. Then:

```bash
cd ~
git clone https://github.com/TheKingCS/MIA.git
cd MIA
```

> 🪟 **Windows:** in PowerShell, `cd ~` then `git clone https://github.com/TheKingCS/MIA.git`
> then `cd MIA`. A GitHub sign-in window pops up the first time; sign in there.

- [ ] MIA downloaded into `~/MIA`

### 1c. Install MIA's Python packages

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

This takes a few minutes. Your prompt now starts with `(.venv)`. **Every
time you open a new terminal for MIA**, run `cd ~/MIA` and
`source .venv/bin/activate` first.

> 🪟 **Windows:** `py -m venv .venv`, then `.venv\Scripts\activate`, then
> the two `pip` lines. If PowerShell refuses to run the activate script,
> run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once and try
> again.

- [ ] Packages installed without errors

### 1d. Check the install

```bash
pytest -q
```

It should end with about **3,680 passed**. One known failure,
`test_sun_moon_summary_for_real_coordinates_has_sensible_shape`, is a
time-zone quirk and is fine to ignore. More than that: send Claude the
last 30 lines.

- [ ] Tests pass

---

## Part 2: First launch

```bash
python main.py
```

1. The splash screen, then the **setup wizard**: enter your name and
   confirm the date and time. This creates your profile.
2. Open **Settings → Change Password** and give your profile a password.
   The phone refuses to log in to a profile without one, because it's a
   line into everything MIA knows. Save it in your password manager.
3. Look around. Nothing is connected to the internet yet, and that's
   fine: MIA works offline.

- [ ] MIA opens, profile created, password set

---

## Part 3: MIA's brain (the local AI)

MIA thinks with **Ollama**, which runs the AI model on this computer.

**Ubuntu:**

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

The model is about 2 GB. Ollama then runs in the background by itself,
including after restarts.

> 🪟 **Windows:** download the installer from ollama.com, run it, then in
> PowerShell: `ollama pull llama3.2`.

**Check it:** restart MIA (close it, `python main.py`), open the
**Assistant**, and type *"What can you do?"*. She should answer in a
few seconds (the first answer after a restart is slower while the model
loads).

- [ ] MIA answers in the Assistant

---

## Part 4: MIA's voice at home

Offline speech recognition and MIA's voices (about 350 MB):

**Ubuntu:**

```bash
bash deploy/download_voice_models.sh
```

> 🪟 **Windows:** open **Git Bash** (Start menu), `cd ~/MIA`, and run the
> same `bash deploy/download_voice_models.sh`.

Restart MIA. In **Settings → Voice**, pick a voice and set the volume.
In the Assistant, use **Talk** (push to talk) and ask something; she
should answer out loud.

- [ ] MIA hears you and talks back

---

## Part 5: The live conversation check

This runs about 200 realistic sentences past MIA's AI and checks she
picks the right action for each. It uses fake data in a temporary
folder and never actually changes anything. Ollama must be running.

```bash
python tests/live_model_check.py
```

It takes several minutes and ends with a line like `190/206 passed.`
**Copy every line that starts with `[FAIL]`** and send them to Claude.
Failures here are expected and useful: this is the first time these
cases have met the real model.

- [ ] Ran it and saved the FAIL lines

---

## Part 6: Talk it out (Private Journal and conversation modes)

1. MIA → **Notes** → **🔒 Private Journal** tab → **Set Up…**. Choose
   the **journal passphrase** (8+ characters; you may reuse the vault
   passphrase). Save it: **if it's lost, the journal can't be read by
   anyone, MIA included.**
2. In the Assistant, try:
   - *"I want to journal"*, then talk for a few sentences, then *"I'm done
     journaling"*. Check the entry in the Private Journal tab: title,
     mood, themes, summary, and your own words.
   - *"Just listen"*, *"No bullshit"*, *"Hype me up"*, *"Help me figure out
     what to do"*, then *"Back to normal"*.
   - *"Off the record"*, say something, then *"Back on the record"*. Nothing
     from that stretch should appear in the chat history after a restart.
   - Later: *"What have I been writing about?"*
3. **Tell MIA your why**, one link at a time: *"The reason I work at the
   factory is to pay off my debt"*, then *"Paying off debt is so I can
   control my own time"*, and so on up to what you're really building.
   She reads the chain back each time. Then try *"Remind me why I'm
   doing all this."* Her answer should use only your real numbers.
4. Optional: **Settings → Support & Safety → Trusted person**. If you ever
   tell MIA you're in danger, she gives 988 and 911, and names this person
   too.

Each time MIA starts, the journal is locked: she can still **save** to it,
but reading needs **Unlock…** in the Private Journal tab.

- [ ] Journal set up and a test entry saved
- [ ] Your why told to MIA, and "remind me why" tried

**How often MIA messages you on her own:** at most 5 a day, merged
into one message when several come up together, and never while you're
venting or journaling. Change the number in **Settings → When MIA Speaks
Up**, and ask her *"what didn't you tell me today?"* any time.

---

## Part 7: Connect your banks (Plaid)

Full detail is in **`docs/PLAID_SETUP.md`**. The short version:

**Test with fake banks first (sandbox).** This can't use up any of your
10 real connections.

1. **dashboard.plaid.com → Developers → Keys**: copy your **client_id**
   and your **Sandbox** secret.
2. MIA → **Budget → Bank Sync → Set Up Plaid…**: paste both, choose
   **sandbox**, and create the **vault passphrase**.
3. **Connect a Bank…** → any bank → username **`user_good`**, password
   **`pass_good`** (code **`1234`** if asked) → select all accounts →
   back in MIA, enter the passphrase to save the connection.
4. **Sync Now** (passphrase again). Check **Expenses**, **Income** and
   **Debts**. Sync a second time and confirm nothing appears twice.
5. **Tell Claude how it went** (Part 11). This is the first time MIA's
   bank code has talked to the real Plaid service.

**Then your real accounts** (`docs/PLAID_SETUP.md`, Part 6): **Reset Plaid
Setup…** (leave "also delete data imported from Plaid" ticked; it
clears the fake data) → **Set Up Plaid…** with your **Production** secret
and **production** → **Connect a Bank…** with your real logins. Each
bank login uses one of your 10 connections. Then add promo-APR end
dates by hand on the Debts tab.

- [ ] Sandbox test done and reported
- [ ] Real accounts connected

---

## Part 8: Reach MIA from your phone (Tailscale)

Your phone reaches MIA at home through **Tailscale**, a free private
network between your own devices. Full detail:
**`docs/PHONE_VOICE_SETUP.md`**.

**On the computer:**

1. Install and sign in:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   Open the link it prints and sign in (Google works). Use the **same
   account** on your phone.
   > 🪟 **Windows:** install Tailscale from tailscale.com/download and
   > sign in from its tray icon.
2. In a browser: **login.tailscale.com → DNS** → make sure **MagicDNS** is
   on → **Enable HTTPS**.
3. Turn on MIA's phone server: open `config/config.json` in the MIA
   folder (it exists after the first launch) and make its `"server"`
   section say:
   ```json
   "server": {
       "enabled": true,
       "host": "127.0.0.1",
       "port": 8765
   }
   ```
   Keep the commas valid. Restart MIA.
4. Publish MIA on your Tailscale network over https:
   ```bash
   sudo tailscale serve --bg http://127.0.0.1:8765
   tailscale serve status
   ```
   > 🪟 **Windows:** same two commands in PowerShell **run as
   > administrator**, without `sudo`.

   `status` prints your MIA address, like
   `https://your-computer.your-tailnet.ts.net`. **Write it down.**

**On the phone:**

5. Install **Tailscale** from the Play Store, sign in with the same
   account, and turn it on.
6. Open your MIA address in **Chrome** and log in with your profile name
   and password. Tap the orb, allow the microphone, and say *"What's on my
   schedule today?"*.

- [ ] MIA answers on the phone (web app)

---

## Part 9: The Android app (hands-free, phone locked)

The web app needs the screen on. The app doesn't. Full detail:
**`android/README.md`**.

1. On the phone, in Chrome, signed in to GitHub:
   **https://github.com/TheKingCS/MIA/releases/tag/android-latest**
2. Tap **MIA-Companion.apk**, open the download, allow **install unknown
   apps** for Chrome once, go back, and tap **Install**.
3. Open **MIA**, sign in with the same address, name and password.
4. Tap **Start hands-free**, allow the **microphone** and
   **notifications**, then tap **Let MIA run in the background**.
5. Lock the phone and talk through your headphones. A short beep means
   she heard you. Try your **headset button** (pause/resume) and saying
   *"goodbye"*.
6. Optional: tick **Use my Bluetooth headset's microphone** and compare.

Updates: install the newest APK from the same page; it keeps your
sign-in.

- [ ] Hands-free works with the phone locked

---

## Part 10: The Claude Design pass

1. Get the design package: the `docs/design_handoff/` folder on your
   computer (or the zip Claude sent earlier), plus the inspiration
   pictures you picked.
2. Open **Claude Design**, upload the package and the pictures, and
   paste the prompt from section 0 of `docs/design_handoff/README.md`.
3. Bring the 3 design directions back to Claude. The one you choose
   becomes MIA's new look.

- [ ] Design directions ready

---

## Part 11: Report back to Claude

Start a new Claude session on the MIA repo and say *"read
docs/NEXT_SESSION.md"*. Then send, for each part you did:

- **Worked / didn't work**, and anything confusing.
- The **exact error text** and which Part and step.
- For errors, the **last ~30 lines of the newest file in `logs/`**.
- From Part 5: the **`[FAIL]` lines**.
- From the phone: whether it heard you over road noise, how long answers
  took, and whether the headset button and locked-screen listening worked.

**Before sending, check for secrets:** no Plaid secret, passphrase,
password or `access-…` token.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `pip install` fails building a package | Check `python3 --version` (3.11 or 3.12 is what MIA is tested with; Ubuntu 24.04's 3.12 is fine) and that the `.venv` is active |
| MIA won't open; error mentions a missing `.so` file (`libEGL`, `libxcb-cursor`, `libpulse`) | Re-run the `sudo apt install` line in Part 1a |
| 🪟 PowerShell won't run `activate` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again |
| Assistant says it can't think / model unavailable | Ollama isn't running or the model isn't pulled: `ollama list` should show `llama3.2`. On Ubuntu: `systemctl status ollama` |
| MIA doesn't talk or hear | Voice models missing (Part 4), or no mic/speaker selected in the system's sound settings |
| `git pull` refuses because of local changes | Stop and ask Claude before forcing anything |
| Phone page won't load | Tailscale off on the phone or computer, MIA not running, or `server.enabled` isn't `true` (then restart MIA) |
| Phone says "Set a password for this profile…" | Part 2, step 2 |
| Phone says "Open MIA through its https:// Tailscale address" | Use the `https://…ts.net` address from Part 8 step 4, not `http://` |
| Android app: "Can't reach MIA at home" | Tailscale off on the phone, or MIA/the computer is off |
| Android app stops when the screen is off | Part 9 step 4, the background (battery) permission |
| Forgot the journal or vault passphrase | Can't be recovered. Vault: delete `data/plaid_vault.enc` and set Plaid up again. Journal: ask Claude how to start a fresh one |

**Getting future updates:** `cd ~/MIA`, activate the `.venv`, then
`git pull` and `pip install -r requirements.txt`, and restart MIA.
