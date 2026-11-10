---
id: K-0213
kind: implementation
title: Copy on a web page: select-and-copy inside the click first, the clipboard API second
status: confirmed
by: claude
created: 2026-11-10T23:38:37+00:00
concerns: web/shell.js, web/assistant.js, web/concept.css, modules/web_home/module.py
from: file:docs/CONVERSATION_REVIEW.md, file:web/shell.js, file:docs/specs/CONVERSATION.md
---
MIAShell.copy(text, button) and MIAShell.copyButton(text or a function, label) in web/shell.js are the one way a page copies. It puts the text in an off-screen textarea (.copy-box), selects it and runs document.execCommand("copy") inside the click that asked; only if that fails does it try navigator.clipboard.writeText. That order is deliberate: the selection way needs no permission and works in the desktop window (QtWebEngine with its default settings, where only the microphone is granted) and the phone's WebView, where the clipboard API is refused or absent. Checked two ways without a visible window: headless Edge at three widths, and an offscreen QtWebEngine page whose click put the text on the system clipboard. The button says "Copied" with a tick for a moment; if both ways fail she says to select the text. For the same reason export is Copy and Save to Files, not a download: a blob download does nothing in the desktop window or the phone app. The chat page's width: .chat-main has no cap and one message stops at min(88%, 1100px); the tools row under her answer (Copy, thumbs) is offset only when the bubble has an avatar.
