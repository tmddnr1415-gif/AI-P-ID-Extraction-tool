#!/bin/bash
# 이 스크립트가 UI 스위트를 돌리고 끝에 표식을 남긴다.
# 기다리는 쪽은 **이 표식 파일**을 보면 되고, 프로세스 이름을 찾지 않는다.
cd /home/user/AI-P-ID-Extraction-tool
export PID_UI_DB="$PWD/out/round23/ui_db/app.db"
timeout 1500 python3 -m pytest -q -m ui > out/round23/ui.log 2>&1
echo $? > out/round23/ui.rc
