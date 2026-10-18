# Security cameras in MIA (DEC-0033)

MIA's **Security** app shows your cameras live, over your own home
network, with no company cloud in between. It works on the phone and on
the PC, wherever MIA is running on the same network as the cameras.

## Which cameras to get

Get cameras that can be reached **locally**: they give a still picture
or an RTSP video stream on your network. These work out of the box:

| Brand | How MIA reads it | Notes |
|---|---|---|
| **Reolink** | still picture | Easiest. Wired (PoE) models are the most reliable. |
| **Amcrest / Dahua** | still picture | |
| **Hikvision / Annke** | still picture | |
| **Tapo** (TP-Link) | RTSP stream | Make a "camera account" in the Tapo app (Camera Settings → Advanced → Camera Account). Needs ffmpeg where MIA runs. |
| **Wyze** | RTSP stream | Only with Wyze's RTSP firmware. Needs ffmpeg. |
| Anything else with RTSP or a snapshot URL | Other | Type its path. |

**Ring, Nest, Blink and Arlo** only stream through their own cloud, so
MIA can't show them.

## The setup: cameras at home, watched from anywhere

The cameras stay on the **same Wi-Fi as your PC**, and MIA on the PC
talks to them. Your phone reaches the PC through the link you already
use for Talk (Settings → Home Computer, `docs/HOME_COMPUTER_SETUP.md`):

- at home: over the Wi-Fi;
- away (another Wi-Fi, or mobile data): through **Tailscale**, which
  has to be on on both the PC and the phone.

The phone shows the PC's cameras with a **via PC** tag; their pictures
come through the PC. Nothing about the cameras is ever opened to the
internet; only your own devices on your own Tailscale can reach the PC,
and only with your sign-in. If the PC is off or unreachable, Security
says so, and the cameras come back as soon as it answers.

Add cameras from the phone or at the PC: with the home computer linked,
**Add A Camera** on the phone asks where the camera is and defaults to
**On the home computer's Wi-Fi** (MIA saves it on the PC). Saved
pictures from the phone are kept on the phone.

## Adding one

1. Set the camera up with its own app and connect it to your Wi-Fi.
2. Find its address on your network (the camera's app, or your
   router's list of devices): something like `192.168.1.40`. Give it a
   fixed address in your router so it doesn't change.
3. MIA → Security → **Add A Camera**: name, where it is, brand,
   address, the camera's username and password.

MIA only ever talks to addresses inside your home network (it refuses
anything on the internet). The camera's password stays on the device
running MIA (`security_logins.json` in MIA's data folder), is never
shown again, and never goes into the repo.

## Stream-only cameras (RTSP): ffmpeg

On the PC: `winget install ffmpeg` in a terminal, then restart MIA.
Cameras added on the PC's Wi-Fi are read by the PC, so a phone watching
them through the PC never needs ffmpeg itself.

## What's next

- Smoother live video (a real stream, not a picture every second).
- Motion alerts through the communication gate.
- Cameras on the glasses.
- Lights, locks and the thermostat through a local Home Assistant
  (`docs/ROADMAP.md`, Smart Home).
