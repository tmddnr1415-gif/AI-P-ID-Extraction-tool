# 교차검증 — Steam 계통만으로 규칙을 세우고 미지 계통에 적용

현재 97.0% / 87.0% 는 53개 도면을 모두 보면서 맞춘 값입니다. `FE`·`FT`·`LG`·`DPIT` 매핑이 전부 전수 대조에서 나왔다는 사실이 그 증거입니다. 여기서는 **Steam 계통(LBA/LBB/LBC/LBG/MAN)만 보고** 규칙을 재구성한 뒤, 본 적 없는 PGB·PAB·EGD 에 적용해 하락폭을 측정합니다.


## Steam 만으로 정당화되는 규칙 / 꺼진 규칙

| 규칙 | Steam 근거 | 상태 |
|---|---|---|
| `FE` → Field | p10·p11 각각 FE 3개 = Excel 3행 | 유지 |
| `FT` → `FIT` | p10 5/5, p11 5/5, p12 1/1 | 유지 |
| `LSH`/`LSHH`/`LSL` → `LS` | p7 LSHH 4 + LSH 4 = LS 4행 | 유지 |
| `TW` 제외 | Steam 도면 행에 `TW` 없음 | 유지 |
| `VENDOR_MARK_GLYPH` | p6 범례 글리프 | 유지 |
| `VENDOR_MARK_BOX` | p6 HRSG 패키지 박스 | 유지 |
| `LG` → `LI` | Steam 에 근거 없음 (p33/p49/p51) | **꺼짐** |
| `DPIT` → `PDIT` | Steam 에 근거 없음 (p21) | **꺼짐** |
| `VENDOR_MARK_TEXT` | Steam 에 텍스트 범례 페이지 없음 | **꺼짐** |
| 글리프 크기 5.2pt | p49 에서만 관찰 | **꺼짐** (4.0pt 만) |

## 결과

| 대상 | 페이지 | Steam 규칙 재현율 | Steam 규칙 정밀도 | 전체 규칙 재현율 | 전체 규칙 정밀도 | Δ재현율 | Δ정밀도 |
|---|---|---|---|---|---|---|---|
| STEAM (in-sample) | 7 | 100.0% | 94.6% | 100.0% | 94.6% | +0.0% | +0.0% |
| PGB (held out) | 7 | 99.4% | 96.0% | 99.4% | 96.0% | +0.0% | +0.0% |
| PAB (held out) | 3 | 85.7% | 24.0% | 85.7% | 54.5% | +0.0% | -30.5% |
| EGD (held out) | 2 | 93.9% | 54.4% | 100.0% | 64.7% | -6.1% | -10.3% |
| ALL MATCHED | 35 | 95.3% | 81.4% | 97.0% | 87.0% | -1.7% | -5.6% |

## TYPE 별 편차 (Steam 규칙 적용 시, 검출 − Excel)

| 대상 | 편차 |
|---|---|
| STEAM (in-sample) | `FIT` +4, `FE` +2, `PDIT` +1 |
| PGB (held out) | `PI` +4, `LS` +2, `LI` +1, `TIT` -1 |
| PAB (held out) | `LIT` +24, `PI` +13, `PIT` -2, `PDIT` +1 |
| EGD (held out) | `PI` +20, `FE` +2, `LI` -2, `PIT` +2, `TIT` +2 |
| ALL MATCHED | `PI` +56, `LIT` +32, `RO` +8, `PDIT` -5, `PIT` -4, `FE` +3, `FIT` +3, `LI` -3, `LS` +2, `TI` -1, `TIT` +1 |
