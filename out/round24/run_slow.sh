#!/bin/sh
timeout 2400 python3 -m pytest -q -m slow > out/round24/slow.log 2>&1
echo $? > /tmp/slow.done
