#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for f in data/pid_total.pdf data/TC2_260821.pdf app/_data/uploads/2391ee0f1ea6_sadara_1A46.pdf; do
  echo "=== $f"
  timeout 900 python3 spike/note_vocab_delta.py "$f" 2>&1 | tail -25
done
echo DONE > out/round27/vocab.done
