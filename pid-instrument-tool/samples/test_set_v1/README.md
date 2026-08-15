# test_set_v1 — 검증용 대표 도면 세트

정확도를 측정하는 기준입니다. 도면 범위를 넓히기 전에 이 세트에서 목표 정확도를 통과해야 합니다.

## ground_truth.json

`scripts/inspect_template.py`가 사람이 작성한 Field Instrument 목록(563행)에서 생성합니다.
Excel 원본이 그대로 정답이므로 별도로 정답을 만들 필요가 없습니다.

```bash
python3 scripts/inspect_template.py inputs/D00P-00CZE00-J30-0001_RC_Field_Instrument_2512xx.xlsx
```

## 권장 대표 도면 (PDF 페이지 ↔ 정답 행 수)

정답 Excel과 PDF에 **모두** 있는 30개 도면 중, 성격이 다른 것들을 골랐습니다.

| PDF p | 도면번호 | 계통 | 정답 행 수 | 왜 이 도면인가 |
|---|---|---|---|---|
| 38 | `D00P-10PGB10-M05-0004` | Closed Cooling Water | 24 | 텍스트 레이어 24건 = 정답 24행. **기준선이 정확히 맞는 쉬운 케이스** |
| 20 | `D00P-11LAB00-M05-0001` | HRSG Feedwater | 33 | 텍스트 37건 → 정답 33행. `PT/FT/TT` → `PIT/FIT/TIT` 매핑과 `ZS` 제외가 필요 |
| 6 | `D00P-10LBA10-M05-0001` | HP Steam | 6 | 텍스트 34건 → 정답 6행. **Q'ty 통합과 벤더 범위 제외가 핵심인 어려운 케이스** |
| 16 | `D00P-10LCA10-M05-0001` | Condensate (1/2) | 31 | 계기 밀도가 가장 높은 도면 중 하나 |
| 40 | `D00P-10PGB10-M05-0006` | Closed Cooling Water | 32 | 같은 계통의 다른 시트 — 규칙 일반화 확인용 |

```bash
python3 scripts/pdf_to_images.py inputs/D00P_PID_Total_20251125.pdf --pages 6,16,20,38,40 --tiles 3x2
python3 scripts/extract_instruments.py --pages 6,16,20,38,40
```

## 정확도 측정 방법 (현재 / 다음 단계)

**현재**는 리뷰 UI에서 사람이 수정한 건수로 정확도를 가늠합니다.
`apply_feedback.py`가 "수정 없이 통과한 행 비율"을 출력합니다.

**다음 단계**로 `ground_truth.json`과 자동 대조하는 `compare.py`가 필요합니다(워크플로우 5단계).
아직 만들지 않았습니다. 대조 키는 `P&ID No. + TYPE + DESCRIPTION` 조합인데,
DESCRIPTION은 표현이 조금씩 달라질 수 있어 **정규화 규칙을 먼저 합의**해야 합니다.
(예: `BFP A/B` vs `BOILER FEED WATER PUMP A/B`, `#11` vs `11` 처리)
