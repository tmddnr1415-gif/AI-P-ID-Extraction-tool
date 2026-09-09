#!/bin/bash
# 단계 하나를 돌리고 표식 파일을 남긴다. 기다리는 쪽은 표식만 본다.
cd /home/user/AI-P-ID-Extraction-tool
S="$1"
rm -f "out/round25/verify_s$S.done"
timeout 3000 python3 spike/verify_r25.py "$S" > "out/round25/verify_s$S.log" 2>&1
echo $? > "out/round25/verify_s$S.rc"
echo DONE > "out/round25/verify_s$S.done"
