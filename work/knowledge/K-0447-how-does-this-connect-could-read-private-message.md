---
id: K-0447
kind: security-finding
title: How does this connect could read private messages
status: confirmed
by: claude
created: 2026-11-24T18:21:11+00:00
concerns: core/ual.py, core/library_course.py
from: commit:d57954f6, commit:bdac7785
---
Review of d57954f6: talking_about took every user message in the active conversation, so after a journal or off-the-record stretch the connect action sent that text to the model, which could repeat it in a saved reply. Now a message with privacy set is skipped, and a conversation that is private, journal, off the record or in a personal mode gives nothing. Record titles in its prompt are framed as outside content. Same review: learn_about's course fit needed only one shared word (now the title holds the whole subject or the text two thirds of its words), the same course twice was made twice, a lesson for a course nobody named taught the newest quietly, the two lesson tools now name each other, and "how can I use this" went to the help pages (that trigger dropped).
