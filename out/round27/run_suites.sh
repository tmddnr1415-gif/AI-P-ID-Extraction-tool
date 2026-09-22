#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
PID_UI_DB="$PWD/out/round25/ui.db" timeout 1800 python3 -m pytest -q -m ui -p no:cacheprovider > out/round27/ui.log 2>&1
echo $? > out/round27/ui.rc
timeout 4800 python3 -m pytest -q -m slow -p no:cacheprovider > out/round27/slow.log 2>&1
echo $? > out/round27/slow.rc
echo DONE > out/round27/suites.done
