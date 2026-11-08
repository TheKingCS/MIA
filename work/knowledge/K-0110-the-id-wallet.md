---
id: K-0110
kind: implementation
title: The ID wallet
status: confirmed
by: claude
created: 2026-11-08T07:47:44+00:00
concerns: core/id_wallet.py, server/app.py, web/wallet.js, core/today.py, core/assistant_turn.py
from: dec:DEC-0129, dec:DEC-0126
---
core/id_wallet.IdWallet: id_wallet.json (in SEALED and PERSONAL_STORES) plus each photo as its own text file, base64 inside a JSON payload passed through at_rest.seal() (seal works on text; the photo files aren't store files, so they're sealed explicitly). Numbers are treated like passwords: add and edit go through /api/wallet with a WalletCard body, never an action; the only action is wallet.delete (card_id only), so proposals, history and the undo log never hold a number. Lists mask to the last four; get_wallet and Today say names and dates only. wants_card() routes 'show my driver's license' to wallet.html?show=<id> before the model. The Show view asks for a screen wake lock and carries the legal note: a copy is a backup, not the ID.
