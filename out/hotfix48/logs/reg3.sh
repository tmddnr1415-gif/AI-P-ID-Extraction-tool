#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for n in "QFE" "AL NOUF1" "TC2" "UAD-DXF"; do
  f=$(echo "$n" | tr ' ' '_')
  timeout 3000 python3 spike/regression_3p.py --only "$n" > "out/hotfix48/logs/reg3_$f.log" 2>&1
  echo "exit $?" >> "out/hotfix48/logs/reg3_$f.log"
done
echo DONE > out/hotfix48/logs/reg3.done
