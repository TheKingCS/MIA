#!/bin/bash
# Advisory (FW-04): the network. Logged, never a rollback: MIA works offline.
nm-online -q -t 30 || { echo "No network yet (MIA works without it)." >&2; exit 1; }
