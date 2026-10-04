#!/bin/bash
# hotfix38 — 최종 코드로 순차 회귀 (AL NOUF1 → TC2 → QFE).  완료 표식은 파일이다.
cd /home/user/AI-P-ID-Extraction-tool
for P in "AL NOUF1" "TC2" "QFE"; do
  N=$(echo "$P" | tr ' ' '_')
  timeout 2400 python3 spike/regression_3p.py --only "$P" > "out/hotfix39/logs/reg_$N.log" 2>&1
  echo "exit $?" > "out/hotfix39/logs/reg_$N.done"
done
echo done > out/hotfix39/logs/chain.done
