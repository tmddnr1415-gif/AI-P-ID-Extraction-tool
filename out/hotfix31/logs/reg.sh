#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 1500 python3 spike/regression_3p.py --only TC2 > out/hotfix31/logs/reg_tc2.log 2>&1
echo "tc2 exit $?" >> out/hotfix31/logs/reg_status.txt
timeout 1800 python3 spike/regression_3p.py --only 'AL NOUF1' > out/hotfix31/logs/reg_nouf1.log 2>&1
echo "nouf1 exit $?" >> out/hotfix31/logs/reg_status.txt
timeout 1500 python3 spike/regression_3p.py --only 'UAD-DXF' > out/hotfix31/logs/reg_uaddxf.log 2>&1
echo "uaddxf exit $?" >> out/hotfix31/logs/reg_status.txt
git checkout out/regression_3p.json 2>/dev/null
echo DONE > out/hotfix31/logs/reg.done
