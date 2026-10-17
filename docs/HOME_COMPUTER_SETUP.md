# Your home computer as MIA's brain (DEC-0022)

*For the new computer (Ryzen 7 9800X3D, Radeon RX 7900 XTX 24 GB).
When the phone can reach it, Talk uses the computer's bigger model; when
it can't, the phone's own model answers, mid-conversation if needed, and
each reply says which one did (HOME PC or PHONE). Your data stays on
your devices: the phone sends only the conversation turn, and only to
MIA on your own computer, through your own Tailscale network.*

## On the computer (once)

1. **Install MIA**: `docs/SETUP_GUIDE.md` (🪟 Windows: `install.bat`).
2. **Install Ollama for Windows** (ollama.com). It runs on the 7900 XTX
   by itself (AMD ROCm support is built in). Then, in a terminal:
   ```
   ollama pull qwen2.5:14b
   ```
   About 9 GB, fast on your card. (`qwen2.5:32b`, about 19 GB, also fits
   in 24 GB; Claude will compare the two on MIA's own test questions.)
3. **Tell MIA to use it:** in `config/config.json`, under `"llm"`, set
   `"model": "qwen2.5:14b"` (leave `base_url` as `http://localhost:11434`).
4. **Give your profile a password** (MIA → Settings) if it has none.
5. **Turn on Phone Access:** Settings → Phone Access → **Let my phone
   reach MIA**.
6. **Install Tailscale for Windows**, sign in, then in a terminal:
   ```
   tailscale serve --bg http://127.0.0.1:8765
   tailscale serve status
   ```
   Write down the address it prints, like
   `https://your-computer.your-tailnet.ts.net`. Only your own devices
   on your Tailscale account can open it.

## On the phone (once)

1. Install **Tailscale**, sign in with the same account, turn it on.
2. In the MIA app: ⚙ → **Settings** → **Home Computer** → **Link**.
   Put in the address from step 6, your name or email, and your
   password. MIA links and says which model it found.

That's it. In Talk, each answer is marked **HOME PC** or **PHONE**.
**Unlink** (same place) stops it and removes the phone's key from the
computer.

## How it works (for the team)

- The phone links with `/api/model/link` (your own sign-in, never a new
  account) and gets a device key; the computer keeps only its hash
  (`home_link.devices` in its config), so the link survives a restart.
- Each turn, the phone's MIA builds the whole request (facts, memories,
  tools) itself and sends just the model call to `/api/model/chat`; any
  action still runs on the phone, approved there.
- The phone checks the computer at most every 30 seconds, so away from
  home it doesn't wait on it. `core/home_link.py`, `core/llm_manager.py`.
