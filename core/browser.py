"""
core.browser
==============

MIA's own web browser (DEC-0117, Zac 2026-11-07): Microsoft Edge, driven by
Playwright, in a profile that is MIA's alone, never the person's own
browser, logins, cookies or saved passwords. The window is visible on the
computer, so what she does can be watched.

**How she sees a page** (`Page`): its address, title, its text, and the
controls on it, each numbered (`[12] button "Place order"`), so the model
picks a control by number instead of guessing at coordinates. Page text
always reaches the model through `browser_safety.untrusted()`: content from
the web, never instructions.

**How she acts** (`Browser.do()`): every step is sorted by
`core.browser_safety.classify()`. Reading and ordinary steps (following a
link, typing into a field, searching) she does herself. A step that
commits (submit, buy, send, sign in, delete, download...) becomes a
pending step with a screenshot, proposed as the action `browser.commit`
(core/actions.py): it runs only when the person approves it, on a screen
or by saying yes (core/talk_it_out.py), never by the model's own say-so. A
password, card or ID field she never types into.

**Teaching** (core/browser_routines.py): the person does a task once in
her window while she records each step; she replays it later, checking
the page as she goes and stopping at every commit.

**The pieces:**
- `Driver`: what any browser engine gives her (open, snapshot, click,
  type, select, press, back, screenshot, recording, and for the live view
  inside MIA a frame, the page size and the person's own input). `EdgeDriver` is the
  real one: Playwright owns the browser on one worker thread (its objects
  must stay on the thread that made them), and every call is handed to it.
  Tests use a fake driver.
- `Browser`: one person's browser session: the page now, pending commits,
  teaching, and what the person said lately (`hear`): the only words she
  types, chooses or searches for on her own (`authorized`, DEC-0122);
  anything else waits for their OK with the text shown (`go` for opening
  and searching, `do` for steps). It lives inside MIA (2026-11-07): no
  window of its own, shown live on the Browser page (`frame`), worked by
  the person from there (`person`); `browser.own_window` brings the
  separate Edge window back.
- `Browsers` (`context.browsers`): one session per person, each with its
  own profile folder in their own data (so their site sign-ins are theirs).
"""

from __future__ import annotations

import concurrent.futures
import json
import queue
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import quote_plus, urlparse

from core.browser_safety import ACT, COMMIT, NEVER, READ, Control, Verdict, classify, untrusted
from core.logger import get_logger

log = get_logger(__name__)

SEARCH_URL = "https://duckduckgo.com/?q="  # a search when she's given words instead of an address
MAX_CONTROLS = 150
PENDING_MINUTES = 30  # a commit not approved by then is let go
VIEW_W, VIEW_H = 1280, 800  # the page's size when her browser lives inside MIA (no window of its own)
PERSON_KEYS = ("Enter", "Tab", "Backspace", "Escape", "ArrowDown", "ArrowUp", "PageDown", "PageUp")
HEARD_MINUTES = 30  # the person's words she may type or search for on her own, from this long back
HEARD_KEEP = 12  # and at most this many of their messages
_URLISH = re.compile(r"^(https?://|www\.)|^[a-z0-9-]+(\.[a-z0-9-]+)+(:\d+)?(/|$)", re.I)


@dataclass
class Page:
    """A page as MIA reads it: its address, title, text and numbered controls."""
    url: str = ""
    title: str = ""
    text: str = ""
    controls: list = field(default_factory=list)  # Control

    def control(self, ref) -> Optional[Control]:
        """A control by its number on the page, or None."""
        try:
            ref = int(ref)
        except (TypeError, ValueError):
            return None
        return next((c for c in self.controls if c.ref == ref), None)

    def find(self, name: str, role: str = "") -> Optional[Control]:
        """The control a person would mean by its name (and role, when given): an exact name first, then one that
        contains it."""
        want = " ".join((name or "").lower().split())
        if not want:
            return None
        pool = [c for c in self.controls if not role or c.role == role] or self.controls
        exact = [c for c in pool if " ".join(c.name.lower().split()) == want]
        if exact:
            return exact[0]
        return next((c for c in pool if want in c.name.lower()), None)

    def site(self) -> str:
        """The page's site (its host), or its address."""
        return urlparse(self.url).netloc or self.url


@dataclass
class Pending:
    """A step waiting for the person: what it is (a commit to press or type, or a sign-in for them to do), on which
    page, why it waits, the screenshot of the page, when, the proposal it belongs to, and the routine run it's part
    of (to carry on after)."""
    pending_id: str
    kind: str  # click | type | select | press | signin
    control: Optional[Control]
    text: str
    page_url: str
    page_title: str
    why: str
    screenshot: str = ""
    at: float = field(default_factory=time.time)
    proposal_id: str = ""
    routine: Optional[dict] = None  # {"id": routine id, "next": step index to carry on from}

    def summary(self) -> str:
        """The sentence the person approves, made in code: what she'll do (the exact words she'd type or choose, the
        address she'd open), on which site, and why it waits."""
        site = urlparse(self.page_url).netloc or self.page_title or "this page"
        if self.kind == "signin":
            return f"Sign in on {site} yourself in MIA's browser, then approve so she carries on"
        if self.kind == "open":
            return f"Open {self.text[:200]} in MIA's browser ({self.why})"
        name = (self.control.name if self.control else "") or "the control"
        shown = self.text if len(self.text) <= 160 else self.text[:157] + "..."
        what = {"click": f"press \"{name}\"", "press": f"press Enter in \"{name}\"",
                "select": f"choose \"{shown}\" in \"{name}\"",
                "type": f"type \"{shown}\" into \"{name}\""}.get(self.kind, f"{self.kind} \"{name}\"")
        return f"On {site}, {what} ({self.why})"


class Driver:
    """What a browser engine gives MIA. The real one is EdgeDriver; tests use a fake. Every method raises
    BrowserError when the browser can't do it."""

    def open(self, url: str) -> None:
        """Goes to an address."""
        raise NotImplementedError

    def snapshot(self) -> Page:
        """The page now, its controls numbered."""
        raise NotImplementedError

    def click(self, ref: int) -> None:
        """Clicks a numbered control."""
        raise NotImplementedError

    def type(self, ref: int, text: str) -> None:
        """Replaces a field's text."""
        raise NotImplementedError

    def select(self, ref: int, value: str) -> None:
        """Chooses an option in a list by its label."""
        raise NotImplementedError

    def press(self, ref: int, key: str = "Enter") -> None:
        """Presses a key in a control."""
        raise NotImplementedError

    def back(self) -> None:
        """Goes back a page."""
        raise NotImplementedError

    def screenshot(self, path: Path) -> Path:
        """Saves what's on screen as a PNG."""
        raise NotImplementedError

    def on_record(self, callback: Optional[Callable[[dict], None]]) -> None:
        """Starts (with a callback) or stops (None) reporting what the person does in the window."""
        raise NotImplementedError

    def frame(self) -> bytes:
        """What the page shows now, as a small JPEG (the live view inside MIA)."""
        raise NotImplementedError

    def viewport(self) -> tuple[int, int]:
        """The page's width and height in its own pixels (to place a click made on the live view)."""
        raise NotImplementedError

    def person(self, kind: str, x: float = 0, y: float = 0, text: str = "", key: str = "", dy: float = 0) -> None:
        """The person operating the page through the live view: a click at x, y; typing text; a key; a scroll."""
        raise NotImplementedError

    def close(self) -> None:
        """Closes the browser."""
        raise NotImplementedError


class BrowserError(RuntimeError):
    """The browser couldn't do what was asked (not installed, the page went away, a control vanished)."""


# ------------------------------------------------------------------ the real engine: Edge through Playwright

_SNAPSHOT_JS = r"""() => {
  const SEL = 'a[href],button,input,select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],' +
              '[role=checkbox],[role=radio],[role=searchbox],[role=combobox],[contenteditable=true]';
  const visible = el => { const r = el.getBoundingClientRect(); const s = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const nameOf = el => {
    const by = el.getAttribute('aria-labelledby');
    if (by) { const t = by.split(' ').map(id => (document.getElementById(id) || {}).innerText || '').join(' ').trim(); if (t) return t; }
    if (el.getAttribute('aria-label')) return el.getAttribute('aria-label');
    if (el.id) { const l = document.querySelector('label[for="' + CSS.escape(el.id) + '"]'); if (l && l.innerText.trim()) return l.innerText; }
    const wrap = el.closest('label'); if (wrap && wrap.innerText.trim() && wrap !== el) return wrap.innerText;
    const t = (el.innerText || '').trim(); if (t) return t;
    return el.value && el.type !== 'password' ? el.value : (el.placeholder || el.title || el.alt || el.name || '');
  };
  const roleOf = el => {
    if (el.getAttribute('role')) return el.getAttribute('role');
    const tag = el.tagName.toLowerCase(), type = (el.type || '').toLowerCase();
    if (tag === 'a') return 'link'; if (tag === 'select') return 'combobox'; if (tag === 'textarea') return 'textbox';
    if (tag === 'summary') return 'summary';
    if (tag === 'input') { if (['submit','button','reset','image'].includes(type)) return 'button';
      if (type === 'checkbox' || type === 'radio') return type; if (type === 'search') return 'searchbox'; return 'textbox'; }
    return tag === 'button' ? 'button' : 'textbox';
  };
  const inSearch = el => !!(el.closest('[role=search]') || (el.form && (el.form.getAttribute('role') === 'search' ||
     el.form.querySelector('input[type=search],input[name=q],input[name=search],input[name=query]'))));
  document.querySelectorAll('[data-mia-ref]').forEach(e => e.removeAttribute('data-mia-ref'));
  const controls = []; let n = 0;
  for (const el of document.querySelectorAll(SEL)) {
    if (controls.length >= LIMIT) break;
    if (!visible(el) || el.disabled) continue;
    n += 1; el.setAttribute('data-mia-ref', String(n));
    controls.push({ref: n, role: roleOf(el), name: nameOf(el).replace(/\s+/g, ' ').trim().slice(0, 120),
      input_type: (el.type || '').toLowerCase(), autocomplete: el.getAttribute('autocomplete') || '',
      href: el.getAttribute('href') || '', in_search: inSearch(el)});
  }
  return {url: location.href, title: document.title, text: (document.body ? document.body.innerText : '').slice(0, 60000),
          controls};
}""".replace("LIMIT", str(MAX_CONTROLS))

# What the person does in the window while teaching, reported to Python (passwords never: only that they signed in).
_RECORD_JS = r"""(() => {
  if (window.__miaRecorder) return; window.__miaRecorder = true;
  const SEL = 'a[href],button,input,select,textarea,summary,[role=button],[role=link],[role=tab],[role=menuitem],[role=checkbox]';
  const describe = el => ({role: el.tagName.toLowerCase() === 'a' ? 'link' : (el.getAttribute('role') ||
      (el.tagName.toLowerCase() === 'select' ? 'combobox' : el.tagName.toLowerCase() === 'input' &&
       ['submit','button','image'].includes((el.type || '').toLowerCase()) ? 'button' : el.tagName.toLowerCase() === 'button' ? 'button' : 'textbox')),
    name: (el.getAttribute('aria-label') || (el.labels && el.labels[0] && el.labels[0].innerText) || (el.innerText || '').trim() ||
           el.placeholder || el.title || el.name || '').replace(/\s+/g, ' ').trim().slice(0, 120),
    input_type: (el.type || '').toLowerCase(), href: el.getAttribute('href') || ''});
  const send = step => { try { window.miaRecord(JSON.stringify(Object.assign({title: document.title}, step))); } catch (e) {} };
  document.addEventListener('click', ev => { const el = ev.target.closest(SEL); if (!el) return;
    const tag = el.tagName.toLowerCase(), type = (el.type || '').toLowerCase();
    if ((tag === 'input' && !['submit','button','image','checkbox','radio'].includes(type)) || tag === 'textarea' || tag === 'select') return;
    send(Object.assign({kind: 'click'}, describe(el))); }, true);
  document.addEventListener('change', ev => { const el = ev.target; if (!el.matches || !el.matches('input,select,textarea')) return;
    const type = (el.type || '').toLowerCase();
    if (['submit','button','image','checkbox','radio'].includes(type)) return;
    if (type === 'password') { send({kind: 'signin'}); return; }
    send(Object.assign({kind: el.tagName.toLowerCase() === 'select' ? 'select' : 'type',
      text: el.tagName.toLowerCase() === 'select' ? (el.selectedOptions[0] || {}).text || el.value : el.value}, describe(el))); }, true);
  document.addEventListener('keydown', ev => { if (ev.key !== 'Enter') return; const el = ev.target;
    if (!el.matches || !el.matches('input') || (el.type || '').toLowerCase() === 'password') return;
    send(Object.assign({kind: 'type', text: el.value}, describe(el)));
    send(Object.assign({kind: 'press'}, describe(el))); }, true);
})()"""


class _Worker(threading.Thread):
    """The one thread that owns Playwright and the browser; every call is handed to it and waited for."""

    def __init__(self, profile_dir: Path, headless: bool) -> None:
        """Starts the browser thread for this profile (shown, unless headless)."""
        super().__init__(daemon=True, name="mia-browser")
        self.profile_dir, self.headless = profile_dir, headless
        self.jobs: "queue.Queue" = queue.Queue()
        self.ready = concurrent.futures.Future()
        self.recorder: Optional[Callable[[dict], None]] = None
        self.start()
        self.ready.result(timeout=60)

    def run(self) -> None:
        """Opens Edge in MIA's profile (hidden at a fixed page size inside MIA, or in a window of its own), then runs
        each job handed to it until told to stop."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as problem:
            self.ready.set_exception(BrowserError("MIA's browser needs Playwright (pip install playwright)."))
            log.warning("Browser unavailable: %s", problem)
            return
        try:
            with sync_playwright() as p:
                self.profile_dir.mkdir(parents=True, exist_ok=True)
                size = {"no_viewport": True} if not self.headless else {"viewport": {"width": VIEW_W, "height": VIEW_H}}
                self.context = p.chromium.launch_persistent_context(
                    str(self.profile_dir), channel="msedge", headless=self.headless, accept_downloads=False, **size)
                self.context.expose_binding("miaRecord", lambda _source, raw: self._recorded(raw))
                self.context.add_init_script(_RECORD_JS)
                self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
                self.ready.set_result(True)
                while True:
                    fn, done = self.jobs.get()
                    if fn is None:
                        break
                    try:
                        done.set_result(fn(self))
                    except Exception as problem:  # every browser failure is said, never raised past the worker
                        done.set_exception(BrowserError(str(problem).splitlines()[0][:300]))
                self.context.close()
        except Exception as problem:
            if not self.ready.done():
                self.ready.set_exception(BrowserError(f"Edge wouldn't open: {str(problem).splitlines()[0][:200]}"))
            log.exception("The browser thread stopped.")

    def _recorded(self, raw: str) -> None:
        """One thing the person did in the window, passed on while teaching."""
        if self.recorder is not None:
            try:
                self.recorder(json.loads(raw))
            except Exception:
                log.exception("Recording a browser step failed.")

    def call(self, fn: Callable, timeout: float = 45.0):
        """Runs fn(worker) on the browser thread and returns what it gives."""
        done = concurrent.futures.Future()
        self.jobs.put((fn, done))
        return done.result(timeout=timeout)

    def stop(self) -> None:
        """Closes the browser and ends the thread."""
        self.jobs.put((None, None))


class EdgeDriver(Driver):
    """Microsoft Edge in MIA's own profile, through Playwright (no browser to download: it uses the Edge
    installed)."""

    def __init__(self, profile_dir: Path, headless: bool = False) -> None:
        """Opens Edge in the profile folder, its window shown unless headless."""
        self.worker = _Worker(Path(profile_dir), headless)

    def _page(self, w):
        """The tab she uses, opened again if the person closed it."""
        if w.page.is_closed():
            w.page = w.context.pages[0] if w.context.pages else w.context.new_page()
        return w.page

    def _settle(self, page) -> None:
        """Waits for a page to finish loading (or a few seconds, whichever comes first)."""
        try:
            page.wait_for_load_state("domcontentloaded", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=3000)
        except Exception:
            pass

    def _ref(self, page, ref: int):
        """The element a control number points to."""
        return page.locator(f'[data-mia-ref="{int(ref)}"]').first

    def open(self, url: str) -> None:
        """Goes to an address and waits for it."""
        def go(w):
            page = self._page(w)
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            self._settle(page)
        self.worker.call(go)

    def snapshot(self) -> Page:
        """The page now, read in the page itself (_SNAPSHOT_JS)."""
        data = self.worker.call(lambda w: self._page(w).evaluate(_SNAPSHOT_JS))
        return Page(data["url"], data["title"], data["text"], [Control(**c) for c in data["controls"]])

    def click(self, ref: int) -> None:
        """Clicks a control and waits for what it loads."""
        def go(w):
            page = self._page(w)
            self._ref(page, ref).click(timeout=10000)
            self._settle(page)
        self.worker.call(go)

    def type(self, ref: int, text: str) -> None:
        """Replaces a field's text."""
        self.worker.call(lambda w: self._ref(self._page(w), ref).fill(text, timeout=10000))

    def select(self, ref: int, value: str) -> None:
        """Chooses an option by its label."""
        self.worker.call(lambda w: self._ref(self._page(w), ref).select_option(label=value, timeout=10000))

    def press(self, ref: int, key: str = "Enter") -> None:
        """Presses a key in a control and waits for what it loads."""
        def go(w):
            page = self._page(w)
            self._ref(page, ref).press(key, timeout=10000)
            self._settle(page)
        self.worker.call(go)

    def back(self) -> None:
        """Goes back a page."""
        def go(w):
            page = self._page(w)
            page.go_back(timeout=15000)
            self._settle(page)
        self.worker.call(go)

    def screenshot(self, path: Path) -> Path:
        """Saves what's on screen as a PNG."""
        path.parent.mkdir(parents=True, exist_ok=True)
        self.worker.call(lambda w: self._page(w).screenshot(path=str(path)))
        return path

    def on_record(self, callback: Optional[Callable[[dict], None]]) -> None:
        """Starts or stops passing on what the person does in the window."""
        self.worker.recorder = callback

    def frame(self) -> bytes:
        """The page now as a JPEG, fast enough to show about once a second."""
        return self.worker.call(lambda w: self._page(w).screenshot(type="jpeg", quality=70), timeout=15)

    def viewport(self) -> tuple[int, int]:
        """The page's size: the fixed one inside MIA, else the window's."""
        def size(w):
            page = self._page(w)
            if page.viewport_size:
                return page.viewport_size["width"], page.viewport_size["height"]
            return tuple(page.evaluate("[window.innerWidth, window.innerHeight]"))
        return self.worker.call(size, timeout=15)

    def person(self, kind: str, x: float = 0, y: float = 0, text: str = "", key: str = "", dy: float = 0) -> None:
        """The person's own click, typing, key or scroll, as real input to the page (so teaching records it as if
        they'd done it in a window)."""
        def go(w):
            page = self._page(w)
            if kind == "click":
                page.mouse.click(float(x), float(y))
                self._settle(page)
            elif kind == "type":
                page.keyboard.type(text, delay=15)
            elif kind == "key":
                page.keyboard.press(key)
                if key == "Enter":
                    self._settle(page)
            elif kind == "scroll":
                page.mouse.move(float(x) or 1, float(y) or 1)
                page.mouse.wheel(0, float(dy))
            else:
                raise BrowserError(f"I don't know \"{kind}\".")
        self.worker.call(go)

    def close(self) -> None:
        """Closes Edge."""
        self.worker.stop()


# ------------------------------------------------------------------ one person's browser

def looks_like_address(text: str) -> bool:
    """Pure logic. Whether what she was given is a web address rather than words to search for."""
    return bool(_URLISH.match((text or "").strip())) and " " not in (text or "").strip()


def address_for(target: str) -> str:
    """Pure logic. The address to open: the one given (https:// added when it has no scheme), or a search for the
    words. Only web pages: any other scheme (file:, javascript:, data:, edge:...) is a BrowserError, never searched
    for (that would send a local path to the search engine)."""
    target = (target or "").strip()
    scheme = re.match(r"^([a-z][a-z0-9+.-]*):(?!\d)", target, re.I)  # "example.com:8080" is a host and port
    if scheme and scheme.group(1).lower() not in ("http", "https"):
        raise BrowserError("I only open web pages (http or https), not files or other kinds of address.")
    if looks_like_address(target):
        return target if re.match(r"^https?://", target, re.I) else "https://" + target
    return SEARCH_URL + quote_plus(target)


def describe_control(control: Control) -> str:
    """Pure logic. A control as the model reads it: its number, role and name, and whether she'd ask first."""
    verdict = classify("type" if control.role in ("textbox", "searchbox", "combobox") else "click", control)
    flag = {NEVER: " (you type this yourself)", COMMIT: " (asks you first)"}.get(verdict.level, "")
    return f"[{control.ref}] {control.role} \"{control.name or '(no name)'}\"{flag}"


class Browser:
    """One person's browser session: the driver, the page last read, steps waiting for the person, and teaching.
    Made lazily: no Edge opens until she's asked to browse."""

    def __init__(self, context, profile_dir: Path, driver_factory: Optional[Callable[[Path], Driver]] = None) -> None:
        """Keeps where her profile lives and how to make the driver (inside MIA, unless browser.own_window); nothing
        opens yet, and nothing has been heard."""
        self.context = context
        self.profile_dir = Path(profile_dir)
        # Inside MIA (2026-11-07, Zac: "open the browser inside a window in her program"): no window of its own, shown
        # live on the Browser page; browser.own_window brings back the separate Edge window.
        own = bool(getattr(context, "config", None) and context.config.get("browser.own_window", False))
        self._factory = driver_factory or (lambda folder: EdgeDriver(folder, headless=not own))
        self.driver: Optional[Driver] = None
        self.page = Page()
        self.pending: dict[str, Pending] = {}
        self.teaching: Optional[dict] = None
        self.lock = threading.RLock()
        # What the person said lately (Zac, 2026-11-07, review): the only words she may type or search for on her
        # own. Anything else (words she composed, things she knows about them) waits for their OK, shown in full.
        self.heard: list[tuple[float, str]] = []

    # -------------------------------------------------------------- whose words

    def hear(self, words: str) -> None:
        """Keeps what the person just said to MIA (their message, each turn), for HEARD_MINUTES."""
        words = " ".join((words or "").split())
        if words:
            self.heard = [h for h in self.heard if h[0] > time.time() - HEARD_MINUTES * 60][-(HEARD_KEEP - 1):]
            self.heard.append((time.time(), words))

    def authorized(self, text: str, routine: Optional[dict] = None) -> bool:
        """Whether she may put these words into a page on her own: they're empty, or part of a task the person taught
        her by doing it (its words are theirs), or every word of them is in what the person said in the last
        HEARD_MINUTES."""
        words = _words_of(text)
        if not words or routine is not None:
            return True
        cutoff = time.time() - HEARD_MINUTES * 60
        said = set().union(*[_words_of(h[1]) for h in self.heard if h[0] > cutoff] or [set()])
        return words <= said

    # -------------------------------------------------------------- reading

    def _driver(self) -> Driver:
        """The driver, opened the first time it's needed."""
        if self.driver is None:
            self.driver = self._factory(self.profile_dir)
        return self.driver

    def refresh(self) -> Page:
        """Reads the page as it is now."""
        self.page = self._driver().snapshot()
        return self.page

    def go(self, target: str, routine: Optional[dict] = None) -> dict:
        """Opens an address, or searches for words, the way `do` does a step: at once when it carries nothing but
        the person's own words (a plain address, or a search or query they said), else held for their OK with the
        address shown. Returns {done, said, pending}."""
        with self.lock:
            url = address_for(target)
            carries = urlparse(url).query if looks_like_address(target) else target
            if not self.authorized(carries, routine):
                pending = self._hold("open", None, url, Verdict(COMMIT, "those words didn't come from you"), routine)
                return {"done": False, "pending": pending,
                        "said": f"That needs your OK: {pending.summary()}. Say yes, or approve it on screen."}
            self.open(url)
            return {"done": True, "pending": None, "said": self.glance()}

    def open(self, target: str) -> Page:
        """Opens an address, or searches for words; returns the page (no check: `go` is the one that asks)."""
        with self.lock:
            url = address_for(target)
            self._driver().open(url)
            if self.teaching is not None and not self.teaching["steps"]:
                self.teaching["start"] = url
            return self.refresh()

    def read(self, controls: bool = True) -> str:
        """The page now for the model: its title and address, its text (framed as untrusted), and its numbered
        controls."""
        with self.lock:
            if self.driver is None:
                return "MIA's browser isn't open. Ask her to open a page first."
            page = self.refresh()
            lines = [f"Page: {page.title or '(untitled)'} ({page.url})", untrusted(page.text, page.url)]
            if controls and page.controls:
                lines.append("Controls on the page:\n" + "\n".join(describe_control(c) for c in page.controls))
            return "\n".join(lines)

    def glance(self) -> str:
        """The page in a few lines: its title, address and how it begins (framed as untrusted)."""
        page = self.page
        return f"{page.title or '(untitled)'} ({page.url})\n" + untrusted(page.text, page.url, limit=1200)

    # -------------------------------------------------------------- acting

    def _control(self, which) -> Optional[Control]:
        """A control by number, or by the name a person would call it."""
        if which is None or which == "":
            return None
        found = self.page.control(which)
        return found if found is not None else self.page.find(str(which))

    def do(self, kind: str, which=None, text: str = "", routine: Optional[dict] = None) -> dict:
        """One step: click, type, select or press on a control (by number or name), or back. Sorted by
        classify(): done now when it's safe, refused when it's a secret, and waiting for the person (a Pending,
        proposed for approval) when it commits, or when it would type or choose words the person didn't say
        (DEC-0122). Returns {done, said, pending}."""
        with self.lock:
            if kind == "back":
                self._driver().back()
                self.refresh()
                return {"done": True, "said": "Went back. " + self.glance(), "pending": None}
            if self.driver is None:
                return {"done": False, "said": "MIA's browser isn't open.", "pending": None}
            if not self.page.controls:
                self.refresh()
            control = self._control(which)
            if control is None:
                return {"done": False, "said": f"I can't find \"{which}\" on this page.", "pending": None}
            verdict = classify(kind, control)
            if verdict.level == ACT and kind in ("type", "select") and not self.authorized(text, routine):
                verdict = Verdict(COMMIT, "those words didn't come from you")
            if verdict.level == NEVER:
                return {"done": False, "pending": None,
                        "said": f"I won't type into \"{control.name}\": {verdict.why}. You can do it in my window."}
            if verdict.level == COMMIT:
                pending = self._hold(kind, control, text, verdict, routine)
                return {"done": False, "pending": pending,
                        "said": f"That needs your OK: {pending.summary()}. Say yes, or approve it on screen."}
            self._perform(kind, control, text)
            return {"done": True, "pending": None, "said": f"Done ({verdict.why}). " + self.glance()}

    def _perform(self, kind: str, control: Control, text: str) -> None:
        """Does a step on the page and reads it again."""
        driver = self._driver()
        if kind == "click":
            driver.click(control.ref)
        elif kind == "type":
            driver.type(control.ref, text)
        elif kind == "select":
            driver.select(control.ref, text)
        elif kind == "press":
            driver.press(control.ref, "Enter")
        else:
            raise BrowserError(f"I don't know how to {kind}.")
        self.refresh()

    def _shot(self, name: str) -> str:
        """A screenshot of the page now in her shots folder; "" when it can't be taken."""
        try:
            return str(self._driver().screenshot(self.profile_dir.parent / "browser_shots" / f"{name}.png"))
        except Exception:
            log.exception("Browser screenshot failed.")
            return ""

    def _hold(self, kind: str, control: Optional[Control], text: str, verdict: Verdict,
              routine: Optional[dict]) -> Pending:
        """Keeps a step that waits for the person, with a screenshot, and proposes it as browser.commit."""
        self._expire()
        pending_id = uuid.uuid4().hex[:10]
        pending = Pending(pending_id, kind, control, text, self.page.url, self.page.title, verdict.why,
                          screenshot=self._shot(pending_id), routine=routine)
        self.pending[pending_id] = pending
        actions = getattr(self.context, "actions", None)
        if actions is not None:
            try:
                proposal = actions.propose(self.context, "browser.commit", {"pending_id": pending_id}, proposed_by="mia")
                pending.proposal_id = proposal.proposal_id
            except Exception:
                log.exception("Proposing a browser step failed.")
        return pending

    def ask_signin(self, routine: Optional[dict] = None) -> Pending:
        """A routine reached a sign-in: waits for the person to sign in themselves, then carries on."""
        return self._hold("signin", None, "", Verdict(COMMIT, "you sign in yourself"), routine)

    def _expire(self) -> None:
        """Lets go of steps nobody approved in time."""
        cutoff = time.time() - PENDING_MINUTES * 60
        for key in [k for k, p in self.pending.items() if p.at < cutoff]:
            self.pending.pop(key, None)

    def perform_pending(self, pending_id: str) -> str:
        """The person approved a waiting step: it's done now (a sign-in just carries on), the routine it belongs to
        continues; a held address is opened. Returns what happened."""
        with self.lock:
            pending = self.pending.pop(pending_id, None)
            if pending is None:
                raise BrowserError("That step isn't waiting any more.")
            if pending.kind == "open":
                self.open(pending.text)
            elif pending.kind != "signin":
                page = self.refresh()
                if page.url != pending.page_url:
                    raise BrowserError("The page changed since I asked, so I didn't press anything.")
                control = page.find(pending.control.name, pending.control.role) if pending.control else None
                if control is None:
                    raise BrowserError("That button isn't on the page any more.")
                self._perform(pending.kind, control, pending.text)
            said = f"Done: {pending.summary()}. " + self.glance()
            if pending.routine:
                from core.browser_routines import carry_on

                said += "\n" + carry_on(self.context, self, pending.routine)
            return said

    # -------------------------------------------------------------- the live view inside MIA (2026-11-07)

    def frame(self) -> Optional[bytes]:
        """What her browser shows now, as a JPEG for the Browser page's live view; None when it's closed."""
        if self.driver is None:
            return None
        with self.lock:
            return self.driver.frame()

    def viewport(self) -> tuple[int, int]:
        """The page's size in its own pixels, so a click on the live view lands in the same place."""
        if self.driver is None:
            return (VIEW_W, VIEW_H)
        with self.lock:
            return self.driver.viewport()

    def person(self, kind: str, x: float = 0, y: float = 0, text: str = "", key: str = "", dy: float = 0) -> None:
        """The person operating her browser from the live view: a click, typing, one of PERSON_KEYS, or a scroll. It's
        their own hands, so no gate applies, and teaching records it as if done in a window. What they type isn't
        heard as words MIA may type later (it may be a password). BrowserError when it's closed or not one of these."""
        if self.driver is None:
            raise BrowserError("MIA's browser is closed. Open a website first.")
        if kind not in ("click", "type", "key", "scroll") or (kind == "key" and key not in PERSON_KEYS):
            raise BrowserError("That isn't something the live view can do.")
        with self.lock:
            self.driver.person(kind, x, y, (text or "")[:2000], key, dy)
            self.refresh()

    def describe_pending(self, pending_id: str) -> str:
        """The sentence for a waiting step's approval; BrowserError when it isn't waiting."""
        pending = self.pending.get(pending_id)
        if pending is None:
            raise BrowserError("That step isn't waiting any more.")
        return pending.summary()

    def close(self) -> str:
        """Closes her browser (a teaching session is dropped)."""
        with self.lock:
            self.teaching = None
            if self.driver is not None:
                self.driver.on_record(None)
                self.driver.close()
                self.driver = None
            self.page, self.pending = Page(), {}
            return "Closed my browser."


class Browsers:
    """Every person's browser session (`context.browsers`): one each, its profile in that person's own folder, so
    the sites they sign her into are theirs."""

    def __init__(self, context, driver_factory: Optional[Callable[[Path], Driver]] = None,
                 root: Optional[Path] = None) -> None:
        """No sessions yet; where profiles go when a person has no folder of their own."""
        self.context = context
        self.factory = driver_factory
        self.root = Path(root) if root is not None else Path(__file__).resolve().parent.parent / "data" / "browser"
        self.sessions: dict[str, Browser] = {}

    def folder(self, person: Optional[str]) -> Path:
        """Where a person's browser profile lives: their own folder, else the device's."""
        personal = getattr(self.context, "personal_data", None)
        if personal is not None and person:
            try:
                return Path(personal.folder(person)) / "browser" / "profile"
            except Exception:
                pass
        return self.root / (person or "device") / "profile"

    def for_person(self, context) -> Browser:
        """The signed-in person's browser session (made the first time)."""
        from core.person_settings import person_id

        person = person_id(context) or ""
        if person not in self.sessions:
            self.sessions[person] = Browser(context, self.folder(person), self.factory)
        return self.sessions[person]

    def find_pending(self, pending_id: str) -> Optional[Browser]:
        """The session a waiting step belongs to."""
        return next((b for b in self.sessions.values() if pending_id in b.pending), None)

    def close_all(self) -> None:
        """Closes every open browser (when MIA quits)."""
        for browser in self.sessions.values():
            try:
                browser.close()
            except Exception:
                log.exception("Closing a browser failed.")


def yes_to_waiting(context, last_reply: str) -> Optional[str]:
    """A plain "yes" approves the browser step MIA just asked about, in code, never by the model: only the person's
    newest waiting step, only when MIA's last reply named it (its button, or signing in), and through the action
    center as that person. Returns what happened, or None when the yes wasn't about her browser."""
    hub, actions = getattr(context, "browsers", None), getattr(context, "actions", None)
    browser = hub.for_person(context) if hub is not None and actions is not None else None
    if browser is None or not browser.pending or not last_reply:
        return None
    browser._expire()
    newest = max(browser.pending.values(), key=lambda p: p.at, default=None)
    if newest is None or not newest.proposal_id:
        return None
    reply = last_reply.lower()
    named = (newest.control.name if newest.control else "") or ""
    if not (named and named.lower() in reply or newest.kind == "signin" and "sign in" in reply):
        return None
    try:
        proposal = actions.approve(context, newest.proposal_id)
    except (KeyError, ValueError):
        return None
    return proposal.result


def browser_for(context) -> Optional[Browser]:
    """The person's browser session, or None where MIA has no browser."""
    hub = getattr(context, "browsers", None)
    return hub.for_person(context) if hub is not None else None


def _words_of(text: str) -> set:
    """Pure logic. A text's words for comparing whose they are: lowercase letters and digits, anything else a
    break."""
    return set(re.findall(r"[a-z0-9]+", (text or "").lower()))
