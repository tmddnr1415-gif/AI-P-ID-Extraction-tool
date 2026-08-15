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
