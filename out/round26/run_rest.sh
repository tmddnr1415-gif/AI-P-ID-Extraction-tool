#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for S in 7 9 10 13 12; do out/round26/run_verify.sh $S; done
echo DONE > out/round26/verify_rest.done
