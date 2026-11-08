# Looking things up online (DEC-0053)

MIA looks something up on the internet only when the computer is online,
the question needs facts her records and offline packs don't have, and you
asked or said yes when she offered ("I'd need to look that up online. Want
me to?"). Only the search words leave the computer: never your records, and
never an email, a long number or anything after "password"
(`core/online_lookup.py`, `scrub()`). Every fact she found is said with its
source and the date, kept apart from her own reasoning, and never as a
legal or tax ruling. Off on a child's account.

## Her search engine: SearXNG, on this computer

Zac's choice (2026-10-31): a search engine you host yourself, so there's no
account and no tracking. MIA searches it at `http://127.0.0.1:8888` unless
the config says otherwise (`online.searxng_url`); she won't use one that
isn't on this computer or your home network.

To start it (once, at the PC):

1. Install Docker Desktop (or use WSL with Docker in it).
2. Run SearXNG on port 8888:
   `docker run -d --name searxng --restart unless-stopped -p 127.0.0.1:8888:8080 searxng/searxng`
3. Let it answer in JSON: in the container's `/etc/searxng/settings.yml`,
   under `search:`, set `formats: [html, json]`, then
   `docker restart searxng`.
4. Check it: `http://127.0.0.1:8888/search?q=test&format=json` shows results.

Until it's running, a lookup says SearXNG isn't answering and points here.
Turning lookups off: `online.lookup` false in the config.

## Not built yet

- The voice tool and a screen control (the parity and design sessions').
- A company's search API as the fallback (approved, but it needs an
  account and a key nobody has set up).
