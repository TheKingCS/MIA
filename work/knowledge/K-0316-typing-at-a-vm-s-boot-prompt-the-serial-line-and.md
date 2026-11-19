---
id: K-0316
kind: test-procedure
title: Typing at a VM's boot prompt: the serial line, and the prompt's real words
status: confirmed
by: claude
created: 2026-11-19T20:11:46+00:00
concerns: os/poc/vm/type_at_prompt.sh, .github/workflows/mia-os-encryption.yml
from: commit:f07ab33c, commit:0c9b8cda, task:FW-05
---
FW-05's VM test types at disk prompts. What worked: console=tty0 console=ttyS0 as kernel arguments (serial last, so it is the system console), QEMU's serial as a socket chardev with logfile=, wait for the prompt's text in the log, then write the words and a carriage return to the socket (os/poc/vm/type_at_prompt.sh). A fresh QEMU truncates the log, so count matches from 0 then; within one QEMU take the count before the reboot. Check the words a tool really prints before asserting on them: systemd says 'recovery key for' when no passphrase slot is left, and mokutil says 'This system doesn't support Secure Boot' on firmware without it; both cost a two-hour run. A push touching os/ and the daily schedule each cancel the main VM run in progress.
