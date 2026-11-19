#!/bin/bash
# Required (FW-04): the people's homes are there and can be written, where MIA keeps their data.
set -eu
test -d /var/home && test -w /var/home || { echo "/var/home isn't there or can't be written." >&2; exit 1; }
