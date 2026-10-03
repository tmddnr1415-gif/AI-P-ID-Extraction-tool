#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
timeout 2400 python3 /tmp/auditdiff.py > out/round26/auditdiff.log 2>&1
echo $? > out/round26/auditdiff.rc; echo DONE > out/round26/auditdiff.done
