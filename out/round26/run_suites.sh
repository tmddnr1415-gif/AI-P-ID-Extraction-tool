#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 600 python3 -m pytest -q -m "not slow and not ui" -p no:cacheprovider > out/round26/fast.log 2>&1
echo $? > out/round26/fast.rc
PID_UI_DB="$PWD/out/round25/ui.db" timeout 1800 python3 -m pytest -q -m ui -p no:cacheprovider > out/round26/ui.log 2>&1
echo $? > out/round26/ui.rc
timeout 4800 python3 -m pytest -q -m slow -p no:cacheprovider > out/round26/slow.log 2>&1
echo $? > out/round26/slow.rc
echo DONE > out/round26/suites.done
