#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 1500 python3 -m pytest -q tests/test_star_marks.py -m slow -p no:cacheprovider > out/round26/slowstar.log 2>&1
echo $? > out/round26/slowstar.rc; echo DONE > out/round26/slowstar.done
