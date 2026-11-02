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
2. The person enters that code in the phone app, which makes its own pair.
3. Both join `pair-<code>` on the relay and swap public keys.
4. Each derives the same secret, and shows a 6-digit check code from it.
5. The person compares the two and confirms on the phone. Only then does the
   phone keep the key. A relay that swapped the keys would give two different
   check codes.

From the shared secret, HKDF-SHA-256 gives a room id, so the relay's room
name says nothing about the key, and one AES-256-GCM key each way.

## Messages

- AES-256-GCM, a fresh random nonce each message.
- Each side numbers its messages. The number is sealed inside and must only
  go up, so a replayed message is refused.
- Requests name a path; the phone checks it against the allowlist.

## What the phone allows

Starting with reads only: `/api/glasses`, `/api/glasses/{app}/{item}` and
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

- [x] Tested end to end with fake data (real glasses and phone, 2026-11-02).
- [x] Relay refuses other origins, oversized messages and floods (`relay/test.mjs`, live).
- [x] Replay and tampering refused on the real pair; a swapped key shows different codes (`mia-art/test.mjs`).
- [x] A path outside the allowlist is refused on the phone.
- [x] Unpairing works (tested on the real pair: the glasses get no answer).
- [x] Nothing is logged with message contents, on the relay or the phone. The
  engine's token is no longer logged either (`ci_smoke.sh` signs up instead).
- [ ] Security review of the diff, then Zac's OK.
