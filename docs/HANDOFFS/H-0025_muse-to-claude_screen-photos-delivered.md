# H-0025: The rest of the screen photos — delivered
- From: muse (for zac) · To: claude (cc chatgpt) · Date: 2026-10-07
- Related: H-0024, `docs/design/IMAGE_REQUESTS.md`, DEC-0018, DEC-0002

## Done
All 12 remaining hero photos are committed to `web/img/` (1920×1280 JPG, each under 400 KB):
garage, kitchen, workout, real-estate, finances, missions, skills, property, maintenance, dashboard, character, assistant.

## Notes
- Same golden-hour style as ChatGPT's home/greenhouse; dark calm bottom third on each for the title/tagline overlay.
- Verified: no text, logos, brands, faces, plates, names, or addresses in any of them (DEC-0002).
- `gh_repo.py write` can't carry binary, so these went up through the same credential helper as binary-safe PUTs (one commit per file).
- Local originals kept at `~/workspace/mia-screen-photos/` on the agent VM if you ever need to re-derive.
- `docs/design/IMAGE_REQUESTS.md` status table not edited — yours to mark ✅ if you want it current.
