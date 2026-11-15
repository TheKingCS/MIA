---
id: K-0235
kind: implementation
title: Sealed files on Linux: the data key wrapped under a secret systemd keeps
status: confirmed
by: claude
created: 2026-11-15T14:08:21+00:00
concerns: core/at_rest.py, core/key_unlock.py, tools/data_key.py, core/runtime.py, deploy/install_runtime.sh, deploy/mia-runtime.service, tools/move_home.py
from: dec:DEC-0126, dec:DEC-0168, dec:DEC-0169
---
What: on Linux there's no DPAPI, so core/at_rest.py wraps the data key (scrypt n=2^17, AES-256-GCM, the key's id bound in) under an unlock secret. core/key_unlock.py is the only place that knows where the secret is: a systemd credential (systemd-creds --user, systemd 256+), encrypted for this user on this machine with the TPM where there is one. The service gets it from $CREDENTIALS_DIRECTORY (LoadCredentialEncrypted= in deploy/mia-runtime.service); a terminal asks systemd-creds to decrypt the same file. python -m tools.data_key protect makes it once; restore takes a recovery key.

How the key file changed: each entry may say how it's protected ("by"; none means DPAPI). A system opens only its own kind and keeps the others untouched, in _open_keys and in restore. So a key file copied from Windows is never replaced on Linux (it's blocked until the recovery key is restored, which adds a "secret" entry beside the DPAPI one), and Windows still opens a file Linux added to.

Why this way: it matches DEC-0126's choice on Windows (nothing typed at start, useless elsewhere), and a headless service can't ask for a passphrase. A typed passphrase is stronger on a Pi with no TPM and no disk encryption (there the machine's key is on the same drive) and is left to Zac (DEC-0169).

What went wrong or nearly did: (1) With sealing blocked, a store whose sealed file won't open starts empty and its next save writes a plain file over it (the copy aside saves the content). With no window nobody sees that, so core.runtime.main() now asks at_rest.start_problem() first and exits 3: a key file that won't open, or sealed files whose key id isn't held (data copied without restoring the key). (2) tools/data_key.py still built its folder from the code's root after MIA_HOME; it now uses DATA_DIR. (3) An existing credential file is never replaced by make(), even one that won't open, and a new one that doesn't read back is removed: replacing it would lock every sealed file. (4) A cut-off secret (under 16 bytes) is refused rather than used to wrap a key. (5) The secret and the recovery key never go on a command line: systemd-creds gets the secret on stdin, restore asks with getpass.

Testing: tests/test_key_unlock.py forces the "secret" kind on any system (monkeypatch at_rest.dpapi_available and at_rest._unlock_secret, and SCRYPT to a quick cost) and stands in for systemd-creds by replacing key_unlock._run. Not yet run against real systemd: the first run on Fedora or the Pi must check systemd-creds --user and LoadCredentialEncrypted in a user unit.
