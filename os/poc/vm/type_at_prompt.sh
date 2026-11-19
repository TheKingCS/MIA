#!/bin/bash
# os/poc/vm/type_at_prompt.sh: waits for a prompt to show in the VM's serial log, then types the words and Enter on the
# VM's serial line (FW-05's disk prompts). The serial line is the system console in the test image, so the boot's
# prompt listens there whether or not a splash screen is running; the VM's own keyboard isn't always heard.
# Usage: [SINCE=n] type_at_prompt.sh PATTERN WORDS [SECONDS]
#   PATTERN  a grep pattern for the prompt; SINCE how many matches were already in the log (default: those there now;
#            0 after a fresh QEMU, whose log starts empty, so a prompt that came before this was called still counts).
# Exit 1 when the prompt doesn't show in time.
pattern="$1"; words="$2"; wait="${3:-300}"
count() { grep -c -- "$pattern" /tmp/serial.log 2>/dev/null || true; }
since="${SINCE:-$(count)}"
for i in $(seq 1 "$wait"); do
  now=$(count)
  [ "${now:-0}" -gt "${since:-0}" ] && break
  sleep 1
done
[ "${now:-0}" -gt "${since:-0}" ] || { echo "No prompt matching '$pattern' in ${wait}s." >&2; exit 1; }
sleep 2
printf '%s\r' "$words" | socat - UNIX-CONNECT:/tmp/serial.sock
echo "Typed at the prompt matching '$pattern'."
