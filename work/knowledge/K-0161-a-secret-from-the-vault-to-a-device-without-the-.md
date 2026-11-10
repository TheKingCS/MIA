---
id: K-0161
kind: implementation
title: A secret from the vault to a device without the model or a log ever holding it
status: confirmed
by: claude
created: 2026-11-09T05:25:19+00:00
concerns: core/greenhouse_provision.py, core/greenhouse_setup.py, tests/test_greenhouse_secret.py
from: dec:DEC-0150
---
DEC-0150, 2026-11-09. greenhouse_provision.push_secret reads the login's password from context.passwords only when the person has unlocked it (MIA never calls unlock), and passes it to ssh as standard input (_run_input), never as an argument (a process list would show it). The remote side is a small Python script (_SET_SECRET) with no backslashes and no single quotes so it survives the remote shell, which sets smtp_password, keeps the line's comment, chmods 600 and prints only 'set'. Whatever the command prints comes back with the secret replaced by [hidden] in push_secret itself, so an injected runner can't leak it (a test caught the first version hiding it only in the default runner). Every sentence about it is said in code and names the vault login by title. Tests run the remote script in-process (exec with stdin and cwd patched) rather than starting a Python.
