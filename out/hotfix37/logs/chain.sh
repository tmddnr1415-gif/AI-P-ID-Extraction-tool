#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for P in QFE "AL NOUF1" TC2 UAD-DXF; do
  tag=$(echo "$P" | tr ' ' '_')
  python3 spike/regression_3p.py --only "$P" > "out/hotfix37/logs/$tag.log" 2>&1
  echo "exit $?" > "out/hotfix37/logs/$tag.done"
done
echo ALL > out/hotfix37/logs/chain.done
