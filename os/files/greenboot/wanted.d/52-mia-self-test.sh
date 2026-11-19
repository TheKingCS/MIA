#!/bin/bash
# Wanted (FW-04): MIA's self-test, as a throwaway user on an empty folder: it never sees anyone's home.
systemd-run --wait --pipe --quiet -p DynamicUser=yes -p ProtectHome=yes -p StateDirectory=mia-self-test \
  -p WorkingDirectory=/usr/lib/mia -E QT_QPA_PLATFORM=offscreen \
  /usr/lib/mia/venv/bin/python -m core.self_test --home /var/lib/mia-self-test/run-$(date +%s)
