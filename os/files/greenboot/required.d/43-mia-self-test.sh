#!/bin/bash
# Required (FW-04): MIA's self-test. An update whose MIA fails it is rolled back. It runs as nobody, on a fresh empty
# folder, so it can't read anyone's home (they're private to their owners); it needs no network and no model server.
set -u
dir=$(mktemp -d /var/tmp/mia-self-test.XXXXXX) || exit 1
chown 65534:65534 "$dir"
cd /usr/lib/mia || exit 1
setpriv --reuid=65534 --regid=65534 --clear-groups --inh-caps=-all \
  env -i PATH=/usr/bin:/bin HOME="$dir" QT_QPA_PLATFORM=offscreen \
  /usr/lib/mia/venv/bin/python -m core.self_test --home "$dir/home"
code=$?
rm -rf "$dir"
exit $code
