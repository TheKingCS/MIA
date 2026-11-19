#!/bin/bash
# Required (FW-04): the login screen came up, so he can sign in to MIA or to Plasma. A failure rolls the update back.
set -eu
for i in $(seq 1 60); do
  systemctl is-active --quiet display-manager.service && exit 0
  sleep 2
done
echo "The login screen (display-manager.service) isn't running." >&2
exit 1
