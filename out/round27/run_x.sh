#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 2400 python3 /tmp/xcheck.py data/pid_total.pdf out/regression_3p/AL_NOUF1.json > out/round27/xcheck_alnouf1.log 2>&1
timeout 2400 python3 /tmp/xcheck.py data/TC2_260821.pdf out/regression_3p/TC2.json > out/round27/xcheck_tc2.log 2>&1
echo DONE > out/round27/x.done
