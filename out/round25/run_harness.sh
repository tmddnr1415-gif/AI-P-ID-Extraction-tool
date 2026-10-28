#!/bin/bash
# 표식 파일만 기다린다 (23회차 규칙). 세 프로젝트 순차 — 병렬 금지.
cd /home/user/AI-P-ID-Extraction-tool
timeout 3000 python3 spike/regression_3p.py > out/round25/harness_r25.log 2>&1
echo $? > out/round25/harness_r25.rc
echo DONE > out/round25/harness_r25.done
