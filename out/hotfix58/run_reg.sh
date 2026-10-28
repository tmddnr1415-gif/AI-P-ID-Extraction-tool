#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for p in TC2 "AL NOUF1" QFE; do
  n=${p// /_}
  timeout 3000 python3 spike/regression_3p.py --only "$p" > out/hotfix58/logs/$n.log 2>&1
  echo "$p exit $?" >> out/hotfix58/logs/progress.txt
done
echo DONE > out/hotfix58/logs/reg.done
