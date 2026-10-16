#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 3300 python3 spike/regression_3p.py > out/round29/reg4.log 2>&1
echo $? > out/round29/reg4.rc
echo DONE > out/round29/reg4.done
