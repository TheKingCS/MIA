#!/bin/bash
# Required (FW-04): at least 2 GB free where the homes are, so MIA and an update have room.
set -eu
free_kb=$(df --output=avail -k /var/home | tail -n 1 | tr -d ' ')
[ "$free_kb" -ge $((2 * 1024 * 1024)) ] || { echo "Only $((free_kb / 1024)) MB free under /var/home." >&2; exit 1; }
