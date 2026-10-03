#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
python3 spike/regression_3p.py --only 'AL NOUF1' > out/hotfix33/logs/reg_nouf1.log 2>&1; echo "nouf1=$?" >> out/hotfix33/logs/reg_pdf.status
python3 spike/regression_3p.py --only TC2 > out/hotfix33/logs/reg_tc2.log 2>&1; echo "tc2=$?" >> out/hotfix33/logs/reg_pdf.status
echo DONE > out/hotfix33/logs/reg_pdf.done
