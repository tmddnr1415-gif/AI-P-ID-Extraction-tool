#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
S="$1"; rm -f "out/round26/verify_s$S.done"
timeout 3000 python3 spike/verify_r26.py "$S" > "out/round26/verify_s$S.log" 2>&1
echo $? > "out/round26/verify_s$S.rc"; echo DONE > "out/round26/verify_s$S.done"
