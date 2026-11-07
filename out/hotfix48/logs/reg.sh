#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
until [ -f out/hotfix48/probe_all.done ]; do sleep 30; done
for p in QFE AL_NOUF1 TC2; do
  timeout 3000 python3 spike/regression_3p.py --only $p > out/hotfix48/logs/reg_$p.log 2>&1
  echo "exit $?" >> out/hotfix48/logs/reg_$p.log
done
echo DONE > out/hotfix48/logs/reg.done
