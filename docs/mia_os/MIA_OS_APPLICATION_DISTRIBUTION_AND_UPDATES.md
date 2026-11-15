# MIA OS: packaging, distribution and updates (Prompt 03 §11)

*Approved with Zac's clarification (DEC-0177): MIA is a first-class part of the OS image, the primary operating
environment, not an app; her native apps are managed by the MIA Runtime's registry and never depend on Flatpak;
Flatpak is for conventional Linux software, alongside the distribution's other package mechanisms. Coexistence:
[MIA_OS_APPLICATION_REGISTRY.md](MIA_OS_APPLICATION_REGISTRY.md) section G.*

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).
DEC-0177 proposed. Research in MIA_OS_APPLICATION_TECHNOLOGY_EVALUATION.md.*

## 1. Recommendation: three channels, no new package manager

| What | Packaged as | Comes from | Updates | Rollback |
|---|---|---|---|---|
| MIA itself and her first-party apps | part of the OS image on the PC (bootc, DEC-0157); the runtime service on the Pi (`deploy/install_runtime.sh`) | Zac's own image build (signed with cosign) | a new image; or a merged lab branch, reviewed (Fable) | the image's previous deployment; git |
| Ordinary GUI apps | Flatpak | Flathub (repository signed with GPG) | Flatpak | Flatpak's previous commit |
| MIA extensions (when the host exists) | a signed bundle: manifest + code + its sandbox profile | Zac's own builds and the lab | the extension host, on approval | the previous bundle, kept |

Not chosen: AppImage (no sandbox, no update channel), raw RPMs layered on the image (Fedora's own guidance is to
layer sparingly), a MIA app store (DEC-0119). Android apps stay on the phone's Android.

## 2. Requirements met by the channels

Discovery (Apps for MIA's; GNOME Software/Discover or Flathub for GUI apps), metadata (the manifest; AppStream for
Flatpaks), verification (cosign for the image, GPG for Flatpak repos, Zac's key for extensions), dependencies (the
image; Flatpak runtimes; extensions declare a contract version), versions and updates (each channel's own), automatic
updates (the image on a schedule with a notice; Flatpaks the same; extensions never automatically), offline
installation (a local Flatpak bundle or an image from a USB stick), third-party sources (Flathub only by default;
others added by Zac).

## 3. Installing by asking

"Find me a CAD app and install it": MIA searches Flathub's metadata, explains the app, its source and its Flatpak
permissions in plain words, and proposes the install as an action; on Zac's yes the System Manager helper (DEC-0158)
runs `flatpak install` with fixed arguments. Never a shell command written by a model (prompt §11).

## 4. Official, trusted, community, local

Official: MIA's own (in the image). Trusted: Flathub's verified apps, extensions signed by Zac. Community: unverified
Flathub apps (shown as such). Local: built in the lab, merged on approval (they become official).
