#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 1800 python3 spike/regression_3p.py --only TC2 > out/round24/tc2_before.log 2>&1
echo $? > out/round24/tc2_before.rc
