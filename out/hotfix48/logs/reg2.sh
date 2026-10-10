#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
until [ -f out/hotfix48/logs/reg.done ]; do sleep 30; done
timeout 3000 python3 spike/regression_3p.py --only "AL NOUF1" > out/hotfix48/logs/reg_AL_NOUF1.log 2>&1
echo "exit $?" >> out/hotfix48/logs/reg_AL_NOUF1.log
cd /tmp/wt_before
PID_DATA_DIR=/tmp/wt_before_data timeout 3000 python3 spike/analyse_one.py /home/user/AI-P-ID-Extraction-tool/data/QFE_260326.pdf /home/user/AI-P-ID-Extraction-tool/out/hotfix48/QFE_before.json > /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/before.log 2>&1
echo "exit $?" >> /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/before.log
echo DONE > /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/reg2.done
