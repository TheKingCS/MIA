# MIA OS: open questions for Zac

> **Prompt 17 (2026-11-18):** superseded by Prompts 01 to 17 and kept for history only; `MIA_OS_FINAL_MASTER_IMPLEMENTATION_BLUEPRINT.md` governs.

*Claude, 2026-11-13. Each needs Zac's answer before the stage it blocks.
My recommendation is given, but the choice is his.*

## Before stage 1 (the runtime)

1. **Approve the order?** Runtime first, on Windows, before any OS work.
   *Recommend yes: it helps today, and everything else depends on it.*
2. **Should MIA keep running after the window closes on Windows,** started
   at sign-in? *Recommend yes, with a tray icon to stop it.*

## Before stages 2–3

3. **Who is MIA OS for?** Zac alone (DEC-0119), or eventually others
   (DEC-0050, DEC-0127)? This decides signed public images, licensing and
   the installer. *Recommend: build for Zac and keep the product path
   open.*
4. **Grants: how much should be standing?** For example, may MIA close an
   app that's frozen without asking? *Recommend: nothing standing until
   Zac has used the approvals for a while.*
5. **Do spoken approvals count** for act-with-approval actions on the PC?
   *Recommend yes on his own device, never for security settings.*

## Before stage 4–5 (the image)

6. **Fedora (bootc) as the base?** *Recommend yes;* Ubuntu LTS is the
   fallback.
7. **KDE Plasma as the conventional desktop,** or GNOME? *Recommend KDE.*
8. **Dual boot with Windows on its own drive** for how long? Which
   Windows-only things does he still need (games with anti-cheat, Edge
   profiles, Office)?
9. **Boot unlock:** TPM2 plus a PIN, or TPM2 only? *Recommend a PIN.*
10. **Does the PC have a free drive** for MIA OS, or does one need to be
    bought?

## Product questions (no stage blocked yet)

11. **Life Enrichment Protocol:** what is it? Learning paths, Natural
    Momentum and the Loop all touch it; one definition would let it be
    built on the current engine.
12. **Smart Closet:** what should it do (inventory, outfits, laundry,
    weather)? Is there a camera involved?
13. **Shared Conversation Mode:** who talks with MIA together (Zac and a
    guest, the council)? It needs speaker identification, which isn't
    built yet.
14. **Phone:** may MIA become the phone's default assistant, and
    optionally its home screen?
15. **Neural interfaces:** an allowance in the HAL only, for now?

## Facts to check on the PC (Claude can do these from a PC session)

- ROCm or Vulkan performance for qwen2.5:14b on the 7900 XTX under Linux.
- Whether the PC has a TPM2 enabled in the firmware.
- Free disk space and drive layout.
- `git status` for uncommitted edits left from the deleted PC session.
