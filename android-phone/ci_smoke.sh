#!/usr/bin/env bash
# The phone spike's check on an Android emulator (DEC-0019): install the
# app, start it, wait for MIA's engine and server, call her API and her
# screens from the "phone", take a screenshot, note memory. Fails if MIA
# doesn't come up.
set -u
APK=android-phone/app/build/outputs/apk/debug/app-debug.apk
OUT=spike-report
mkdir -p "$OUT"
adb install -r "$APK" || exit 1
adb logcat -c
adb shell am start -n com.mia.phone/.MainActivity
ready=""
for i in $(seq 1 120); do
  ready=$(adb logcat -d -s MIA_SPIKE:I | grep "ready" | tail -1)
  [ -n "$ready" ] && break
  if adb logcat -d -s MIA_SPIKE:E | grep -q "failed"; then break; fi
  sleep 2
done
adb logcat -d > "$OUT/logcat.txt"
grep -A40 "MIA_SPIKE" "$OUT/logcat.txt" | head -80 > "$OUT/mia_spike_log.txt"
if [ -z "$ready" ]; then
  echo "MIA did not start on the emulator:"; cat "$OUT/mia_spike_log.txt"; grep -i "python\|Traceback\|Error" "$OUT/logcat.txt" | tail -60
  exit 1
fi
echo "$ready" | tee "$OUT/timings.txt"
token=$(adb logcat -d -s MIA_SPIKE:D | grep -o "token=[A-Za-z0-9_-]*" | tail -1 | cut -d= -f2)
adb forward tcp:8765 tcp:8765
if [ -z "$token" ]; then
  # First start: no account yet, so make one the way a person would (onboarding).
  setup=$(curl -s -H "Content-Type: application/json" \
    -d '{"name":"Robin","email":"robin@example.com","password":"phone-test","country":"US","interests":[]}' \
    http://127.0.0.1:8765/api/setup)
  echo "setup: $(echo "$setup" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('name'), bool(d.get('recovery_code')))")" | tee -a "$OUT/timings.txt"
  token=$(echo "$setup" | python3 -c "import json,sys; print(json.load(sys.stdin)['token'])") || exit 1
fi
for path in /web/index.html /api/shell /api/dashboard /api/missions /api/skills /api/money; do
  code=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $token" "http://127.0.0.1:8765$path")
  echo "$code $path" | tee -a "$OUT/timings.txt"
  [ "$code" = "200" ] || exit 1
done
proposal=$(curl -s -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
  -d '{"kind":"mission.add","params":{"name":"Hello from the phone","reward_xp":"10"}}' http://127.0.0.1:8765/api/actions/propose)
pid=$(echo "$proposal" | python3 -c "import json,sys; print(json.load(sys.stdin)['proposal_id'])") || exit 1
curl -s -H "Authorization: Bearer $token" -X POST "http://127.0.0.1:8765/api/actions/$pid/approve" | tee -a "$OUT/timings.txt"; echo
sleep 8
adb exec-out screencap -p > "$OUT/screen.png"
adb shell dumpsys meminfo com.mia.phone | grep -i "TOTAL PSS\|TOTAL:" | head -3 | tee -a "$OUT/timings.txt"
ls -la "$APK" | awk '{print "apk_bytes " $5}' | tee -a "$OUT/timings.txt"
