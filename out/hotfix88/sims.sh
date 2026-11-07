#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
rm -rf /tmp/qfe_perf && cp -r /tmp/qfe_flow /tmp/qfe_perf
timeout 1500 python3 spike/perf_sim.py /tmp/qfe_perf f4f152014e6e out/hotfix88/perf_after.json 3 > out/hotfix88/perf_sim.log 2>&1
timeout 1500 python3 spike/perf_edit_sim.py /tmp/qfe_flow f4f152014e6e out/hotfix88/edit_after.json 3 > out/hotfix88/perf_edit.log 2>&1
timeout 2400 python3 spike/qa_sim.py /tmp/qfe_flow out/hotfix88/qa --rounds 2 > out/hotfix88/qa_sim.log 2>&1
echo DONE > out/hotfix88/sims.done
