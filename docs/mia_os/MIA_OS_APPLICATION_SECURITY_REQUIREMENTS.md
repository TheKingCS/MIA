# MIA OS: application-level security (Prompt 03 §10)

*Claude (Opus), 2026-11-15. Planning; nothing built. Part of [MIA_OS_APPLICATION_FRAMEWORK.md](MIA_OS_APPLICATION_FRAMEWORK.md).
Prompt 13 (security, Fable) expands this; it sets only the application-level model. Grants are DEC-0156 (proposed).*

## 1. Trust levels

| Level | Who | Runs | Can do |
|---|---|---|---|
| Core | the OS image | the OS | the OS's own |
| First-party | MIA's own code, merged on Zac's approval (DEC-0058) | in the MIA Runtime | the platform services directly; capabilities through the action contract |
| Signed extension | code signed by Zac's key, through the extension host (proposed) | its own sandboxed process | only its granted capabilities, over the local API |
| External | any other program (Flatpak, Android, websites) | its own sandbox (Flatpak, Android) | only what's sent to MIA or a portal allows |

**Being integrated with MIA grants nothing** (prompt §10): an extension starts with no capabilities.

## 2. Permissions

| Permission | How it's declared | How it's granted |
|---|---|---|
| Filesystem | only MIA's file service; no raw paths for extensions | per capability |
| Network | declared hosts or "the person's SearXNG" per capability | per capability; World Intelligence shows what goes out |
| Hardware, camera, microphone, location | declared per capability, with why and how long (continuous, while open, one operation) | runtime request, in plain words, the first time |
| Personal data | the stores a capability reads and writes | per capability; sealed stores never leave the runtime except as the capability's answer |
| Inter-app | the other app's capabilities it calls | per capability |
| Background | declared jobs | at install; homeostasis can defer |
| Administrative | never for apps; only the System Manager helper (DEC-0158) | — |
| AI tool invocation | which capabilities the model may propose for this app | the tier decides approval |

**How grants are given** (prompt §10's list): install-time declaration (what it may ask for) → runtime request in
plain words the first time it's needed ("The greenhouse extension wants the camera to read the thermometer once a
day. Allow once / always / no?") → standing grants listed on one screen, revocable. Temporary, session-only grants
exist for one-off needs. Managed policies aren't needed (DEC-0119: one person).

## 3. Sandboxing (for code that isn't MIA's)

Out-of-process, one process per extension, started with a restrictive profile: user namespaces with no network unless
granted, a private `/tmp`, no home directory, read-only system, seccomp filtering, cgroup memory and CPU limits; via
bubblewrap (what Flatpak uses) or `systemd-run --user` with `ProtectSystem=strict`, `PrivateNetwork=`,
`NoNewPrivileges=`, `MemoryMax=`. Its only door to MIA is the local API with its token, so every call meets the grant
check. External GUI apps use Flatpak's own sandbox and portals.

## 4. Updates and trust

An extension's update must be signed by the same key; a changed permission set is shown before it's accepted; a
downgrade needs Zac's approval. MIA's own updates come with the signed OS image (bootc) or a merged, reviewed branch.

## 5. Risks recorded

- **R-04 stays open:** "Add Module" runs code with full privileges until the extension host exists.
- Prompt injection through app data: outside text is always `untrusted()` to the model, and a change it asks for is
  held (`browser_safety.carries_outside_text`); capabilities, not text, decide what happens.
