# MIA OS: application framework, open questions (Prompt 03)

*Claude (Opus), 2026-11-15. Questions for Zac are also in MIA_OS_OPEN_QUESTIONS.md (Q-27 to Q-29); questions for later
prompts are listed with the prompt that owns them.*

## For Zac

| ID | Question | What a yes changes |
|---|---|---|
| Q-27 | **Third-party apps and a marketplace:** keep the doors (manifests, trust levels, signing) but build no store or third-party SDK, since MIA is for you alone (DEC-0119)? | yes: the developer framework stays first-party; no marketplace work |
| Q-28 | **Extensions out of process (DEC-0176):** approve the proof of concept (one sandboxed "hello sensor" extension) when its time comes, after grants (DEC-0156)? | yes: Prompt 13 designs the sandbox profile; the host is built after grants |
| Q-29 | **Approve DEC-0175 to DEC-0177** (capability-first apps in the runtime; out-of-process extensions; MIA in the image, Flatpak for GUI apps, no marketplace)? | yes: Prompt 04 builds its requirements on them |

## For later prompts

| ID | Question | Owner |
|---|---|---|
| T-02 | The local API's transport for local callers: HTTP over a Unix socket, or D-Bus? | Prompt 05 |
| T-03 | Per-store schema versions and migrations | Prompt 15 |
| T-04 | Device identity beyond tokens | Prompt 12 / 13 |
| T-06 | Typed events across processes: delivery guarantees, idempotency | Prompt 05 |
| T-07 | The capability contract's fields as code: where they're declared, and the test | Prompt 08 (with DEC-0156) |
| T-08 | The extension sandbox's profile and threat model | Prompt 13 (Fable) |
| T-09 | A MIA portal (D-Bus) for Flatpak apps to offer capabilities to MIA | Prompt 05 / 10 |
