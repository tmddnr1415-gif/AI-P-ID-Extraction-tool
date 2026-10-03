#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
export PID_DATA_DIR=/tmp/uadtest
rm -f out/round28/uad.json
timeout 2400 python3 spike/analyse_one.py data/UAD_binding.pdf out/round28/uad.json > out/round28/uad.log 2>&1
echo $? > out/round28/uad.rc
timeout 3000 python3 spike/regression_3p.py > out/round28/reg.log 2>&1
echo $? > out/round28/reg.rc
echo DONE > out/round28/all.done
