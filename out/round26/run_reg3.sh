#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 3000 python3 spike/regression_3p.py > out/round26/reg3.log 2>&1
echo $? > out/round26/reg3.rc; echo DONE > out/round26/reg3.done
