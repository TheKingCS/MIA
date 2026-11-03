# The sealed relay (DEC-0062)

How MIA's public Web App on the glasses reaches her engine on the phone,
with no address on the internet that leads to MIA, and nothing the relay
can read.

## The parts

```
glasses Web App  <-- encrypted -->  relay  <-- encrypted -->  phone app  -->  engine
(public page, no data)          (a mailbox)           (connects out)     (127.0.0.1)
```

- **Page**: `mia-art`, public. Holds no data and no secrets in its code.
- **Relay**: `relay/`, a Cloudflare Worker. It passes messages between two
  sockets in a room. It stores nothing and logs nothing it's given.
- **Phone app**: connects out to the relay, decrypts, calls only the allowed
  engine paths, and encrypts the answer.

## Pairing

The key never travels. It can't go in the QR link: that passes through
Meta's app, whose logs print links.

1. The page makes an ECDH P-256 key pair and shows a 6-digit room code.
2. The person enters that code in the phone app. The phone makes its own pair
   and a nonce, and sends only a hash of them: its promise. It repeats that
   until the page answers, because the relay keeps nothing.
3. The page answers with its public key and nonce.
4. The phone reveals its key and nonce. The page checks them against the
   promise, and refuses a changed promise.
5. Each derives the same secret and shows an 8-digit check code, from a
   transcript of both keys and nonces.
6. The person compares the two and confirms on both: They Match on the
   glasses, and Android's own dialog on the phone, which no page can answer.
   A fake phone can prove it holds its own key, so the glasses need a person
   too.
7. The phone sends proof that it holds the key, and the glasses check it
   before keeping theirs and send their own proof back. Only then does the
   phone keep the key.
8. Once anyone has answered, a stopped pairing waits for the person to start
   again, so nobody gets fresh guesses unseen.

The order is what stops a relay in the middle: each side's key is fixed
before it sees the other's, so it can't search for keys whose codes match.
It gets one guess in 100 million for each pairing the person starts. A plain "ok" proves
nothing (the first version trusted one; the review caught both).

From the shared secret, HKDF-SHA-256 gives a room id, so the relay's room
name says nothing about the key, one AES-256-GCM key each way, and a key for
each side's proof.

## Messages

- Each answer must match a question the page is still waiting on, by a random
  id, once. A held-back answer can't pass as another's.
- A Listen older than 30 seconds is refused, so holding one back can't open
  the mic later.

- AES-256-GCM, a fresh random nonce each message.
- Each side numbers its messages. The number is sealed inside and must only
  go up, so a replayed message is refused.
- Requests name a path; the phone checks it against the allowlist.

## What the glasses see (DEC-0066)

Every app the engine lists for the glasses, and each designed panel, money
included. A question button runs a Talk turn only when its words are ones the
phone itself served in the cards or the welcome's ideas.

## Her address

The page lives at `mia-glasses.yhrhodes.workers.dev` on its own (a static
Cloudflare Worker), not on `thekingcs.github.io`, which other sites share:
nothing else can reach the key there. A strict Content-Security-Policy keeps
out any script but its own. Publish with `tools/publish_glasses.py`, then from
`mia-art`: `wrangler deploy --name mia-glasses --assets . --compatibility-date
2026-10-01`. The relay only lets that origin in.

## Meeting her (writes)

First boot, User Sync and the tours need to save. The glasses can only POST to
`/api/user-sync` and `/api/welcome`, `/firstboot/step` for
`firstboot.advance` and `firstboot.skip`, and `/action/propose`, `/approve`
and `/reject` for the offers below. Each must be under 30 seconds old.

## Everyday actions: the fifth review (2026-11-02, code read only)

Approved and built (DEC-0064), compiled but not yet run on the real pair. What
the review found:

1. **Bug:** `/firstboot/step` posts to `/api/actions`, which doesn't exist
   (the route is `/api/actions/propose`), so her first boot can't save
   through the relay and would start over each time she opens.
2. **Money already crosses:** `/api/user-sync` approves its chips, and the
   Money topic's can be `bill.add`. DEC-0062 keeps money off the glasses.
   User Sync's Money topic should stay off the relay until Zac says otherwise.
3. **The page is the risk.** It holds the key and its code is public. If
   `mia-art` or its deploy were taken over, new code on the glasses could
   send anything the phone accepts, so the phone can't trust the page's
   `kind` or `params`.

The design that answers 3: when the phone sends a panel, it swaps each
allowed `action` for a one-time reference and keeps the real kind and params
itself. The page can only send that reference back, so it can use what was
offered and invent nothing. Then propose and approve, as elsewhere:

- Only a short list of kinds (DEC-0064), everyday and undoable.
- Under 30 seconds old, like the other writes. A cap per minute.
- Undo only for a proposal made in this pairing.
- References die on unpairing and after a few minutes.
- Checked: a linked phone reads panels and saves actions on the same engine.
- A pairing acts for one person: whoever made its first change. If the engine
  is someone else's after that, the change is rejected.

`HOME_APPS` now has `garage` and `greenhouse`; `maintenance` came off, since
it was never on the glasses. On User Sync's Money topic the phone lets only
skip, later and moving on through, and marks the screen `phone_only`.

DEC-0065 adds `mission.complete`, `meal.cook` and the live workout to the list;
the workout's small steps take one press.

Not built: undo from the glasses. They have no Undo control; undo is on the phone.

`music` is in `HOME_APPS` (Zac, 2026-11-02: "I need the music app working").
`/music/play` takes track ids that must look like ids, `/music/control` a named
control, `/music/now` is read; each plays only this phone's library.

`/api/talk/thread` and `/api/glasses/feed` read the home computer's when the
phone is linked: that's where her voice turns go.

## The bridges

Only pages at `http://127.0.0.1:PORT/` stay in the app's WebView; links go to
the browser, which has none of MIA's bridges, and anything else from outside
but a picture is refused.

## What the phone allows

`/voice/listen` makes her listen; she answers through the glasses, not the
relay. Reads (Zac: read-only Home, 2026-11-02; "build her out according to
the designs"): `/api/glasses`, each panel of the apps in `HOME_APPS`,
`/api/glasses/orb`, `/api/glasses/feed` and `/api/talk/thread` (conversation).
Each must match an exact shape. The
phone cuts the answer down: only approved apps, only panel menu items, every
`action` removed (a short list come back as references, DEC-0064), and any
text with a currency symbol blanked. Nothing else passes, whatever the page asks: no financial or account paths.

Before any change path goes on the list, freshness must cover it as it does
Listen: a held-back request otherwise passes at any age.

## What a person with the relay could do

They could drop or delay messages, see when they flow and how big they are.
They can't read them, or change one without it being refused. Metadata stays
visible: that's accepted.

## If the glasses are lost

The key sits in the page's `localStorage`. "Unpair glasses" on the phone
drops the key, so the glasses can reach nothing. The page can't read data
offline: it keeps none.

## Before anything personal crosses (the gate in DEC-0062)

- [x] Tested end to end with fake data, on the second pairing version (Zac, 2026-11-02).
- [x] Relay refuses other origins, oversized messages and floods (`relay/test.mjs`, live).
- [x] Replay and tampering refused on the real pair, on the second version; a swapped key and an unproved `ok` are refused (`mia-art/test.mjs`).
- [x] A path outside the allowlist is refused on the phone.
- [x] Unpairing works (tested on the real pair: the glasses get no answer).
- [x] Nothing is logged with message contents, on the relay or the phone. The
  engine's token is no longer logged either (`ci_smoke.sh` signs up instead).
- [x] Security review of the diff, then Zac's OK, given 2026-11-02 for read-only Home only. The fourth review (2026-11-02) found nothing at
  confidence 8 or above, code read only. The third
  found the page gave up its key for an empty commit, which undid the promise.
  Two reviews before it: the
  first found a relay could beat the check code, an unproved `ok` and an open
  bridge; the second found no person confirming on the glasses, a dialog not
  tied to its pairing, and answers not tied to questions. All fixed.
- [x] Foreign pages can't reach the bridges: links leave for the browser, and
  outside frames, scripts and form posts are blocked (`shouldInterceptRequest`).
