#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for p in TC2_260821 pid_total; do
  timeout 2400 python3 spike/unit_notes.py data/$p.pdf > out/round27/notes_$p.log 2>&1
done
timeout 2400 python3 spike/unit_notes.py app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf > out/round27/notes_sadara.log 2>&1
echo DONE > out/round27/notes.done
