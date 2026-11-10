---
id: K-0166
kind: implementation
title: Passwords autofill on the phone: an Android autofill service
status: confirmed
by: claude
created: 2026-11-09T08:58:37+00:00
concerns: core/password_autofill.py, android-phone/app/src/main/java/com/mia/phone/MiaAutofillService.kt, android-phone/app/src/main/java/com/mia/phone/AutofillActivity.kt, web/passwords.js
from: dec:DEC-0035
---
DEC-0035's named next step. MiaAutofillService.kt finds the password box (autofill hints, input type, an HTML type=password) and the username box before it, plus the web domain, and answers with one dataset, 'Fill from MIA', locked behind AutofillActivity (PendingIntent FLAG_MUTABLE, as Android adds extras). The activity talks to MIA's own server on 127.0.0.1 with the phone's session token: GET /api/passwords/autofill (core/password_autofill.matches: same host 3, a subdomain 2, an app whose package names the site 1; a look-alike domain never fits; titles and usernames only), 423 → the master-password box (marked not-for-autofill) → /api/passwords/unlock; the tapped login is read with the same reveal as Show and returned as the authentication result. No SaveInfo: logins are added on the Passwords page. Compiled by the android-phone CI workflow, not in the cloud session; never tried on a phone yet.
