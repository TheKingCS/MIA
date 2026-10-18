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
The phone app can't read RTSP streams yet; still-picture cameras work
there.

## What's next

- Smoother live video (a real stream, not a picture every second).
- Motion alerts through the communication gate.
- Cameras on the glasses.
- Lights, locks and the thermostat through a local Home Assistant
  (`docs/ROADMAP.md`, Smart Home).
