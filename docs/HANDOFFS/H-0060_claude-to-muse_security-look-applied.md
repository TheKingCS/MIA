# H-0060 · claude → muse (cc zac) · 2026-10-18

## H-0059 applied

1. **Strip honesty:** the Cameras cell is `soon` (amber edge) whenever
   any camera has a problem or stops answering, or the linked home
   computer can't be reached. Otherwise it's `ok`. It updates live with
   the tiles, the same way Answering does.
2. **Full view** keeps "location · via PC".
3. **Delete picture:** `aria-label="Delete this picture"`.
4. **Empty state:** your copy, word for word. The brand list now lives
   only in Set Up.

Checks:

- **`camera.remove`** is intentional. It follows the record pattern
  (`person.*`, `pet.*`, `shop_reward.*`: noun.verb on the thing itself),
  while `security.save_picture` and `security.picture_delete` act on the
  app's pictures. Not a typo.
- **Grown-ups only** is enforced by the engine, not the page:
  `security` isn't in `CHILD_APPS` (core/child_accounts.py). So the
  shell never lists it for a child, every `/api/security*` endpoint
  returns 403 for a child (`_screen` / `_security_book` in
  server/app.py), and none of its actions are `child_ok`.
  `tests/test_security_cams.py::test_grown_ups_only` checks this.

Also new: the glasses' **Heads-Up** screen (Zac): clear until a win or
notification, then a card for 6 s (`.hud-card` in glasses.css: the
reward frame's corners, smaller). It's ready for a look when you get to
it.
