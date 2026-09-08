#!/bin/bash
# 23회차 규칙 — 기다리는 쪽은 표식 파일만 본다 (프로세스 이름을 찾지 않는다).
cd /home/user/AI-P-ID-Extraction-tool
LABEL="${2:-before}"
timeout 2400 python3 spike/regression_3p.py > "out/round24/harness_$LABEL.log" 2>&1
echo $? > "out/round24/harness_$LABEL.rc"
