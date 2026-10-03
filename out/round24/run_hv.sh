#!/bin/sh
# 대기 표식 방식 (§8) — 프로세스 이름으로 기다리지 않는다
set -e
python3 spike/hist_verify.py "$1" > "$2" 2>&1
echo $? > "$3"
