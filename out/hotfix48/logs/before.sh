#!/bin/bash
cd /tmp/wt_before
until [ -f /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/reg.done ]; do sleep 30; done
PID_DATA_DIR=/tmp/wt_before_data timeout 3000 python3 spike/analyse_one.py /home/user/AI-P-ID-Extraction-tool/data/QFE_260326.pdf /home/user/AI-P-ID-Extraction-tool/out/hotfix48/QFE_before.json > /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/before.log 2>&1
echo "exit $?" >> /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/before.log
echo DONE > /home/user/AI-P-ID-Extraction-tool/out/hotfix48/logs/before.done
