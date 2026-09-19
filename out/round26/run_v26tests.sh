#!/bin/bash
R=/home/user/AI-P-ID-Extraction-tool
cd /tmp/v26
timeout 600 python3 -m pytest -q -m "not slow and not ui" -p no:cacheprovider > "$R/out/round26/v26_fast.log" 2>&1
echo $? > "$R/out/round26/v26_fast.rc"
PID_UI_DB="$R/out/round25/ui.db" timeout 1800 python3 -m pytest -q -m ui -p no:cacheprovider > "$R/out/round26/v26_ui.log" 2>&1
echo $? > "$R/out/round26/v26_ui.rc"
timeout 4800 python3 -m pytest -q -m slow -p no:cacheprovider > "$R/out/round26/v26_slow.log" 2>&1
echo $? > "$R/out/round26/v26_slow.rc"
echo DONE > "$R/out/round26/v26tests.done"
