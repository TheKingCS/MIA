"""
core.plain_words
==================

Markdown out of what MIA says (2026-10-30). Models write **bold**,
### headings and `code`, which the desktop's chat bubbles show as
asterisks and hashes and the voice reads as noise. Pure logic.

- `strip_markdown(text)`: for the screen: the markers go, the words and
  any "- " list lines stay.
- `for_speech(text)`: for the voice: the same, and list lines become
  sentences.
"""

from __future__ import annotations

import re

_HEADING = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_BOLD = re.compile(r"(\*\*|__)(.+?)\1", re.DOTALL)
_ITALIC = re.compile(r"(?<![\w*])\*(?!\s)([^*\n]+?)(?<!\s)\*(?![\w*])")
_CODE = re.compile(r"`([^`]*)`")
_RULE = re.compile(r"^\s*(-{3,}|\*{3,}|_{3,})\s*$", re.MULTILINE)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)


def strip_markdown(text: str) -> str:
    out = _RULE.sub("", text or "")
    out = _HEADING.sub("", out)
    out = _BOLD.sub(r"\2", out)
    out = _ITALIC.sub(r"\1", out)
    out = _CODE.sub(r"\1", out)
    out = re.sub(r"^\s*\*\s+", "- ", out, flags=re.MULTILINE)  # "* item" lists read as "- item"
    return re.sub(r"\n{3,}", "\n\n", out).strip()


def for_speech(text: str) -> str:
    lines = [ln for ln in (_BULLET.sub("", line).strip() for line in strip_markdown(text).splitlines()) if ln]
    if len(lines) <= 1:
        return lines[0] if lines else ""
    return " ".join(ln if ln[-1] in ".!?:;" else ln + "." for ln in lines)  # lines joined become sentences
