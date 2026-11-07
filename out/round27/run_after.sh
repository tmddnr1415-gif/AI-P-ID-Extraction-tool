#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
# slow 스위트가 끝날 때까지 기다린다 — 표식 파일로 (프로세스 이름으로 기다리지 않는다)
for i in $(seq 1 120); do [ -f out/round27/suites.done ] && break; sleep 30; done
[ -f out/round27/suites.done ] || { echo "TIMEOUT waiting for suites" ; exit 1; }
timeout 2400 python3 spike/regression_3p.py > out/round27/reg3.log 2>&1
echo $? > out/round27/reg3.rc
for f in data/pid_total.pdf data/TC2_260821.pdf; do
  echo "=== $f" >> out/round27/vocab2.log
  timeout 1200 python3 spike/note_vocab_delta.py "$f" >> out/round27/vocab2.log 2>&1
done
echo DONE > out/round27/after.done
