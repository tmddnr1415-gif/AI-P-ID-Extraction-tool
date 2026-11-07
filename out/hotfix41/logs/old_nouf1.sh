#!/bin/bash
# hotfix41 — 직전 커밋(4304ef9) 코드로 AL NOUF1 을 한 번 더 돌려 1137행 결과를 얻는다 (칸 단위 대조용).
cd /tmp/wt_hf40
PID_DATA_DIR=/tmp/wt_hf40_data timeout 2400 python3 spike/regression_3p.py --only "AL NOUF1" > /home/user/AI-P-ID-Extraction-tool/out/hotfix41/logs/old_nouf1.log 2>&1
echo "exit $?" > /home/user/AI-P-ID-Extraction-tool/out/hotfix41/logs/old_nouf1.done
