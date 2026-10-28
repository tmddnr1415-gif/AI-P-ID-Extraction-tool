#!/bin/sh
PID_UI_DB="$PWD/out/round24/ui.db" timeout 1800 python3 -m pytest -q -m ui > out/round24/ui.log 2>&1
echo $? > /tmp/ui.done
