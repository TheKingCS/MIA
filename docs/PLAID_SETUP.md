# Connecting Your Banks to MIA (Plaid Setup)

Your step-by-step checklist for linking real bank, card and loan
accounts to MIA's Budget module. Written 2026-09-27, right after your
Plaid account was approved (Trial plan: sandbox access + up to 10 real
connections).

**Where you are right now:**

- [x] Plaid account created and approved
- [ ] Part 1: Get the latest MIA code onto your main computer
- [ ] Part 2: Copy your Plaid keys from the dashboard
- [ ] Part 3: Set up Plaid inside MIA (sandbox)
- [ ] Part 4: Connect a fake sandbox bank and sync
- [ ] Part 5: Report back to Claude
- [ ] Part 6: Real accounts (**wait**, see the note there)

---

## Ground rules (read once)

- **Never paste your Plaid secret or your vault passphrase into a chat,
  email, text, or GitHub.** They only ever get typed into MIA's own
  "Set Up Plaid" window on your computer.
- MIA stores your keys and bank connections in `data/plaid_vault.enc`,
  encrypted with a passphrase you choose. `data/`, `config/config.json`
  and `financial_snapshots/` are all git-ignored, so none of your
  financial data ever gets committed or pushed.
- **The vault passphrase cannot be recovered.** If you forget it, the
  only fix is deleting `data/plaid_vault.enc` and setting Plaid up again.
  Save it in a password manager.
- Plaid gives you **two different secrets**: one for Sandbox, one for
  Production. Today you only need the **Sandbox** one.

---

## Part 1: Get the latest MIA code

Open a terminal on your main computer.

**If you already have MIA on this computer** (you probably do, since your
real config and data live there):

```bash
cd ~/path/to/MIA          # wherever your MIA folder is
git status                # check for uncommitted local changes first
git pull origin master
source .venv/bin/activate
pip install -r requirements.txt
```

If `git status` shows changes you care about, commit or stash them
before pulling (`git stash`, then `git stash pop` after). If you're
not sure, stop and ask Claude before pulling.

**If this computer doesn't have MIA yet:**

```bash
git clone https://github.com/TheKingCS/MIA.git
cd MIA
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

(The repo is private, so git will ask you to sign in to GitHub. Use a
personal access token as the password if it asks.)

**On Windows** (not WSL), activate with `.venv\Scripts\activate`
instead of `source .venv/bin/activate`.

**Start MIA:**

```bash
python main.py
```

**If MIA won't start** and the error mentions a missing `.so` file
(like `libEGL.so.1` or `libpulse.so.0`), install the missing system
libraries on Ubuntu, then try again:

```bash
sudo apt-get update
sudo apt-get install -y libegl1 libgl1 libxkbcommon0 libpulse0
```

- [ ] MIA opens

---

## Part 2: Copy your Plaid keys

1. Sign in at **dashboard.plaid.com**.
2. Go to **Developers → Keys** (sometimes shown as "Team Settings →
   Keys").
3. You need two values:
   - **client_id**: the same for Sandbox and Production.
   - **Sandbox secret**: *not* the Production one.
4. Keep that browser tab open. You'll paste these into MIA in a
   minute; don't save them anywhere else in plain text.

- [ ] I have my client_id and Sandbox secret ready

---

## Part 3: Set up Plaid inside MIA

1. In MIA, open **Budget**, then the **Bank Sync** tab.
2. Click **Set Up Plaid…**
3. Fill in the window:
   - **Client ID**: paste your client_id
   - **Secret**: paste your **Sandbox** secret
   - **Environment**: choose **sandbox**
   - **New vault passphrase**: make up a strong passphrase and save
     it in your password manager *now*
   - **Confirm passphrase**: type it again
4. Click **OK**. You should see *"Plaid is set up and unlocked for this
   session."*

Next time you open MIA, Bank Sync will say it's locked. Click
**Unlock…** and enter your vault passphrase.

- [ ] Plaid set up; status says "Unlocked — 0 connected accounts"

---

## Part 4: Connect a fake sandbox bank and sync

Sandbox uses Plaid's fake test banks: no real money, no real
accounts, nothing that counts against your 10 connections.

1. Click **Connect a Bank…**
2. Your web browser opens a Plaid page, and MIA shows a small
   **"Connecting a Bank"** window that says it's waiting. Leave that
   window open.
3. In the browser: pick any bank (for example "First Platypus Bank" or
   "Chase").
4. Log in with Plaid's sandbox test login:
   - Username: **`user_good`**
   - Password: **`pass_good`**
   - If it asks for a verification code, try **`1234`**.
5. Select all accounts it offers, and continue until Plaid says you're
   done.
6. Go back to MIA. Within a few seconds the waiting window closes on
   its own. MIA then asks you to **re-enter your vault passphrase**;
   that's what saves the new connection. Enter it.
7. The account list should now show the bank with tags like
   *"transactions enabled, cards/loans enabled"*.
8. Click **Sync Now**. It asks for your passphrase again, then shows
   a summary like *"Synced 1 connected account(s). Imported N new
   transaction(s)… Debts: N new…"*

**Now check these tabs:**

- [ ] **Expenses** / **Income**: fake transactions appear
- [ ] **Debts**: a fake credit card and/or student loan appears, marked
      **(bank-synced)**, with a balance, APR and ranking
- [ ] **Summary**: totals changed, including the Total Debt line
- [ ] Click **Sync Now** a second time: the counts should say
      "updated", and **nothing should show up twice**

---

## Part 5: Report back to Claude

This is the first time MIA's bank code has ever talked to Plaid for
real, so tell Claude how it went either way.

**If it worked**, say so, plus anything that looked wrong or confusing
(wrong categories, weird names, missing debts).

**If something failed**, copy and send:

- The exact text of the error popup
- What step you were on (Part and step number)
- The last ~30 lines of the newest file in MIA's `logs/` folder

**Double-check before you send:** no Plaid secret, no passphrase, no
access tokens (long strings starting with `access-`).

- [ ] Reported back

---

## Part 6: Real accounts (**wait**)

**Don't connect your real accounts yet.** Two things are missing and
should be built first:

1. **Switching from sandbox to production.** MIA has no button for
   this yet. Today it would mean deleting `data/plaid_vault.enc` by
   hand.
2. **Disconnecting a bank.** Deleting the vault file doesn't tell Plaid
   the connection is gone. On the Trial plan you get **10 real
   connections**, so a connection MIA forgot about but Plaid didn't
   could keep using up one of your 10 slots.

Ask Claude to build **"Disconnect" and "Reset Plaid setup"** (it's
already been offered). Once that's in, the production steps will be:

1. `git pull` to get the new code.
2. Bank Sync → **Reset Plaid setup** (removes the sandbox test banks).
3. **Set Up Plaid…** again with your client_id, your **Production**
   secret, and environment **production**.
4. **Connect a Bank…** and log in with your *real* bank username and
   password (this happens on Plaid's page, not in MIA).
5. Repeat for each bank or card company. Each login is one of your 10
   connections, and one login that covers several accounts (checking +
   savings + a card at the same bank) counts as just one.
6. **Sync Now**, then review Debts and add promo APR end dates by hand
   (**Edit Selected** on the Debts tab). Banks don't report promo
   expiration dates.

**One habit to keep with real accounts:** for a bank-synced card, don't
use the Debts tab's **Record Payment** button. The bank sync already
imports your payment as a transaction, so recording it again would
count the expense twice. Just let the next sync update the balance.
