#!/usr/bin/env bash
# 33회차 [C-3] — 네 프로젝트 28장 전/후.  "전" 은 32회차 캡처(같은 HEAD 2410e73 ·
# 같은 도구 · 같은 장 선택)를 그대로 옮기고, "후" 는 최종 엔진 결과로 다시 찍는다.
set -e
cd "$(dirname "$0")/.."
D="out/round33/7_캡처/색_전후"
mkdir -p "$D"
# shot_overlay 는 projects_3p.json 의 이름("AL NOUF1", 띄어쓰기)으로 PDF 를 찾고,
# 결과 json 은 밑줄 이름이다.
for P in AL_NOUF1 SADARA TC2 UAD; do
  NAME="${P/_/ }"
  rm -rf "$D/${P}_전"; cp -r "out/round32/7_캡처/$P" "$D/${P}_전"
  timeout 900 python3 spike/shot_overlay.py "$NAME" "out/regression_3p/$P.json" "$D/${P}_후"
done
mkdir -p "$D/범례패널"
for P in SADARA UAD; do
  for f in "$D/${P}_후"/p*_legend.png; do cp "$f" "$D/범례패널/${P}_후_$(basename "$f")"; done
done
echo DONE > out/round33_shots.done
