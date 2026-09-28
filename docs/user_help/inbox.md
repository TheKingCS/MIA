# Inbox: receipts, manuals, and documents MIA files for you

## What it does

Send MIA a document (a store receipt, an owner's manual, a warranty,
an invoice) and it reads it, works out what it is and which of your
things it's for, and suggests where it goes. **Nothing is filed until
you say so.**

## Three ways to send documents

- **Drop a file** in the `inbox` folder inside MIA's folder, or use
  Inbox → Add Files….
- **From your phone:** in any Android app, Share → **MIA inbox** (a
  PDF from Gmail, a photo of a receipt, a manual from Files; several at
  once works too). Or Send a file in the phone web app. Up to 25 MB each.
- **By email (optional):** Inbox → Email Settings… connects a mailbox
  you choose (best: a separate address used only for MIA). MIA checks
  it every 10 minutes and takes each new message and its attachments.
  For Gmail you need an app password (Google Account → Security →
  2-Step Verification → App passwords), not your normal password.
  The password is encrypted with your passphrase; unlocking the
  Private Journal with the same passphrase unlocks email too. While
  locked, MIA just doesn't check mail.

New documents show up within a minute, and MIA tells you (counted in
her daily message limit, merged with anything else she has to say).

## What MIA reads

- **What it is:** receipt, invoice, manual, warranty, or other.
- **Whose it is:** matched to your Maintenance items by serial number,
  model, name or maker. Fill in the model and serial number on your
  mower, truck and tools so their documents are recognized. It can
  also match a build (project) named in the document.
- **Receipts and invoices:** the total (from the Total line, never the
  subtotal; the Inbox screen shows which line it read), the date and
  the store.
- **Manuals:** maintenance steps with an interval, like "change the
  engine oil every 50 hours".

All of this is done by fixed rules, not the AI model, so it never
invents a number.

**Photos and scans** (a phone picture of a paper receipt, a scanned
manual) are read with text recognition (Tesseract) in the background.
They show "(reading…)" for a moment and are announced once read.
Reading a faded or crumpled receipt can get a digit wrong, so check the
amount (the screen shows which line it came from) before filing. If
Tesseract isn't installed, the document is kept and the note says how
to enable reading it; you can still type the amount and file it.
iPhone HEIC photos can't be read; send them as JPEG.

## Filing

Select a document, correct anything (which item, which build, the
amount, the category), untick maintenance steps you don't want, and
click **File It**:

- a receipt or invoice becomes a Budget expense, tagged to the tool or
  build it's for;
- a manual, warranty or receipt for an item goes on that item's page
  in Maintenance (its documents);
- ticked maintenance steps become maintenance tasks (hour-based steps
  use the item's hour meter).

**Dismiss** takes a document out of the list without filing it. Filed
and dismissed documents stay listed (✓ and ✕) and their files stay in
the inbox folder.

By voice: "what's in my inbox?", "file it", "file the Lowe's receipt
under the greenhouse", "file the mower manual without the tasks",
"don't file that one".
