#!/bin/bash
# 11단계 — 푼 코드(worktree /tmp/v25)로 UI 24 · slow 14 를 순차로. 표식 파일만 기다린다.
R=/home/user/AI-P-ID-Extraction-tool
cd /tmp/v25
PID_UI_DB="$R/out/round25/ui.db" timeout 1800 python3 -m pytest -q -m ui -p no:cacheprovider > "$R/out/round25/verify_ui.log" 2>&1
echo $? > "$R/out/round25/verify_ui.rc"; echo DONE > "$R/out/round25/verify_ui.done"
timeout 3600 python3 -m pytest -q -m slow -p no:cacheprovider > "$R/out/round25/verify_slow.log" 2>&1
echo $? > "$R/out/round25/verify_slow.rc"; echo DONE > "$R/out/round25/verify_slow.done"
