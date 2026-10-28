#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for spec in "AL_NOUF1 data/pid_total.pdf" "TC2 data/TC2_260821.pdf" "QFE data/QFE_260326.pdf"; do
  set -- $spec
  timeout 3000 python3 spike/act_reach_probe.py $2 out/hotfix48/probe_$1.json > out/hotfix48/probe_$1.log 2>&1
  echo "exit $?" >> out/hotfix48/probe_$1.log
done
echo DONE > out/hotfix48/probe_all.done
