# Talking to MIA From Your Phone

Put in headphones, tap once, and hold a hands-free conversation with
the full MIA running on your computer at home, over Wi-Fi or cellular.
Written 2026-09-27 for the first version (a phone web app).

**How it works:** your phone records you, detects when you stop
talking, and sends the audio through **Tailscale** (a free, private,
encrypted network between your own devices) to MIA at home. MIA
transcribes it offline, thinks, takes actions (add a mission, check
your schedule, look things up), and sends her spoken reply back to your
headphones. Nothing goes through anyone else's cloud except Tailscale's
encrypted connection.

---

## What works in this first version (and what doesn't yet)

**Works:**
- Tap once, then talk back and forth hands-free. MIA starts listening
  again after each answer.
- Wi-Fi and cellular, anywhere your phone has a signal.
- Headphones and Bluetooth, through your phone's normal audio.
- The screen stays awake during a conversation.
- Say **"goodbye"**, **"stop listening"** or **"that's all"** to end it.
- You can also type to MIA from the same screen.

**Not yet (fixed by the native app, the next phase):**
- **The screen must stay on with MIA open.** If you lock the phone or
  switch apps, the phone cuts off the microphone. That's a rule phones
  apply to web apps. Mount the phone and leave MIA on screen.
- Your headphones' play/pause button may or may not start or stop a
  conversation, depending on the phone.
- Phone conversations aren't saved to the desktop's chat History yet.
  Things MIA *does* (missions, notes, events) are saved normally.

**Safety:** this is built to be used without looking at the screen.
Start the conversation before you pull out, and keep your eyes on the
road.

---

## One-time setup

### A. On your computer at home

1. **Install Tailscale** and sign in:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
   A sign-in link appears. Open it and log in (a Google or Apple
   account works). Use this **same account** on your phone.

2. **Turn on HTTPS for your Tailscale network.** Your phone only allows
   the microphone on secure (https) pages. In a browser, go to
   **login.tailscale.com → DNS**. Make sure **MagicDNS** is on, then
   click **Enable HTTPS** (under "HTTPS Certificates").

3. **Give your MIA profile a password**, if it doesn't have one:
   MIA → Settings → change password. The phone login refuses profiles
   without a password, since this is a line into everything MIA knows.

4. **Turn on MIA's phone server.** Open `config/config.json` in your
   MIA folder and add (or edit) this section, keeping the commas valid:
   ```json
   "server": {
       "enabled": true,
       "host": "127.0.0.1",
       "port": 8765
   }
   ```
   Then restart MIA. `127.0.0.1` means only this computer can reach
   the server directly; your phone gets in through Tailscale in the next
   step.

5. **Publish MIA to your Tailscale network over https:**
   ```bash
   sudo tailscale serve --bg http://127.0.0.1:8765
   tailscale serve status
   ```
   `status` prints your MIA address, something like
   `https://your-computer.your-tailnet.ts.net`. **Write it down.** Only
   devices signed in to your Tailscale account can open it. `--bg`
   keeps it running after reboots.

6. **Make sure MIA's brain is running:** Ollama (the local AI model)
   should be running, as it is for the desktop Assistant.

### B. On your phone

1. Install **Tailscale** from the App Store or Play Store. Sign in with
   the same account and turn it **on**.
2. Open your MIA address (from step A5) in Safari (iPhone) or Chrome
   (Android).
3. Log in with your MIA profile name and password.
4. **Add it to your Home Screen**: Share → "Add to Home Screen" on
   iPhone, or ⋮ → "Add to Home screen" / "Install app" on Android. Now
   it opens like an app.
5. The first time you tap the orb, allow **microphone** access.
6. Optional: under "Notifications & settings", tap **Enable
   notifications** so MIA's reminders reach your phone.

---

## Daily use: the drive home

1. Put in your headphones. Make sure Tailscale is on (it usually stays
   on).
2. Open MIA from your Home Screen and tap the orb.
3. Talk normally. When you pause, MIA answers in your ears and then
   listens again.
4. Say "goodbye" when you're done, or tap **End conversation**.

**New topic** clears the conversation's short-term memory so MIA
doesn't mix subjects. Long-term things she's learned about you are
kept.

---

## If something's wrong

| What you see | Fix |
|---|---|
| "Open MIA through its https:// Tailscale address" | You opened `http://`. Use the `https://…ts.net` address from step A5 |
| "Microphone blocked" | Allow the microphone for this site in your phone's browser settings |
| Page won't load | Tailscale is off on the phone or computer, MIA isn't running, or `server.enabled` isn't `true` |
| "Your session expired" | MIA restarted. Log in again |
| "Not available on MIA's computer right now: …" | That piece (speech models or Ollama) isn't running at home |
| "Set a password for this profile…" | Do step A3 |
| MIA keeps hearing background noise | Use headphones with a mic, or turn off Hands-free and tap to talk each time |

When reporting a problem to Claude, send the message you saw plus the
last lines of the newest file in MIA's `logs/` folder. Never send
passwords.
