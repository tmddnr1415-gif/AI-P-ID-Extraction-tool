#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 2400 python3 spike/star_gate_probe.py data/TC2_260821.pdf > out/round25/gate_tc2.log 2>&1
echo $? > out/round25/gate_tc2.rc; echo DONE > out/round25/gate_tc2.done
timeout 2400 python3 spike/star_gate_probe.py data/pid_total.pdf > out/round25/gate_alnouf1.log 2>&1
echo $? > out/round25/gate_alnouf1.rc; echo DONE > out/round25/gate_alnouf1.done
