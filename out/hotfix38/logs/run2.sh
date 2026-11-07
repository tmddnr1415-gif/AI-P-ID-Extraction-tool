#!/bin/bash
# hotfix38 — 최종 코드로 (1) 두 판 실제 경로 흐름 (2) 순차 회귀.  메모리 때문에 순차.
cd /home/user/AI-P-ID-Extraction-tool
rm -rf /tmp/qfe_rev_data2
timeout 5400 python3 spike/rev_flow_qfe.py /tmp/qfe_rev_data2 data/QFE_260112.pdf data/QFE_260326.pdf out/hotfix38/flow2 > out/hotfix38/logs/flow2.log 2>&1
echo "exit $?" > out/hotfix38/logs/flow2.done
bash out/hotfix38/logs/chain.sh
