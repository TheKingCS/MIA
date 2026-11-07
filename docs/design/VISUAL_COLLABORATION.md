# Visual collaboration: ChatGPT, Muse, Claude Code, Codex

*Claude, 2026-11-07, for H-0087 (the Experience Maturity handoff). A **proposal**: Zac approves it (or changes it)
before it's the way we work. What's in `docs/design/visual_library/` now is only the empty structure and the
manifest, so concepts have somewhere to land.*

## 1. Who does what

| Role | Who | Makes | Hands to |
|---|---|---|---|
| Visual concept designer | **ChatGPT** (image generation in the ChatGPT app) | Concept art: identity, atmosphere, the orb, app moods, whole-screen concepts | Zac, then the library |
| Interface designer | **Muse / Claude Design** | Real screens from approved concepts: layouts, components, annotated mockups, specs | Claude Code, through `docs/design/applications/` and the design system |
| Engineering | **Claude Code** | Tokens, components, pages; what the architecture allows; what it costs | Codex for review; Zac for acceptance |
| Independent review | **Codex / ChatGPT** | Comparison of the built screen with the approved spec; regressions | Claude Code, Zac |
| Decides | **Zac** | Approves directions, concepts, specs and every merge | everyone |

## 2. What can and can't be connected (checked, not assumed)

- **The ChatGPT app's image generation can't be called by Claude.** It's a consumer feature inside ChatGPT, not an
  API Claude Code has. Images from it reach MIA only when a person moves them (download, then upload to the repo).
- **The OpenAI Images API** is a separate, paid, programmatic service (it needs an API key from Zac's OpenAI
  developer account, billed per image). It could be wrapped as a small tool in MIA's development environment
  (`tools/concept_image.py`, prompt in, image and its prompt saved to the library). Conditions if Zac wants it:
  the key in MIA's secrets store (`core/secrets_manager.py`, never in the repo or a log), a monthly spending cap
  set in the OpenAI account and a per-run limit in the tool, approval per batch, and every image recorded in the
  manifest with its prompt. **Not built**: a decision for Zac.
- **Already on the PC, free and offline:** a local image model (SDXL-Turbo, used for the Chronicles' panels,
  `data/chronicles/`). Good for quick atmosphere and texture studies and variations; weaker than ChatGPT at precise
  interface concepts. Claude can run it directly, with the same manifest discipline.
- **Claude Design / Muse** reads images from the repository (or uploaded to it). The repository is the shared place
  every role can reach, so it's the hub.

**Recommendation:** start now with the repository library and the manual ChatGPT step (no cost, no keys); use the
local model for variations; decide on the API after the first concept round shows whether the manual step is the
bottleneck.

## 3. The library

```
docs/design/visual_library/
  MANIFEST.md            every asset: id, file, what it is, for which app, the prompt, the style reference,
                         revision, approval status, the spec it serves
  identity/              MIA herself: the orb, her mark, her presence
  atmosphere/            moods and environments (light, depth, texture) for the shell and each app
  interface_concepts/    whole-screen and component concepts
  applications/          per-app concepts: workout/, kitchen/, ...
  approved_references/   only what Zac approved (copied here, never edited in place)
  archive/               superseded concepts, kept for history
```

**Rules:**
- A concept is a **reference, never a production asset**: screens are built from tokens and components, not from
  pasted images. Only photos and illustrations a spec names ship in `web/img/`, and only once approved.
- Nothing personal in any image or prompt: no real names, faces, addresses, plates, account details (the repo is
  shared; the mobile concept picture stayed out for this reason).
- Every file is in the manifest before it's referenced anywhere. Ids: `VL-0001`, in order.
- Status: `concept` → `shortlisted` → `approved` (by Zac) → `superseded` (moved to archive/).
- Size: under 1 MB each (PNG or WebP), so the repo stays light.

## 4. One round, step by step

1. **Brief** (Claude Code, from the design system and the app spec): what's needed, with ready-to-paste prompts
   (`docs/design/MIA_VISUAL_IDENTITY.md` §5 has the first round's).
2. **Generate** (ChatGPT): 2–4 images per prompt; Zac downloads the ones worth keeping.
3. **Add** (Zac, or anyone with the files): upload to the right folder on GitHub (Add file → Upload files), named
   `VL-xxxx_short-name.png`, or drop them in the PC's repo folder; Claude adds the manifest rows (or Zac does, with
   the prompt pasted).
4. **Shortlist** (Muse and Claude): which concepts carry the identity; a short note per pick.
5. **Approve** (Zac): the chosen ones move to `approved_references/`.
6. **Specify** (Muse): screens and components from them, in the app spec and the design system.
7. **Build** (Claude Code): tokens and components first, then the page; check on desktop, phone and glasses widths.
8. **Review** (Codex/ChatGPT): built screen against spec; differences listed.
9. **Accept** (Zac): on real use, which is the only way to level 5.
