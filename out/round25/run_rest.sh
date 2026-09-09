#!/bin/bash
cd /home/user/AI-P-ID-Extraction-tool
for S in 7 9 10 13 12; do out/round25/run_verify.sh $S; done
echo DONE > out/round25/verify_rest.done
