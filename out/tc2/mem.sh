#!/bin/bash
# 최대 RSS 를 함께 잰다
/usr/bin/time -v python3 out/tc2/run.py "$1" "$2" 2>&1
