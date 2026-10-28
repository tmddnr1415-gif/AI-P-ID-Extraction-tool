#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 4800 python3 -m pytest -q -m slow -p no:cacheprovider > out/round26/slow2.log 2>&1
echo $? > out/round26/slow2.rc; echo DONE > out/round26/slow2.done
