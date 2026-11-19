#!/bin/bash
# os/poc/vm/type_at_prompt.sh: waits for a prompt to show in the VM's serial log, then types the words at the VM's
# keyboard through QEMU's monitor and presses Enter (FW-05's disk prompts). Usage: type_at_prompt.sh PATTERN WORDS
# [SECONDS]. Exit 1 when the prompt doesn't show in time. Letters, digits and '-' only (a recovery key, a PIN).
pattern="$1"; words="$2"; wait="${3:-300}"; seen_before=$(grep -c -- "$pattern" /tmp/serial.log 2>/dev/null || true)
for i in $(seq 1 "$wait"); do
  now=$(grep -c -- "$pattern" /tmp/serial.log 2>/dev/null || true)
  [ "${now:-0}" -gt "${seen_before:-0}" ] && break
  sleep 1
done
[ "${now:-0}" -gt "${seen_before:-0}" ] || { echo "No prompt matching '$pattern' in ${wait}s." >&2; exit 1; }
sleep 2
for (( i=0; i<${#words}; i++ )); do
  c="${words:$i:1}"
  case "$c" in -) k=minus ;; *) k="$c" ;; esac
  printf 'sendkey %s\n' "$k" | socat - UNIX-CONNECT:/tmp/mon.sock > /dev/null
  sleep 0.1
done
printf 'sendkey ret\n' | socat - UNIX-CONNECT:/tmp/mon.sock > /dev/null
echo "Typed at the prompt matching '$pattern'."
