# Field Kit: Devices, Scripts, and Security Tools

## Device Manager

Field Kit detects connected external USB storage and serial/MCU
devices. For each one you can browse its files or eject it safely.
Flashing an OS image onto another device is designed but not yet
available for general use.

## Scripts

Save your own scripts in the Scripts library and run them from here —
useful for repeatable field diagnostics or setup tasks. Output streams
live while a script runs, and a Stop button cleanly kills it (including
anything the script itself spawned).

## Security tools

The Security tab covers device-testing tools that need no special
hardware or system installs:

- **Hash Identifier** — guess the likely algorithm(s) behind a hash
  string (MD5, bcrypt, etc.).
- **Password Strength** — an entropy-based strength rating with
  specific warnings.
- **Subnet Calculator** — network address, broadcast, netmask, and
  usable host range from a CIDR block.
- **Port Scanner** — a quick TCP connect-scan of common ports.

Heavier tools (packet crafting, hash cracking, a Wi-Fi analyzer) need
system binaries and root access this device doesn't have — they're not
available yet.
