"""Copies MIA's glasses interface to the public page (DEC-0062).

web/glasses.* stays the one source. The page in the mia-art repo is that
interface with pairing added and boot.js in place of mia.js, so it reaches
the engine only through the sealed relay. Nothing here may hold data.

    python -m tools.publish_glasses <mia-art folder>

Then commit and push mia-art.
"""

import re
import shutil
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent / "web"
COPIED = ("glasses.js", "glasses.css", "icons.js")

HEAD = """  <meta name="application-name" content="MIA">
  <meta name="description" content="MIA on Meta Ray-Ban Display glasses">
  <meta name="mrbd-web-app-capable" content="yes">
"""

# Her touchscreen arrows aren't for the glasses, and pairing sits over her until it's done.
STYLE = """  <style>
    .edge { display: none; }
    #pairing { position: fixed; inset: 0; z-index: 9; background: #000; color: #dff6ff; display: grid; align-content: center; justify-items: center; gap: 18px; padding: 32px; text-align: center; font: 22px/1.3 system-ui, sans-serif; }
    #pairing[hidden], #pairing [hidden] { display: none; }
    #big { font-size: 56px; letter-spacing: 6px; color: #a6ecff; }
    #sure { display: flex; gap: 12px; }
    #pairing button { font: inherit; color: #dff6ff; background: transparent; border: 2px solid rgba(53,212,255,.45); border-radius: 12px; padding: 8px 14px; }
    #pairing button:focus { outline: 3px solid #35d4ff; }
  </style>
"""

PAIRING = """  <section id="pairing" hidden aria-live="polite">
    <div id="big"></div>
    <div id="facts"></div>
    <div id="sure" hidden>
      <button id="match" type="button">They Match</button>
      <button id="differ" type="button">They Don't</button>
    </div>
    <button id="wait" type="button" hidden>Keep Waiting</button>
    <button id="restart" type="button" hidden>Pair Again</button>
  </section>
  <script type="module" src="boot.js"></script>
"""


def page() -> str:
    html = (WEB / "glasses.html").read_text(encoding="utf-8")
    html = re.sub(r'\s*<script src="[^"]*"></script>', "", html)
    html = re.sub(r'href="glasses\.css\?v=\d+"', 'href="glasses.css"', html)
    html = html.replace("<title>MIA · Glasses</title>", "<title>MIA</title>")
    html = html.replace("</head>", HEAD + STYLE + "</head>")
    return html.replace("</body>", PAIRING + "</body>")


def main(folder: str) -> None:
    out = Path(folder)
    for name in COPIED:
        shutil.copyfile(WEB / name, out / name)
    (out / "index.html").write_text(page(), encoding="utf-8", newline="\n")
    print("Published to", out)


if __name__ == "__main__":
    main(sys.argv[1])
