#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
python3 spike/regression_3p.py --only UAD-DXF > out/hotfix33/logs/reg_uad.log 2>&1
echo "exit=$?" > out/hotfix33/logs/reg_uad.done
