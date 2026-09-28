# MIA Companion (Android app)

Hands-free MIA **with your phone locked**: talk through your headphones,
and MIA at home hears you, acts, and answers in your ears. The phone web
app (`docs/PHONE_VOICE_SETUP.md`) needs the screen on; this app doesn't.

It talks to the same MIA server as the web app, over Tailscale, so do
the "On your computer at home" part of `docs/PHONE_VOICE_SETUP.md`
first (Tailscale, a profile password, `server.enabled`).

## Install (no Android Studio needed)

1. On your phone, open the GitHub page for the MIA repo (signed in to
   GitHub in the browser) → **Releases** → **MIA Companion (Android)**.
   Direct link: `https://github.com/TheKingCS/MIA/releases/tag/android-latest`
2. Tap **MIA-Companion.apk** to download it, then open it.
3. Android asks whether your browser may **install unknown apps**:
   allow it once, go back, and tap **Install**.
4. Open **MIA**, sign in with your MIA address (the `https://…ts.net`
   one), your profile name and password.
5. Tap **Start hands-free** and allow the **microphone** and
   **notifications**.
6. Tap **Let MIA run in the background** and allow it, so Android
   doesn't put MIA to sleep while you're driving.

**Updating:** download and install the newest release the same way.
It installs over the old one and keeps your sign-in.

## Using it

- A notification, **MIA · Listening**, shows while she's on. It has
  **Pause** and **Stop**.
- Talk normally. A short beep means she heard you; then she answers.
- **Headset button** (play/pause) pauses and resumes listening. On most
  phones this works with the screen locked.
- Say **"goodbye"**, "stop listening" or "that's all" and she pauses
  after answering. Press the headset button to start again.
- **Bluetooth headset mic:** tick "Use my Bluetooth headset's
  microphone" to talk through the headset instead of the phone's mic
  (better in a pocket or a car; the sound is phone-call quality).
- You can also type to MIA from the app.
- **Show money** opens a read-only money summary: this month, bills and
  paydays coming up, budget targets, debts in payoff order, net worth,
  builds and tools. Same numbers as the desktop.
- **Share to MIA:** in any app (Gmail, Files, Photos), Share →
  **MIA inbox** sends the file (or several) to MIA's document inbox at
  home: receipts, manuals, warranties. Shared text works too.
- If MIA at home restarted, the app signs in again by itself. Your
  password is kept encrypted in Android's secure key storage.

## Not yet

- Replies arrive all at once, not word by word.
- (Phone conversations now appear in the desktop's History, titled
  "📱 …". Each answer's log line ends with how long hearing, thinking and
  speaking took; send those to Claude if replies feel slow.)
- After a phone restart, open the app and tap Start again (Android
  doesn't let a microphone app start itself in the background).

## For developers

- Plain Kotlin, no third-party libraries. UI is built in code, no XML
  resources. `VoiceCore.kt` (speech detection, WAV) is pure Kotlin and
  unit-tested; it's a straight port of `server/static/voice.js`.
- Built by `.github/workflows/android.yml` on every push that touches
  `android/`, and published as the `android-latest` release.
- `mia-companion.keystore` is committed on purpose: Android only
  installs an update signed with the same key, and a new CI key per
  build would force an uninstall every time. It's a personal signing
  key for a sideloaded app in a private repo, not a Play Store key.
- Claude's cloud workspace can't reach Google's Android SDK host, so
  there the sources are type-checked against Robolectric's Android 14
  framework jar (from Maven Central) and the unit tests run on the JVM;
  the real APK is built by GitHub Actions.
