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

# ---- MIA's own model (docs/PHONE_MODEL_TEST.md) ----------------------------
api() { curl -s -H "Authorization: Bearer $token" -H "Content-Type: application/json" "$@"; }
field() { python3 -c "import json,sys; d=json.load(sys.stdin); print(eval(sys.argv[1], {}, {'d': d}))" "$1"; }
echo "model test available: $(api http://127.0.0.1:8765/api/model-test | field "d['available']")" | tee -a "$OUT/timings.txt"
libdir=$(adb shell pm path com.mia.phone | tr -d '\r' | sed 's|package:||; s|base.apk||')lib/x86_64
adb shell "$libdir/libllama_server.so --version" 2>&1 | tail -2 | tee -a "$OUT/timings.txt"
if [ -n "${MODEL_FILE:-}" ] && [ -f "$MODEL_FILE" ]; then
  # The model a phone would download, put where the app keeps it.
  adb push "$MODEL_FILE" /data/local/tmp/model.gguf > /dev/null
  adb shell run-as com.mia.phone mkdir -p files/mia/data/models
  adb shell run-as com.mia.phone cp /data/local/tmp/model.gguf "files/mia/data/models/$(basename "$MODEL_FILE")"
  adb shell rm /data/local/tmp/model.gguf
  api -d "{\"model\":\"$MODEL_ID\"}" http://127.0.0.1:8765/api/model-test/start > /dev/null
  state=""
  for i in $(seq 1 150); do
    state=$(api http://127.0.0.1:8765/api/model-test | field "d['server']['state']")
    [ "$state" = ready ] || [ "$state" = error ] && break
    sleep 2
  done
  api http://127.0.0.1:8765/api/model-test | field "d['server']" | tee -a "$OUT/timings.txt"
  [ "$state" = ready ] || exit 1
  # The emulator has few, slow cores: two cases show the whole chain works.
  # Speed is the real phone's to measure.
  api -d '{"count":2}' http://127.0.0.1:8765/api/model-test/run > /dev/null
  for i in $(seq 1 360); do
    done_=$(api http://127.0.0.1:8765/api/model-test | field "d['run'].get('finished')")
    [ "$done_" = True ] && break
    sleep 5
  done
  api http://127.0.0.1:8765/api/model-test | field "d['run']" | tee -a "$OUT/timings.txt"
  adb shell run-as com.mia.phone tail -c 1500 files/mia/data/models/server.log > "$OUT/llama-server.log" 2>&1 || true
  api http://127.0.0.1:8765/api/model-test | field "[m['results'] and {k: m['results'][k] for k in ('done','passed','median_seconds','read_per_second','write_per_second','load_seconds')} for m in d['models'] if m['id']=='$MODEL_ID'][0]" | tee -a "$OUT/timings.txt"
  passed=$(api http://127.0.0.1:8765/api/model-test | field "[m['results']['done'] for m in d['models'] if m['id']=='$MODEL_ID' and m['results']][0]") || exit 1
  [ "$passed" -ge 1 ] || exit 1
  # Talk on the phone now answers from the phone's own model.
  api --max-time 900 -d '{"text":"Say hello in five words."}' http://127.0.0.1:8765/api/voice/text | head -c 400 | tee -a "$OUT/timings.txt"; echo
fi
