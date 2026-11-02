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
6. The person compares the two and confirms in Android's own dialog, which no
   page can answer.
7. The phone sends proof that it holds the key, and the glasses check it
   before keeping theirs and send their own proof back. Only then does the
   phone keep the key.

The order is what stops a relay in the middle: each side's key is fixed
before it sees the other's, so it can't search for keys whose codes match.
It gets one guess in 100 million for each pairing. A plain "ok" proves
nothing (the first version trusted one; the review caught both).

From the shared secret, HKDF-SHA-256 gives a room id, so the relay's room
name says nothing about the key, one AES-256-GCM key each way, and a key for
each side's proof.

## Messages

- AES-256-GCM, a fresh random nonce each message.
- Each side numbers its messages. The number is sealed inside and must only
  go up, so a replayed message is refused.
- Requests name a path; the phone checks it against the allowlist.

## The bridges

Only pages at `http://127.0.0.1:PORT/` stay in the app's WebView; everything
else goes to the browser, which has none of MIA's bridges.

## What the phone allows

`/voice/listen` makes her listen; she answers through the glasses, not the
relay. Then reads only: `/api/glasses`, `/api/glasses/{app}/{item}` and
`/api/glasses/orb`. Changes come later, through `/api/actions` and the usual
approval (Propose, Approve, Execute), each added on purpose. Nothing else
passes, whatever the page asks: no financial or account paths.

## What a person with the relay could do

They could drop or delay messages, see when they flow and how big they are.
They can't read them, or change one without it being refused. Metadata stays
visible: that's accepted.

## If the glasses are lost

The key sits in the page's `localStorage`. "Unpair glasses" on the phone
drops the key, so the glasses can reach nothing. The page can't read data
offline: it keeps none.

## Before anything personal crosses (the gate in DEC-0062)

- [ ] Tested end to end with fake data, on the second pairing version.
- [x] Relay refuses other origins, oversized messages and floods (`relay/test.mjs`, live).
- [ ] Replay and tampering refused on the real pair, on the second version; a swapped key and an unproved `ok` are refused (`mia-art/test.mjs`).
- [x] A path outside the allowlist is refused on the phone.
- [x] Unpairing works (tested on the real pair: the glasses get no answer).
- [x] Nothing is logged with message contents, on the relay or the phone. The
  engine's token is no longer logged either (`ci_smoke.sh` signs up instead).
- [ ] Security review of the diff, then Zac's OK. The first review found a
  relay could beat the check code, an unproved `ok`, and an open bridge; all
  three are fixed and being reviewed again.
