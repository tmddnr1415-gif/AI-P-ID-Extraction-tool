# 검토 기록

사람이 결과를 검토하며 지적한 오류와, 그에 대응해 개정한 규칙의 이력입니다.
**최신 기록이 위쪽**에 옵니다.

기록은 `scripts/apply_feedback.py`가 리뷰 UI의 피드백 JSON을 받아 자동으로 추가합니다.

```bash
python3 scripts/apply_feedback.py feedback_run_20260815_2230.json --apply-rules
```

각 항목에는 **언제 · 누가 · 무엇을 · 왜 고쳤는지**와 **앞으로 어떻게 출력되어야 하는지**가
함께 남습니다. 규칙 코멘트는 `rules/extraction_guide.md` 하단에 초안으로 쌓이며,
사람이 문장을 다듬어 본문 절로 승격시킵니다.

<!-- 새 기록은 이 아래에 추가됩니다 -->


## 2026-08-15 — 프로젝트 초기화

- 작업자: 파일럿 셋업
- 내용: 파이프라인 초기 구축 (`inspect_template` → `pdf_to_images` → `parse_legend` →
  `extract_instruments` → `build_excel` → 리뷰 UI → `apply_feedback`)
- 첨부 자료 분석으로 확인한 사실을 `rules/extraction_guide.md` v1에 반영:
  - 정답 Instrument List 563행 분석 결과, 모델이 도면에서 판독해야 하는 컬럼은
    `SYSTEM`, `P&ID No.`, `TYPE`, `Q'ty`, `DESCRIPTION`, `INST. TYPICAL TYPE`, `REMARK` 7개뿐이다.
    사양 컬럼 5개는 `INST. TYPICAL TYPE`으로 결정되고, 19개는 Design Table 조인 값이며,
    9개는 템플릿에서 전 행 비어 있다.
  - `TAG` 열은 563행 전부 비어 있다. 제안 단계 도면이라 계기 버블의 태그 자리가
    점선으로 비어 있기 때문이다. → **태그 번호를 생성하지 않는다**는 규칙으로 반영.
  - PDF에 텍스트 레이어가 있어 계기 문자를 좌표까지 결정적으로 추출할 수 있다.
    p38(CCW 4/7)은 텍스트 레이어 24건 = 정답 24행으로 정확히 일치했다.
    → 텍스트 후보를 판독 기준선으로 함께 넣는 방식 채택.
  - p6(HP Steam)은 텍스트 34건 대 정답 6행으로 차이가 크다. 호기 중복(Q'ty 통합)과
    벤더 패키지 범위 제외 때문으로 보이며, 이 두 규칙이 정확도의 핵심이다.
- 확인 필요로 남긴 것:
  - PDF p15의 타이틀블록 도면번호(`D00P-10LBG10-M05-0001`)가 p12와 중복이다.
    도면명은 GT Flash Pipe System이므로 번호 오기로 보인다. 원본 확인 필요.
  - `D00P-00PAB10-M05-0001`이 p26/27/28/30에 중복 사용되고 있다. (1/3, 2/3, 3/3 및 순환수 계통)
  - 정답 Excel의 P&ID No. 중 10건이 PDF 58쪽에 없다. 도면 세트가 일부 누락된 것인지 확인 필요.


## 2026-08-16 — 1차 시험판독 (p6 / p20 / p38) 및 규칙 개정

- 작업자: 세션 직접 판독 (Claude API 미사용 — 사용자가 API 키 없이 결과를 보고 싶어 함)
- 방법: `pdf_to_images.py --pages 6,20,38 --tiles 3x2 --dpi 200` 으로 이미지를 만들고,
  전체 도면 1장 + 확대 타일을 읽어 `extraction.json` 을 손으로 작성했다.
  출력 형식이 `extract_instruments.py` 와 같아 `build_excel.py` 를 그대로 썼다.
- 산출물: `outputs/run_session_manual/` (1차), `outputs/run_session_manual_v2/` (검토 반영)

### 1차 결과 — 정답을 보지 않고 판독

| 항목 | p6 | p20 | p38 |
|---|---|---|---|
| 행 수 | 12 / 12 | 33 / 33 | 24 / 24 |
| TYPE | 100% | 100% | 100% |
| INST. TYPICAL TYPE | 100% | 100% | 100% |
| Q'ty | 100% | 100% | 87.5% |
| DESCRIPTION (완전일치) | 0% | 18% | 0% |

행 수·TYPE·TYPICAL은 전부 맞았다. **DESCRIPTION만 69행 중 6행**이다.
계기를 찾는 것보다 **부르는 이름을 맞추는 것**이 어렵다는 뜻이다.

### 정답 대조로 확인한 것

1. **`*` / `**` 공급 범위 표기가 최대 제외 사유.** p6은 계기 문자 34건 중 22건이
   `* DENOTES ... SUPPLIED BY HRSG` / `** ... BY ST SUPPLIER` 라서 빠지고 12건만 남는다.
   이 각주를 못 읽으면 행 수가 3배가 된다. → 규칙 3.1 신설
2. **`CONFIGURATION IS IDENTICAL FOR ...` 는 행 분리가 아니라 Q'ty 배수.**
   `GROUP#20` → 2, `UNIT#12,21,22` → 4. → 규칙 5.1 신설
3. **`PLANT COMMON` 설비는 그 배수에서 빠진다** (qty 1). p38 Q'ty 오차 3건이 전부 이것.
4. **도면 안 병렬 계기는 합치지 않는다.** FE 1개 + FIT 2개 = 3행. → 규칙 5.2
5. **A/B가 두 자리에서 뜻이 다르다.** 설비명 뒤 = 어느 설비, 문장 끝 = 같은 지점의
   몇 번째 계기. `PUMP A SUCTION PRESSURE B`. → 규칙 6.1
6. **설비 이름은 그 도면 설비 박스에 적힌 대로.** p20은 `BOILER FEED WATER PUMP`,
   p38은 `BFP A/B COOLER`. 같은 설비라도 도면이 다르게 부르면 다르게 쓴다. → 규칙 6.2, 6.3
7. **공용 헤더는 설비 서브 식별자를 뺀다.** → 규칙 6.4
8. **구간 이름은 배관 치수가 아니라 도착지에서.** `MINIMUM FLOW RECIRCULATION LINE` 이라
   적힌 라인의 유량계도 정답은 `DISCHARGE IP FLOW` 다. → 규칙 6.5
9. **그룹 공용 계기는 그룹 번호를 호기 자리에** (`UNIT #10`). → 규칙 6.6

### 2차 (검토 반영) 결과

위 규칙을 적용해 다시 쓰니 69/69행이 TYPE·Q'ty·DESCRIPTION·TYPICAL 모두 일치했다.
**단, 이 3장은 정답을 보고 고친 것이라 정확도의 증거가 아니다.**
규칙이 실제로 일반화되는지는 **정답을 보지 않은 다른 도면**으로 확인해야 한다.

### 다음에 할 것

- 정답이 있는 다른 도면 3~5장을 골라 규칙 개정본으로 재판독 (blind)
- 그때는 Claude API 또는 이 세션 중 어느 쪽이든 같은 규칙을 쓰므로 비교가 가능하다
- `compare.py` 를 만들어 이 대조를 자동화 (DESCRIPTION 정규화 기준 합의 필요)
